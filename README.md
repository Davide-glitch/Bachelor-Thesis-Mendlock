# Mendlock: Verified Self-Healing for End-to-End Web Tests

**Author:** Davide Luca-Sfia  
**Supervisor:** Assoc. Prof. Dr. Ing. Răzvan Bogdan  
**Institution:** Politehnica University of Timișoara, Faculty of Automation and Computers, CTI-EN  
**Academic Year:** 2026–2027  

---

## 1. Overview

End-to-end (E2E) browser automation tests written with frameworks such as Playwright suffer from fragility caused by *selector rot*. Frontend updates frequently regenerate class names, dynamic framework IDs, and layout wrappers, causing locators to fail even when functional behavior remains intact. Existing repair tools rely primarily on uncalibrated attribute similarity, risking *silent false heals* on look-alike decoy elements.

**Mendlock** is an automated test repair framework for Playwright that repairs broken locators only when a calibrated statistical confidence model and a live browser post-condition check agree, rolling back browser state if a trial interaction fails and rewriting the broken selector in the test source file.

---

## 2. Repository Layout

This repository follows the official UPT AC 2026–2027 thesis structure:

```text
Bachelor-Thesis-Mendlock/
├── README.md                 # Entry point, build commands, and overview
├── requirements.txt          # Python runtime dependencies
├── docs/
│   ├── proiect.md            # Detailed topic definition, objectives, architecture
│   ├── literatura.md         # 10 critical paper reviews and comparative positioning
│   ├── evaluare.md           # Metrics, experimental protocol, baselines, telemetry
│   └── plan-bilunar.md       # Bi-weekly progress calendar (S1–S32)
├── mendlock/                 # Python core package (models, AST patcher, page decorator)
│   ├── native_bridge.py      # ctypes loader with pure Python fallback
│   └── data/                 # Serialized default model parameters
├── native/                   # C++23 acceleration library and edge daemon
├── sut-react/                # Target System Under Test: React 18 + TypeScript SPA
├── bench/                    # Benchmarks, synthetic corpus generator, and CLI runners
├── tests/                    # Unit and Playwright integration tests
└── results/                  # Generated CSV sweeps, LaTeX tables, and reports
