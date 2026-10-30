"""Fits Stage 1 ranker on train split and Stage 2 acceptor + thresholds on calibration split."""
from __future__ import annotations

import shutil
from pathlib import Path

from mendlock.model import DEFAULT_MODEL_PATH, fit_model

from .collect import load_cases


def train(out_dir, results_dir, alpha: float = 0.01, beta: float = 0.10, k: int = 3, install: bool = False):
    blob = load_cases(out_dir)
    cases = blob["cases"]
    train_cases = [c for c in cases if c.split == "train"]
    calib_cases = [c for c in cases if c.split == "calib"]
    model = fit_model(train_cases, calib_cases, blob["features"], alpha, beta, k)
    model.meta["text_backend"] = blob["backend"]
    path = Path(results_dir) / "model.json"
    model.save(path)
    print(
        f"model: tau_commit={model.tau_commit:.3f} tau_attempt={model.tau_attempt:.2f} "
        f"(train {len(train_cases)} cases, calib {len(calib_cases)} cases) -> {path}"
    )
    if install:
        DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, DEFAULT_MODEL_PATH)
        print(f"installed as package default: {DEFAULT_MODEL_PATH}")
    return model