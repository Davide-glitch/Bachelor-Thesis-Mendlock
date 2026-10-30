"""CLI runner for the Mendlock benchmark pipeline."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from mendlock.model import Model

from . import collect as collect_mod
from . import corpus, e2e, evaluate as evaluate_mod, train as train_mod


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="bench.run_eval")
    ap.add_argument("step", choices=["generate", "collect", "train", "evaluate", "e2e", "all"])
    ap.add_argument("--out", default="bench/out")
    ap.add_argument("--results", default="results")
    ap.add_argument("--per-cell", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--backend", default="lexical", choices=["lexical", "sbert"])
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--beta", type=float, default=0.10)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--install-model", action="store_true")
    a = ap.parse_args(argv)
    steps = ["generate", "collect", "train", "evaluate", "e2e"] if a.step == "all" else [a.step]
    t0 = time.time()
    for s in steps:
        print(f"== {s}", flush=True)
        if s == "generate":
            recs = corpus.generate(a.out, a.per_cell, a.seed)
            print(f"wrote {len(recs)} cases to {a.out}")
        elif s == "collect":
            collect_mod.collect(a.out, a.backend)
        elif s == "train":
            train_mod.train(a.out, a.results, a.alpha, a.beta, a.k, a.install_model)
        elif s == "evaluate":
            blob = collect_mod.load_cases(a.out)
            model = Model.load(Path(a.results) / "model.json")
            print("wrote", evaluate_mod.evaluate(blob, model, a.results, a.alpha, a.beta, a.k))
        elif s == "e2e":
            e2e.run_e2e(a.out, Path(a.results) / "model.json", a.results, a.limit)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()