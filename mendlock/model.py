"""Two-stage L2-regularized logistic model fitted via Newton-Raphson (IRLS)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .decision import plan
from .features import FEATURES


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class Logistic:
    """L2-regularized logistic regression fitted with Newton-Raphson / IRLS."""

    def __init__(self, l2: float = 1.0):
        self.l2 = l2
        self.mu = self.sd = self.w = None
        self.b = 0.0

    def fit(self, X, y, iters: int = 60, feature_penalties: np.ndarray | None = None):
        X, y = np.asarray(X, float), np.asarray(y, float)
        self.mu = X.mean(0)
        self.sd = X.std(0)
        self.sd[self.sd < 1e-9] = 1.0
        n, d = X.shape
        A = np.hstack([(X - self.mu) / self.sd, np.ones((n, 1))])
        rate = float(np.clip(y.mean(), 1e-4, 1 - 1e-4))
        theta = np.zeros(d + 1)
        theta[-1] = np.log(rate / (1 - rate))
        pen = np.full(d, self.l2) if feature_penalties is None else np.asarray(feature_penalties, float)
        R = np.diag(list(pen) + [1e-3])

        def loss(th):
            z = np.clip(A @ th, -40.0, 40.0)
            return float(np.sum(np.logaddexp(0.0, z) - y * z) + 0.5 * (th @ (R @ th)))

        cur_loss = loss(theta)
        for _ in range(iters):
            p = _sigmoid(A @ theta)
            g = A.T @ (p - y) + R @ theta
            H = A.T @ (A * (p * (1.0 - p))[:, None]) + R + 1e-6 * np.eye(d + 1)
            step = np.linalg.solve(H, g)
            scale = 1.0
            while scale > 1e-4:
                cand = theta - scale * step
                cand_loss = loss(cand)
                if cand_loss <= cur_loss:
                    theta, cur_loss = cand, cand_loss
                    break
                scale *= 0.5
            if np.abs(scale * step).max() < 1e-7:
                break
        self.w, self.b = theta[:-1], float(theta[-1])
        return self

    def decision(self, X):
        return ((np.asarray(X, float) - self.mu) / self.sd) @ self.w + self.b

    def predict_proba(self, X):
        return _sigmoid(self.decision(X))

    def to_dict(self):
        return {"l2": self.l2, "mu": self.mu.tolist(), "sd": self.sd.tolist(), "w": self.w.tolist(), "b": self.b}

    @classmethod
    def from_dict(cls, d):
        m = cls(d["l2"])
        m.mu, m.sd, m.w, m.b = np.array(d["mu"]), np.array(d["sd"]), np.array(d["w"]), float(d["b"])
        return m


@dataclass
class Model:
    features: list
    ranker: Logistic
    acceptor: Logistic | None = None
    tau_commit: float = 0.5
    tau_attempt: float = 0.2
    meta: dict = field(default_factory=dict)

    def probs(self, X) -> np.ndarray:
        X = np.asarray(X, float)
        if X.shape[0] == 0:
            return np.zeros(0)
        idx = [FEATURES.index(f) for f in self.features]
        return self.ranker.predict_proba(X[:, idx])

    def confidence(self, p_sorted) -> float:
        p1 = float(p_sorted[0])
        p2 = float(p_sorted[1]) if len(p_sorted) > 1 else 0.0
        if self.acceptor is None:
            return p1
        z = np.array([[float(_logit(np.array([p1]))[0]), p1 - p2]])
        return float(self.acceptor.predict_proba(z)[0])

    def to_dict(self) -> dict:
        return {
            "features": self.features,
            "ranker": self.ranker.to_dict(),
            "acceptor": self.acceptor.to_dict() if self.acceptor else None,
            "tau_commit": self.tau_commit,
            "tau_attempt": self.tau_attempt,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Model":
        return cls(
            d["features"],
            Logistic.from_dict(d["ranker"]),
            Logistic.from_dict(d["acceptor"]) if d.get("acceptor") else None,
            d["tau_commit"],
            d["tau_attempt"],
            d.get("meta", {}),
        )

    def save(self, path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "Model":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


DEFAULT_MODEL_PATH = Path(__file__).parent / "data" / "default_model.json"


def load_default_model() -> Model:
    if not DEFAULT_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"{DEFAULT_MODEL_PATH} not found. Train one with: python -m bench.run_eval all --install-model"
        )
    return Model.load(DEFAULT_MODEL_PATH)


def choose_tau_commit(conf, correct, alpha: float, floor: float = 0.5) -> float:
    conf, correct = np.asarray(conf, float), np.asarray(correct, bool)
    n = len(conf)
    if n == 0:
        return 1.01
    uniq = np.unique(conf)[::-1]
    best_idx = -1
    false = 0
    for u_i, u in enumerate(uniq):
        m = conf == u
        false += int((~correct[m]).sum())
        if false / n <= alpha:
            best_idx = u_i
        else:
            break
    if best_idx < 0:
        return 1.01
    lowest_accepted = uniq[best_idx]
    next_lower = uniq[best_idx + 1] if best_idx + 1 < len(uniq) else lowest_accepted - 1e-3
    return float(max(floor, (lowest_accepted + next_lower) / 2))


def choose_tau_attempt(model: Model, calib: list, beta: float, k: int, floor: float = 0.05) -> float:
    info = [(model.probs(c.X), c) for c in calib if len(c.y)]
    n_all = max(len(calib), 1)
    for tau in np.round(np.arange(floor, 1.0, 0.01), 2):
        wrong_cases = 0
        for p, c in info:
            tried = []
            for i in plan(model, p, "verify_topk", k, tau_attempt=float(tau)):
                tried.append(i)
                if c.oracle[i]:
                    break
            wrong_cases += any(not c.y[i] for i in tried)
        if wrong_cases / n_all <= beta:
            return float(tau)
    return 1.01


def fit_model(train: list, calib: list, features: list | None = None, alpha: float = 0.01,
              beta: float = 0.10, k: int = 3, l2: float = 2.0, tau_floor: float = 0.5) -> Model:
    features = list(features or FEATURES)
    idx = [FEATURES.index(f) for f in features]
    tr = [c for c in train if len(c.y)]
    # Stronger L2 penalty on pos_sim so static training layouts do not over-penalize reordered elements
    penalties = np.array([12.0 if f == "pos_sim" else l2 for f in features], dtype=float)
    ranker = Logistic(l2).fit(
        np.vstack([c.X[:, idx] for c in tr]),
        np.concatenate([c.y for c in tr]),
        feature_penalties=penalties,
    )
    model = Model(features, ranker)

    Z, t, confs_input = [], [], []
    for c in calib:
        if not len(c.y):
            confs_input.append(None)
            continue
        p = model.probs(c.X)
        order = np.argsort(-p, kind="stable")
        ps = p[order]
        p2 = ps[1] if len(ps) > 1 else 0.0
        Z.append([float(_logit(np.array([ps[0]]))[0]), float(ps[0] - p2)])
        t.append(bool(c.y[order[0]]))
        confs_input.append(bool(c.y[order[0]]))
    n_pos, n_neg = sum(t), len(t) - sum(t)
    if n_pos >= 8 and n_neg >= 8:
        model.acceptor = Logistic(0.1).fit(np.array(Z), np.array(t))
        acceptor_note = "fitted"
    else:
        acceptor_note = f"skipped ({n_pos} pos / {n_neg} neg) -> confidence = p1"

    confs, correct = [], []
    for c, ok in zip(calib, confs_input):
        if ok is None:
            confs.append(0.0)
            correct.append(False)
            continue
        p = model.probs(c.X)
        confs.append(model.confidence(np.sort(p)[::-1]))
        correct.append(ok)
    model.tau_commit = choose_tau_commit(confs, correct, alpha, tau_floor)
    if all(c.oracle is not None for c in calib):
        model.tau_attempt = choose_tau_attempt(model, calib, beta, k)
    model.meta = {
        "alpha": alpha, "beta": beta, "k": k, "l2": l2, "tau_floor": tau_floor,
        "n_train_cases": len(train), "n_train_candidates": int(sum(len(c.y) for c in train)),
        "n_calib_cases": len(calib), "acceptor": acceptor_note,
        "weights": {f: round(float(w), 4) for f, w in zip(features, ranker.w)},
    }
    return model