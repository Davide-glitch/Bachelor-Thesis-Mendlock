"""Candidate selection policy shared between live execution and offline evaluation."""
from __future__ import annotations

import numpy as np

MODES = ("gate", "verify", "verify_topk")


def plan(model, p, mode: str, max_attempts: int = 3, tau_attempt: float | None = None) -> list[int]:
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")
    p = np.asarray(p, float)
    if p.size == 0:
        return []
    order = np.argsort(-p, kind="stable")
    ps = p[order]
    if mode in ("gate", "verify"):
        return [int(order[0])] if model.confidence(ps) >= model.tau_commit else []
    tau = model.tau_attempt if tau_attempt is None else tau_attempt
    return [int(i) for i, pi in zip(order[:max_attempts], ps[:max_attempts]) if pi >= tau]