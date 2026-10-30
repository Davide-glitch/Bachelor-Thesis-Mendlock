"""Browser pass: extracts features, ground truth labels, and post-condition oracle outcomes."""
from __future__ import annotations

import json
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

from mendlock import vision
from mendlock._compat import PlaywrightError
from mendlock.candidates import locator_ok, make_fingerprint, snapshot
from mendlock.features import FEATURES, compute
from mendlock.text import get_backend
from mendlock.verify import check

from .corpus import make_expect

VIEWPORT = {"width": 1000, "height": 700}


@dataclass
class CaseData:
    id: str
    template: str
    category: str
    split: str
    oracle_blind: bool
    has_target: bool
    X: np.ndarray
    y: np.ndarray
    oracle: object
    css_paths: list
    texts: list
    old_selector: str
    collect_ms: float


def load_manifest(path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def collect(out_dir, backend_name: str = "lexical", limit: int | None = None, verbose: bool = True) -> Path:
    out_dir = Path(out_dir)
    recs = load_manifest(out_dir / "manifest.jsonl")
    if limit:
        recs = recs[:limit]
    backend = get_backend(backend_name)
    cases, skipped = [], {}
    out = out_dir / "cases.pkl"
    if out.exists():
        prev = load_cases(out_dir)
        if prev["backend"] == backend_name:
            cases, skipped = prev["cases"], prev["skipped"]
    done = {c.id for c in cases}
    t_start = time.time()

    def save():
        with out.open("wb") as f:
            pickle.dump({"backend": backend_name, "features": FEATURES, "skipped": skipped, "cases": cases}, f)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport=VIEWPORT, device_scale_factor=1).new_page()
        for k, r in enumerate(recs, 1):
            if r["id"] in done:
                continue
            base_url = (out_dir / r["base_page"]).resolve().as_uri()
            mut_url = (out_dir / r["mutated_page"]).resolve().as_uri()
            page.goto(base_url)
            fp = make_fingerprint(page, r["old_selector"])
            page.goto(mut_url)
            if locator_ok(page, r["old_selector"]):
                skipped["old_selector_still_works"] = skipped.get("old_selector_still_works", 0) + 1
                continue
            t0 = time.perf_counter()
            snap = snapshot(page)
            img = vision.decode_png(snap.screenshot)
            crops = [vision.crop_bbox(img, c.bbox) for c in snap.candidates]
            X = compute(fp, snap.candidates, r["intent"], crops, backend, snap.doc_size)
            ms = (time.perf_counter() - t0) * 1000
            y = np.array([c.gt for c in snap.candidates], dtype=bool)
            if int(y.sum()) != (1 if r["has_target"] else 0):
                skipped["ground_truth_mismatch"] = skipped.get("ground_truth_mismatch", 0) + 1
                continue
            oracle = None
            if r["split"] != "train":
                expect, oracle = make_expect(r["result_text"]), np.zeros(len(snap.candidates), dtype=bool)
                for j, c in enumerate(snap.candidates):
                    page.goto(mut_url)
                    try:
                        page.locator(c.css_path).click(timeout=2000)
                        oracle[j] = check(expect, page)
                    except PlaywrightError:
                        oracle[j] = False
            cases.append(CaseData(
                r["id"], r["template"], r["category"], r["split"], r["oracle_blind"],
                r["has_target"], X, y, oracle, [c.css_path for c in snap.candidates],
                [c.text for c in snap.candidates], r["old_selector"], ms,
            ))
            if k % 50 == 0:
                save()
                if verbose:
                    print(f"  collected {k}/{len(recs)} ({time.time() - t_start:.0f}s)", flush=True)
        browser.close()
    save()
    if verbose:
        print(f"collected {len(cases)} cases, skipped {skipped or 0}, in {time.time() - t_start:.0f}s -> {out}")
    return out


def load_cases(out_dir) -> dict:
    with (Path(out_dir) / "cases.pkl").open("rb") as f:
        return pickle.load(f)