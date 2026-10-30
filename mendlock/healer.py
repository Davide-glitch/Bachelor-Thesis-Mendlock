"""Self-healing pipeline: snapshot -> features -> ranking -> speculative verification."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from . import features as F
from . import vision
from .candidates import Candidate, Fingerprint, snapshot, stable_selector
from .decision import MODES, plan
from .model import Model
from .text import get_backend
from .verify import attempt_click, check, plain_click


@dataclass
class HealConfig:
    mode: str = "verify"
    max_attempts: int = 3
    verify_timeout_ms: int = 1500
    click_timeout_ms: int = 2000
    guard_mutations: bool = False
    allow_unverified: bool = False
    compute_selector: bool = True
    backend: str = "lexical"

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")


@dataclass
class Attempt:
    css_path: str
    selector: str
    p: float
    clicked: bool
    verified: bool
    error: str = ""
    gt: bool = False


@dataclass
class HealResult:
    status: str
    candidate: Candidate | None = None
    selector: str = ""
    css_path: str = ""
    confidence: float = 0.0
    verified: bool = False
    attempts: list = field(default_factory=list)
    ranking: list = field(default_factory=list)
    latency_ms: float = 0.0
    reason: str = ""
    new_fingerprint: Fingerprint | None = None
    blocked_requests: list = field(default_factory=list)

    @property
    def healed(self) -> bool:
        return self.status in ("HEALED_VERIFIED", "HEALED_UNVERIFIED")

    def to_log(self) -> dict:
        return {
            "status": self.status,
            "selector": self.selector,
            "confidence": round(self.confidence, 4),
            "verified": self.verified,
            "latency_ms": round(self.latency_ms, 1),
            "reason": self.reason,
            "attempts": [
                {
                    "css_path": a.css_path,
                    "p": round(a.p, 4),
                    "clicked": a.clicked,
                    "verified": a.verified,
                    "error": a.error,
                }
                for a in self.attempts
            ],
            "ranking": self.ranking,
            "blocked_requests": self.blocked_requests,
        }


@dataclass
class Ranking:
    cands: list
    X: np.ndarray
    p: np.ndarray
    snap: object
    crops: list


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


class Healer:
    def __init__(self, model: Model, cfg: HealConfig | None = None, backend=None):
        self.model = model
        self.cfg = cfg or HealConfig()
        self.backend = backend or get_backend(self.cfg.backend)

    def rank(self, page, fp: Fingerprint, intent: str) -> Ranking:
        snap = snapshot(page)
        if not snap.candidates:
            return Ranking([], np.zeros((0, len(F.FEATURES))), np.zeros(0), snap, [])
        img = vision.decode_png(snap.screenshot)
        crops = [vision.crop_bbox(img, c.bbox) for c in snap.candidates]
        X = F.compute(fp, snap.candidates, intent, crops, self.backend, snap.doc_size)
        return Ranking(snap.candidates, X, self.model.probs(X), snap, crops)

    def heal(self, page, fp: Fingerprint, intent: str, expect=None) -> HealResult:
        t0 = time.perf_counter()
        cfg = self.cfg
        res = HealResult("NO_CANDIDATES")
        rk = self.rank(page, fp, intent)
        if not rk.cands:
            res.latency_ms = _ms(t0)
            return res
        order = np.argsort(-rk.p, kind="stable")
        res.confidence = self.model.confidence(rk.p[order])
        res.ranking = [(rk.cands[i].css_path, rk.cands[i].text, round(float(rk.p[i]), 4)) for i in order[:5]]

        steps = plan(self.model, rk.p, cfg.mode, cfg.max_attempts)
        if not steps:
            res.status, res.latency_ms = "ABSTAINED_LOW_CONFIDENCE", _ms(t0)
            return res

        verifying = cfg.mode != "gate"
        if verifying and expect is None:
            if not cfg.allow_unverified:
                res.status, res.reason, res.latency_ms = "ABSTAINED_NO_ORACLE", "no post-condition given", _ms(t0)
                return res
            verifying = False
        if verifying and check(expect, page):
            res.reason = "post-condition already true before acting; cannot distinguish valid from invalid clicks"
            if not cfg.allow_unverified:
                res.status, res.latency_ms = "ABSTAINED_VACUOUS_ORACLE", _ms(t0)
                return res
            verifying = False
        if not verifying:
            steps = steps[:1]

        for i in steps:
            c = rk.cands[i]
            sel = stable_selector(page, c) if cfg.compute_selector else c.css_path
            crop = rk.crops[i]
            new_fp = Fingerprint(
                sel, fp.page_key, c, rk.snap.doc_size,
                vision.encode_b64(crop) if crop is not None else None,
            )
            if verifying:
                ar = attempt_click(
                    page, c.css_path, expect,
                    click_timeout_ms=cfg.click_timeout_ms,
                    verify_timeout_ms=cfg.verify_timeout_ms,
                    guard_mutations=cfg.guard_mutations,
                )
                clicked, verified, err = ar.clicked, ar.verified, ar.error
                res.blocked_requests += ar.blocked_requests
            else:
                clicked, err = plain_click(page, c.css_path, cfg.click_timeout_ms)
                verified = False
            res.attempts.append(Attempt(c.css_path, sel, float(rk.p[i]), clicked, verified, err, c.gt))
            if clicked and (verified or not verifying):
                res.status = "HEALED_VERIFIED" if verified else "HEALED_UNVERIFIED"
                res.candidate, res.selector, res.css_path = c, sel, c.css_path
                res.verified, res.new_fingerprint = verified, new_fp
                res.latency_ms = _ms(t0)
                return res
        any_clicked = any(a.clicked for a in res.attempts)
        res.status = "REJECTED_VERIFICATION" if any_clicked else "CLICK_FAILED"
        res.latency_ms = _ms(t0)
        return res