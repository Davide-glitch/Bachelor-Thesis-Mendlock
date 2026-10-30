"""Persistent JSON store for element fingerprints."""
from __future__ import annotations

import json
from pathlib import Path

from .candidates import Fingerprint


class FingerprintStore:
    def __init__(self, path):
        self.path = Path(path)
        self._d: dict = {}
        if self.path.exists():
            self._d = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def key(page_key: str, selector: str) -> str:
        return f"{page_key}::{selector}"

    def get(self, page_key: str, selector: str) -> Fingerprint | None:
        d = self._d.get(self.key(page_key, selector))
        if d is None:
            same = [v for v in self._d.values() if v["selector"] == selector]
            d = same[0] if len(same) == 1 else None
        return Fingerprint.from_json(d) if d else None

    def put(self, fp: Fingerprint) -> None:
        self._d[self.key(fp.page_key, fp.selector)] = fp.to_json()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._d, indent=1), encoding="utf-8")