# Bi-Weekly Academic Activity Calendar (2026–2027)

**Student:** Davide Luca-Sfia  
**Supervisor:** Assoc. Prof. Dr. Ing. Răzvan Bogdan  
**Repository:** [https://github.com/Davide-glitch/Bachelor-Thesis-Mendlock](https://github.com/Davide-glitch/Bachelor-Thesis-Mendlock)

> **Status Legend:** `N` = Not Started, `L` = In Progress, `F` = Completed

| Interval         | Target Milestone                      | Specific Tasks & Activities                                                                               | Deliverables & Verification Evidence                                       | Status |
| :--------------- | :------------------------------------ | :-------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------- | :----: |
| **01 / S1–S2**   | Problem Definition & Repository Setup | Define project scope (Mendlock); initialize repository layout and documentation structure.                | `README.md` and `docs/proiect.md` committed.                               | **F**  |
| **02 / S3–S4**   | Scientific Literature Review (Part 1) | Review first 5 papers on web test repair (WATER, VISTA, Similo, CrawlFabric).                             | Reading notes 1–5 in `docs/literatura.md`.                                 | **F**  |
| **03 / S5–S6**   | Scientific Literature Review (Part 2) | Review 5 papers on calibration, Sentence-BERT, selective prediction, and McNemar tests.                   | Reading notes 6–10 and comparative table in `docs/literatura.md`.          | **F**  |
| **04 / S7–S8**   | Synthesis & Positioning               | Formalize threat model (look-alike decoys, vacuous oracles) and error budgets ($\alpha, \beta$).          | Positioning section in `docs/literatura.md`.                               | **F**  |
| **05 / S9–S10**  | Detailed Architecture Design          | Specify 13-feature vector, C ABI interface, and transactional state rollback contract.                    | Architecture diagrams in `docs/proiect.md`.                                | **F**  |
| **06 / S11–S12** | Prototype & Build Environment         | Set up Python virtual environment, CMake C++23 build pipeline, and React 18 + TS SUT.                     | `CMakeLists.txt`, `requirements.txt`, `sut-react/`.                        | **F**  |
| **07 / S13–S14** | Core Model Implementation             | Implement Newton-Raphson / IRLS logistic regression and Stage 2 margin calibrator.                        | `mendlock/model.py` and `tests/test_units.py`.                             | **F**  |
| **08 / S15–S16** | Native C++23 Kernel Integration       | Implement trigram cosine, Levenshtein ratio, and AVX2 visual NCC in C++23; link via `ctypes`.             | `native/src/mendlock_core.cpp` and `bench/bench_native.py`.                | **F**  |
| **09 / S17–S18** | Speculative Verification & Rollback   | Implement DOM/storage snapshotting, `mutation_guard` HTTP blocker, and AST byte-span patcher.             | `mendlock/verify.py`, `mendlock/patcher.py`, `tests/test_browser.py`.      | **F**  |
| **10 / S19–S20** | Evaluation Plan Finalization          | Define statistical metrics, Wilson intervals, and experimental protocols.                                 | `docs/evaluare.md` and `mendlock/stats.py`.                                | **F**  |
| **11 / S21–S22** | Preliminary Testing & Corpus Gen      | Generate 640-case synthetic corpus and verify end-to-end demo execution.                                  | `bench/corpus.py` and `examples/demo.py`.                                  | **L**  |
| **12 / S23–S24** | Model Training & Calibration          | Collect browser features, fit Stage 1 & 2 models, and tune $\tau_{\text{commit}}, \tau_{\text{attempt}}$. | `mendlock/data/default_model.json`.                                        | **N**  |
| **13 / S25–S26** | Comparative & Ablation Experiments    | Run policy comparisons, feature group ablations, and React SUT case study.                                | `results/summary.md`, `results/tables.tex`, `results/react_case_study.md`. | **N**  |
| **14 / S27–S28** | Hardware Edge Evaluation & Analysis   | Benchmark C++23 edge daemon on Raspberry Pi 5 and analyze statistical significance.                       | `bench/bench_edge.py` results.                                             | **N**  |
| **15 / S29–S30** | Thesis Manuscript Drafting            | Write thesis chapters and integrate generated LaTeX tables and architecture figures.                      | Complete thesis draft PDF.                                                 | **N**  |
| **16 / S31–S32** | Final Validation & Defense Prep       | Final code audit, reproducibility check, and defense presentation slides.                                 | Final GitHub release and slide deck.                                       | **N**  |
