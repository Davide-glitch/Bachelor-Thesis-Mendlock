"""Live browser-in-the-loop verification check against offline simulation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

from mendlock.candidates import make_fingerprint
from mendlock.healer import HealConfig, Healer
from mendlock.model import Model

from .collect import VIEWPORT, load_cases, load_manifest
from .corpus import make_expect
from .evaluate import _md, run_method

MODES = ("gate", "verify", "verify_topk")


def run_e2e(out_dir, model_path, results_dir, limit: int = 80) -> Path:
    out_dir, results_dir = Path(out_dir), Path(results_dir)
    model = Model.load(model_path)
    k = model.meta.get("k", 3)
    blob = load_cases(out_dir)
    by_id = {c.id: c for c in blob["cases"]}
    recs = [
        r for r in load_manifest(out_dir / "manifest.jsonl")
        if r["split"] in ("test", "test_ood") and r["id"] in by_id
    ]
    if limit and len(recs) > limit:
        recs = recs[:: max(1, len(recs) // limit)][:limit]
    healers = {m: Healer(model, HealConfig(mode=m, max_attempts=k, backend=blob["backend"])) for m in MODES}
    st = {m: {"agree": 0, "ok": 0, "bad": 0, "lat": [], "rollbacks": 0, "clean": 0, "mismatch": []} for m in MODES}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport=VIEWPORT, device_scale_factor=1).new_page()
        for r in recs:
            case = by_id[r["id"]]
            base_url = (out_dir / r["base_page"]).resolve().as_uri()
            mut_url = (out_dir / r["mutated_page"]).resolve().as_uri()
            page.goto(base_url)
            fp = make_fingerprint(page, r["old_selector"])
            expect = make_expect(r["result_text"])
            for m in MODES:
                page.goto(mut_url)
                res = healers[m].heal(page, fp, r["intent"], expect)
                _, committed = run_method(m, case, model, 0.0, k)
                offline = case.css_paths[committed] if committed is not None else None
                online = res.css_path if res.healed else None
                s = st[m]
                s["lat"].append(res.latency_ms)
                s["agree"] += int(online == offline)
                if online != offline:
                    s["mismatch"].append(f"{r['id']}: live={online} offline={offline} ({res.status})")
                if res.healed:
                    s["ok" if res.candidate.gt else "bad"] += 1
                if res.status == "REJECTED_VERIFICATION":
                    s["rollbacks"] += 1
                    clean = (
                        page.url == mut_url
                        and not page.locator("#toast").is_visible()
                        and not page.locator("#result").is_visible()
                    )
                    s["clean"] += int(clean)
        browser.close()

    n = len(recs)
    body = []
    for m in MODES:
        s = st[m]
        lat = np.array(s["lat"])
        body.append([
            m, f"{s['agree']}/{n}", s["ok"], s["bad"], f"{s['clean']}/{s['rollbacks']}",
            f"{np.percentile(lat, 50):.0f}", f"{np.percentile(lat, 95):.0f}",
        ])
    L = [
        "# End-to-End Live Verification", "",
        f"{n} held-out cases sampled evenly.", "",
    ]
    L += _md(["Mode", "Agreement", "Correct heals", "Wrong heals", "Clean rollbacks", "Latency p50 ms", "Latency p95 ms"], body)
    out = results_dir / "e2e.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return out