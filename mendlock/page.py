"""HealingPage decorator wrapper around a Playwright Page."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .candidates import locator_ok, make_fingerprint, page_key_of
from .healer import HealConfig, Healer, HealResult
from .model import Model, load_default_model
from .patcher import patch_selector
from .store import FingerprintStore


class HealingUnavailable(RuntimeError):
    """Raised when a locator is stale and no prior fingerprint exists."""


class HealingFailed(AssertionError):
    def __init__(self, result: HealResult):
        top = "; ".join(f"{t!r} p={p}" for _, t, p in result.ranking[:3])
        super().__init__(f"Self-healing refused ({result.status}). Top candidates: {top}. {result.reason}".strip())
        self.result = result


class HealingPage:
    def __init__(self, page, *, model: Model | None = None, heal: HealConfig | None = None,
                 out_dir: str = ".mendlock", patch_mode: str = "suggest", record: str = "if_missing"):
        if patch_mode not in ("off", "suggest", "apply") or record not in ("if_missing", "always"):
            raise ValueError("patch_mode in {off, suggest, apply}; record in {if_missing, always}")
        self._page = page
        self.model = model or load_default_model()
        self.healer = Healer(self.model, heal or HealConfig())
        self.out_dir = Path(out_dir)
        self.store = FingerprintStore(self.out_dir / "fingerprints.json")
        self.patch_mode, self.record = patch_mode, record
        self.events: list = []

    def __getattr__(self, name):
        return getattr(self._page, name)

    def click(self, selector: str, *, intent: str, expect=None, timeout: int = 1500) -> HealResult:
        frame = sys._getframe(1)
        where = (frame.f_code.co_filename, frame.f_lineno)
        page_key = page_key_of(self._page.url)

        if locator_ok(self._page, selector):
            if self.record == "always" or self.store.get(page_key, selector) is None:
                self.store.put(make_fingerprint(self._page, selector, page_key))
            self._page.locator(selector).click(timeout=timeout)
            return HealResult("NOT_NEEDED")

        fp = self.store.get(page_key, selector)
        if fp is None:
            raise HealingUnavailable(
                f"{selector!r} is stale and was never recorded on {page_key!r}; run the test once "
                "against a working version of the page so a fingerprint can be saved."
            )
        res = self.healer.heal(self._page, fp, intent, expect)
        event = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "test": f"{where[0]}:{where[1]}",
            "old_selector": selector,
            **res.to_log(),
        }
        if res.status == "HEALED_VERIFIED":
            self.store.put(res.new_fingerprint)
            event["patch"] = self._patch(where, selector, res.selector)
        self._log(event)
        if res.healed:
            return res
        raise HealingFailed(res)

    def _patch(self, where, old: str, new: str):
        if self.patch_mode == "off":
            return None
        r = patch_selector(where[0], where[1], old, new, apply=self.patch_mode == "apply")
        if r is None:
            return "no matching string literal on that call"
        d = self.out_dir / "patches"
        d.mkdir(parents=True, exist_ok=True)
        diff_file = d / f"{len(self.events):03d}-{Path(where[0]).stem}.diff"
        diff_file.write_text(r.diff, encoding="utf-8")
        return {"diff_file": str(diff_file), "applied": r.applied, "replaced": r.replaced}

    def _log(self, event: dict) -> None:
        self.events.append(event)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with (self.out_dir / "heals.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")