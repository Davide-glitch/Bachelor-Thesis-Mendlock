# Detailed Project Specification: Mendlock

**Student:** Davide Luca-Sfia  
**Supervisor:** Assoc. Prof. Dr. Ing. Răzvan Bogdan  
**Degree Program:** Computers and Information Technology in English (CTI-EN), UPT AC  
**Repository:** [https://github.com/Davide-glitch/Bachelor-Thesis-Mendlock](https://github.com/Davide-glitch/Bachelor-Thesis-Mendlock)  

---

## 1. Context and Problem Statement

Automated end-to-end (E2E) web tests written with Playwright break frequently when front-end interfaces undergo routine refactoring (dynamic CSS hashes, regenerated IDs, DOM wrappers, and element reordering). Existing self-healing tools rely primarily on attribute similarity heuristics, which can silently select look-alike decoy controls and mask real regressions. Mendlock addresses this by committing locator repairs only when a calibrated two-stage statistical confidence model and an explicit post-condition check agree.

## 2. Measurable Objectives and Deliverables

1. **Hybrid Signal Extraction:** Extract 13 structural, geometric, visual (edge-gradient NCC), and semantic features in under 150 ms using Python and a C++23 native shared library (`libmendlock_core.so`).
2. **Calibrated Two-Stage Inference:** Fit a Newton-Raphson / IRLS L2-regularized logistic ranker and a Stage 2 margin acceptor ($p_1 - p_2$) that bounds the empirical False-Commit Rate below $\alpha \le 1\%$.
3. **Transactional Speculative Verification:** Snapshot and restore browser cookies, `localStorage`, and `sessionStorage` while blocking mutating HTTP requests (`POST`/`DELETE`) during trial clicks, followed by exact UTF-8 byte-span AST source patching.
4. **Empirical & Edge Validation:** Evaluate on a 640-case synthetic corpus, a multi-release React 18 + TypeScript application, and an optional ARM64 edge daemon on a Raspberry Pi 5.

## 3. Architecture & Data Flow

1. **Interception (`mendlock/page.py`):** Wraps Playwright `Page.click()`. Healthy selectors record a baseline `Fingerprint`; broken selectors invoke `Healer.heal()`.
2. **Feature Extraction (`mendlock/features.py`, `native/`):** Computes 13 signals across live DOM candidates using C++23 AVX2 routines and MiniLM embeddings.
3. **Decision Policy (`mendlock/model.py`, `mendlock/decision.py`):** Evaluates top-$k$ candidates against calibrated thresholds ($\tau_{\text{commit}}, \tau_{\text{attempt}}$).
4. **Verification & Patching (`mendlock/verify.py`, `mendlock/patcher.py`):** Performs speculative clicks with state rollback on failure and rewrites the Python test file via `ast` on verified success.
