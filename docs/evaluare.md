# Experimental Evaluation Plan: Mendlock

**Project:** Mendlock: Verified Self-Healing for End-to-End Web Tests  
**Author:** Davide Luca-Sfia  
**Supervisor:** Assoc. Prof. Dr. Ing. Răzvan Bogdan  

---

## 1. Quantitative Metrics

1. **Heal Rate (%):** Percentage of broken locators (where the target element still exists on the page) that are repaired to the ground-truth element.
2. **False-Commit Rate — FCR (%):** Percentage of all evaluation cases (including `removed` cases) where the healer commits a wrong element.
3. **False Attempt Rate (%):** Percentage of cases where at least one wrong candidate is clicked speculatively before rollback.
4. **Silent False-Pass Rate (%):** Percentage of cases where a wrong element is committed and satisfies a weak/blind post-condition oracle.
5. **Latency (ms):** p50 and p95 end-to-end healing time, plus C++23 vs. Python per-candidate feature extraction latency.
6. **Hardware Edge Telemetry:** Pure compute latency ($\mu\text{s}$), network RTT (ms), and CPU temperature ($^\circ\text{C}$) on Raspberry Pi 5.

---

## 2. Experimental Protocol & Baselines

* **Synthetic Benchmark (`bench/run_eval.py`):** 640 cases across 8 templates and 8 mutation categories (`id_churn`, `class_churn`, `label_shift`, `dom_wrap`, `reorder`, `tag_change`, `restyle`, `removed`), partitioned into `train`, `calib`, `test` (in-distribution), and `test_ood` (unseen templates).
* **Real-Application Case Study (`bench/bench_react.py`):** 5 multi-release scenarios on the React 18 + TypeScript SPA (`?release=v1` vs. `?release=v2`) with 28 interactive controls per view.
* **Baselines Compared:** `no_heal`, `attr_baseline` (fixed threshold $\theta=0.5$), `attr_tuned` (calibrated on `calib`), `gate` (unverified Stage 1+2 model), `verify` (top-1 verified), and `verify_topk` (top-$k$ verified with rollback).
* **Statistical Rigor:** 95% Wilson confidence intervals, Clopper-Pearson 95% exact upper bounds, and paired exact McNemar $p$-values (`mendlock/stats.py`).
