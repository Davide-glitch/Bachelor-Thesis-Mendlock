"""Offline evaluation, ablation studies, threshold sweeps, and LaTeX table generation."""
from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import numpy as np

from mendlock.decision import plan
from mendlock.features import FEATURES, GROUPS
from mendlock.model import Model, choose_tau_commit, fit_model
from mendlock.stats import exact_upper, fmt_rate, mcnemar_exact

METHODS = ["no_heal", "attr_baseline", "attr_tuned", "gate", "verify", "verify_topk"]
LABELS = {
    "no_heal": "No healing",
    "attr_baseline": "Attribute similarity, fixed threshold",
    "attr_tuned": "Attribute similarity, tuned threshold",
    "gate": "Learned + calibrated gate (no verification)",
    "verify": "Learned gate + verification",
    "verify_topk": "Learned, verified top-k",
}
ATTR_WEIGHTS = {
    "tag_match": 0.30, "id_sim": 0.25, "class_sim": 0.15,
    "text_sim": 0.15, "path_sim": 0.10, "pos_sim": 0.05,
}
ATTR_THETA = 0.5


def attr_scores(X: np.ndarray) -> np.ndarray:
    return sum(w * X[:, FEATURES.index(f)] for f, w in ATTR_WEIGHTS.items())


def tune_attr_theta(calib: list, alpha: float) -> float:
    conf, correct = [], []
    for c in calib:
        if not len(c.y):
            conf.append(0.0)
            correct.append(False)
            continue
        s = attr_scores(c.X)
        conf.append(float(s.max()))
        correct.append(bool(c.y[int(np.argmax(s))]))
    return choose_tau_commit(conf, correct, alpha, floor=0.0)


def run_method(method: str, c, model: Model, theta_tuned: float, k: int = 3):
    attempted, committed = [], None
    if not len(c.y) or method == "no_heal":
        return attempted, committed
    if method in ("attr_baseline", "attr_tuned"):
        s = attr_scores(c.X)
        i = int(np.argmax(s))
        if s[i] >= (ATTR_THETA if method == "attr_baseline" else theta_tuned):
            attempted, committed = [i], i
        return attempted, committed
    for i in plan(model, model.probs(c.X), method, k):
        attempted.append(i)
        if method == "gate" or c.oracle[i]:
            committed = i
            break
    return attempted, committed


def _row(c, method, attempted, committed) -> dict:
    wrong = committed is not None and not c.y[committed]
    return {
        "case": c.id, "split": c.split, "template": c.template, "category": c.category,
        "oracle_blind": int(c.oracle_blind), "has_target": int(c.has_target), "method": method,
        "n_attempts": len(attempted), "committed": int(committed is not None),
        "correct": int(committed is not None and bool(c.y[committed])), "wrong": int(wrong),
        "wrong_attempt": int(any(not c.y[i] for i in attempted)),
        "silent": int(wrong and bool(c.oracle[committed])),
    }


def evaluate_methods(cases: list, model: Model, theta: float, methods=METHODS) -> dict:
    k = model.meta.get("k", 3)
    return {m: [_row(c, m, *run_method(m, c, model, theta, k)) for c in cases] for m in methods}


def summarize(rows: list) -> dict:
    s = {key: sum(r[key] for r in rows) for key in ("correct", "wrong", "wrong_attempt", "silent", "has_target")}
    s["N"] = len(rows)
    s["committed"] = s["correct"] + s["wrong"]
    return s


def _md(headers: list, body: list) -> list:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return lines + ["| " + " | ".join(str(x) for x in r) + " |" for r in body]


def headline(res: dict, methods=METHODS) -> list:
    out = []
    for m in methods:
        s = summarize(res[m])
        out.append([
            LABELS[m], fmt_rate(s["correct"], s["has_target"]), fmt_rate(s["wrong"], s["N"]),
            fmt_rate(s["wrong_attempt"], s["N"]), fmt_rate(s["silent"], s["N"]),
            fmt_rate(s["correct"], s["committed"]),
        ])
    return out


HEAD = ["Method", "Heal rate %", "False-commit rate %", "False attempts %", "Silent false-pass %", "Precision %"]


def latex_table(caption: str, label: str, body: list) -> str:
    def esc(x):
        return str(x).replace("%", "\\%").replace("&", "\\&")

    lines = [
        "\\begin{table}[htbp]", "  \\centering", f"  \\caption{{{caption}}}", f"  \\label{{{label}}}",
        "  \\small", "  \\begin{tabular}{lccccc}", "    \\toprule",
        "    " + " & ".join(f"\\textbf{{{esc(h)}}}" for h in HEAD) + " \\\\", "    \\midrule",
    ]
    lines += ["    " + " & ".join(esc(x) for x in r) + " \\\\" for r in body]
    return "\n".join(lines + ["    \\bottomrule", "  \\end{tabular}", "\\end{table}"])


def by_category(res: dict, methods: list) -> list:
    cats = sorted({r["category"] for r in res[methods[0]]})
    body = []
    for cat in cats:
        row = [cat]
        for m in methods:
            rs = [r for r in res[m] if r["category"] == cat]
            s = summarize(rs)
            row.append(
                f"{100 * s['wrong'] / max(s['N'], 1):.0f}% wrong"
                if cat == "removed"
                else f"{100 * s['correct'] / max(s['has_target'], 1):.0f}%"
            )
        body.append(row)
    return body


def paired(res: dict, a: str, b: str, key: str) -> tuple:
    ra = {r["case"]: r[key] for r in res[a]}
    rb = {r["case"]: r[key] for r in res[b]}
    only_a = sum(1 for k in ra if ra[k] and not rb[k])
    only_b = sum(1 for k in ra if rb[k] and not ra[k])
    return only_a, only_b, mcnemar_exact(only_a, only_b)


def calibration_table(model: Model, cases: list, bins=(0, 0.2, 0.4, 0.6, 0.8, 1.0001)) -> list:
    conf, ok = [], []
    for c in cases:
        if len(c.y):
            p = model.probs(c.X)
            order = np.argsort(-p, kind="stable")
            conf.append(model.confidence(p[order]))
            ok.append(bool(c.y[order[0]]))
    conf, ok = np.array(conf), np.array(ok)
    body = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf >= lo) & (conf < hi)
        if m.any():
            body.append([f"[{lo:.1f}, {min(hi, 1.0):.1f})", int(m.sum()), f"{conf[m].mean():.2f}", f"{ok[m].mean():.2f}"])
    return body


def sweep(cases: list, model: Model, grid) -> list:
    rows = []
    for tau in grid:
        mdl = dataclasses.replace(model, tau_commit=float(tau), tau_attempt=float(tau))
        res = evaluate_methods(cases, mdl, 0.0, methods=["gate", "verify", "verify_topk"])
        for m, rs in res.items():
            s = summarize(rs)
            rows.append({
                "method": m, "tau": round(float(tau), 3),
                "heal_rate": s["correct"] / max(s["has_target"], 1),
                "false_commit": s["wrong"] / s["N"],
                "false_attempt": s["wrong_attempt"] / s["N"],
                "silent_false_pass": s["silent"] / s["N"],
            })
    return rows


def ablation(train: list, calib: list, test: list, alpha: float, beta: float, k: int) -> list:
    variants = [("full model", FEATURES)] + [
        (f"without {g}", [f for f in FEATURES if f not in fs]) for g, fs in GROUPS.items()
    ]
    out = []
    for name, feats in variants:
        mdl = fit_model(train, calib, feats, alpha, beta, k)
        res = evaluate_methods(test, mdl, 0.0, methods=["gate", "verify", "verify_topk"])
        row = [name]
        for m in ("gate", "verify", "verify_topk"):
            s = summarize(res[m])
            row += [f"{100 * s['correct'] / max(s['has_target'], 1):.1f}", f"{100 * s['wrong'] / s['N']:.1f}"]
        out.append(row)
    return out


def write_csv(path: Path, rows: list) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def evaluate(cases_blob: dict, model: Model, results_dir, alpha: float, beta: float, k: int) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    cases = cases_blob["cases"]
    split = {s: [c for c in cases if c.split == s] for s in ("train", "calib", "test", "test_ood")}
    theta = tune_attr_theta(split["calib"], alpha)
    sets = {"test": split["test"], "test_ood": split["test_ood"], "test+test_ood": split["test"] + split["test_ood"]}
    res = {name: evaluate_methods(cs, model, theta) for name, cs in sets.items()}

    L = [
        "# Mendlock Evaluation Summary", "",
        f"Corpus: {len(cases)} usable cases (" + ", ".join(f"{s}: {len(v)}" for s, v in split.items()) + "); "
        f"excluded during collection: {cases_blob['skipped'] or 'none'}; text backend: `{cases_blob['backend']}`.", "",
        f"**Model.** tau_commit = {model.tau_commit:.3f}, tau_attempt = {model.tau_attempt:.2f} "
        f"(alpha = {alpha:.0%}, beta = {beta:.0%}, top-k = {k}); tuned attribute threshold = {theta:.3f}.", "",
    ]
    tex = []
    for name, title in (
        ("test", "Held-out cases, same templates"),
        ("test_ood", "Held-out cases, unseen templates"),
        ("test+test_ood", "All held-out cases"),
    ):
        body = headline(res[name])
        L += [f"## {title} (n = {len(sets[name])})", ""] + _md(HEAD, body) + [""]
        if name != "test+test_ood":
            tex.append(latex_table(
                f"Mendlock evaluation: {title.lower()} (n={len(sets[name])}); 95\\% Wilson intervals.",
                f"tab:eval-{name.replace('+', '-').replace('_', '-')}",
                body,
            ))

    allr = res["test+test_ood"]
    L += ["## Design target vs measurement", ""]
    body = []
    for m in ("attr_tuned", "gate", "verify", "verify_topk"):
        s = summarize(allr[m])
        body.append([
            LABELS[m], f"{s['wrong']}/{s['N']}",
            f"{100 * s['wrong'] / s['N']:.2f}", f"{100 * exact_upper(s['wrong'], s['N']):.2f}",
        ])
    L += _md(["Method", "False commits", "Rate %", "95% upper bound %"], body) + [""]

    L += ["## By category", ""]
    ms = ["attr_tuned", "gate", "verify", "verify_topk"]
    L += _md(["Category"] + [LABELS[m] for m in ms], by_category(allr, ms)) + [""]

    L += ["## Strong vs weak post-condition", ""]
    body = []
    for m in ("gate", "verify", "verify_topk"):
        row = [LABELS[m]]
        for blind in (0, 1):
            rs = [r for r in allr[m] if r["oracle_blind"] == blind]
            s = summarize(rs)
            row += [f"{s['wrong']}/{s['N']}", f"{s['silent']}/{s['N']}"]
        body.append(row)
    L += _md(["Method", "strong: false commits", "strong: silent false-pass", "weak: false commits", "weak: silent false-pass"], body) + [""]

    L += ["## Paired comparisons (exact McNemar)", ""]
    body = []
    for a, b, key, what in (
        ("gate", "verify", "wrong", "false commits"),
        ("verify", "verify_topk", "correct", "correct heals"),
        ("attr_tuned", "gate", "correct", "correct heals"),
        ("attr_tuned", "gate", "wrong", "false commits"),
    ):
        oa, ob, p = paired(allr, a, b, key)
        body.append([f"{LABELS[a]} vs {LABELS[b]}", what, oa, ob, f"{p:.4f}"])
    L += _md(["Comparison", "Outcome", "only first", "only second", "p-value"], body) + [""]

    L += ["## Calibration of confidence", ""]
    L += _md(["Confidence bin", "Cases", "Mean confidence", "Observed accuracy"], calibration_table(model, sets["test+test_ood"])) + [""]

    abl = ablation(split["train"], split["calib"], sets["test+test_ood"], alpha, beta, k)
    L += ["## Ablation study", ""]
    L += _md(["Variant", "gate heal", "gate FCR", "verify heal", "verify FCR", "top-k heal", "top-k FCR"], abl) + [""]

    L += ["## Learned weights (standardised features)", ""]
    L += _md(["Feature", "Weight"], [[f, w] for f, w in model.meta.get("weights", {}).items()]) + [""]

    (results_dir / "summary.md").write_text("\n".join(L), encoding="utf-8")
    (results_dir / "tables.tex").write_text("\n\n".join(tex) + "\n", encoding="utf-8")
    write_csv(results_dir / "per_case.csv", [r for m in METHODS for r in allr[m]])
    write_csv(results_dir / "sweep.csv", sweep(sets["test+test_ood"], model, np.round(np.arange(0.05, 1.0, 0.05), 2)))
    return results_dir