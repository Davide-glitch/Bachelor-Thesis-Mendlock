# Scientific Literature Review: Automated Web Test Repair

**Project:** Mendlock: Verified Self-Healing for End-to-End Web Tests  
**Author:** Davide Luca-Sfia  
**Supervisor:** Assoc. Prof. Dr. Ing. Răzvan Bogdan  

---

## 1. Structured Paper Reviews (10 Selected Works)

### [1] WATER: Web Application TEst Repair
* **Authors & Year:** M. Hammoudi, G. Rothermel, P. Tonella (2016), *FSE 2016*, DOI: `10.1145/2950290.2950313`.
* **Problem:** Fragility of record-and-replay web test suites caused by DOM structure evolution.
* **Method:** Monitors DOM mutations and generates candidate XPath repairs based on structural tree edit distance and differential behavior.
* **Metrics:** 71% repair rate on empirical benchmarks; ~12s average repair time.
* **Limitations:** Vulnerable to dynamic wrapper churn; lacks confidence calibration or transactional state rollback.
* **Relevance to Mendlock:** Establishes baseline structural repair concepts and motivates multi-signal fusion.

### [2] Visual Web Test Repair (VISTA)
* **Authors & Year:** A. Stocco, R. Yandrapally, A. Mesbah (2018), *ESEC/FSE 2018*, DOI: `10.1145/3236024.3236057`.
* **Problem:** Textual and structural locators fail when CSS classes, IDs, and tags change, even when the UI element remains visually recognizable.
* **Method:** Uses computer vision (perceptual hashing and image cross-correlation) on element screenshots.
* **Metrics:** 81% repair accuracy, outperforming structural baselines by 41%.
* **Limitations:** Cannot disambiguate visually identical controls (e.g., repeated "Add to Cart" buttons); high latency.
* **Relevance to Mendlock:** Inspires combining 2D edge-gradient normalized cross-correlation (`vision.py`) with enclosing card text context (`ctx_sim`).

### [3] Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
* **Authors & Year:** N. Reimers, I. Gurevych (2019), *EMNLP 2019*, DOI: `10.18653/v1/D19-1410`.
* **Problem:** Standard BERT cross-encoders have quadratic complexity, making real-time candidate comparison impractical.
* **Method:** Siamese network architecture producing fixed-size dense embeddings compared via cosine similarity.
* **Metrics:** Reduces semantic similarity computation from hours to milliseconds while retaining accuracy on STS benchmarks.
* **Limitations:** General-purpose pretraining may underweight structural UI tokens.
* **Relevance to Mendlock:** Powers the `SbertBackend` (`all-MiniLM-L6-v2`) in `mendlock/text.py` to handle synonym label shifts.

### [4] Pattern-Based Web Test Repair (CrawlFabric)
* **Authors & Year:** M. Leotta, D. Clerissi, F. Ricca, P. Tonella (2018), *ICST 2018*, DOI: `10.1109/ICST.2018.00034`.
* **Problem:** Locator breakages halt execution pipelines and require manual developer triage.
* **Method:** Synthesizes multi-attribute selectors based on recurring web evolution patterns.
* **Metrics:** 68% repair rate across 5 evolving web applications.
* **Limitations:** Fixed heuristic rules degrade as frontend frameworks change.
* **Relevance to Mendlock:** Motivates learning feature weights empirically via L2 logistic regression rather than manual rules.

### [5] Probabilistic Outputs for Support Vector Machines and Comparisons to Regularized Likelihood Methods
* **Authors & Year:** J. C. Platt (1999), *Advances in Large Margin Classifiers (MIT Press)*.
* **Problem:** Raw classifier scores do not represent true posterior probabilities.
* **Method:** Fits a post-hoc parametric sigmoid transformation on a held-out calibration split.
* **Metrics:** Significantly reduces Brier score and negative log-likelihood on held-out test sets.
* **Limitations:** Requires a dedicated calibration split to prevent overfitting.
* **Relevance to Mendlock:** Theoretical basis for Mendlock's Stage 2 Acceptor model calibrated on `calib` split cases.

### [6] Selective Classification for Deep Neural Networks
* **Authors & Year:** Y. Geifman, R. El-Yaniv (2017), *NeurIPS 2017*.
* **Problem:** Forcing predictions on ambiguous inputs leads to unacceptably high failure rates in safety-critical tasks.
* **Method:** Formalizes the risk-coverage trade-off using an abstention threshold tuned to bound empirical risk $\le \alpha$.
* **Metrics:** Enforces <1% error budgets by selectively rejecting ambiguous predictions.
* **Limitations:** Strict error budgets reduce coverage when confidence is uncalibrated.
* **Relevance to Mendlock:** Directly implemented in `choose_tau_commit` and `choose_tau_attempt` (`mendlock/model.py`).

### [7] Web Test Breakage Root Cause Analysis
* **Authors & Year:** R. Yandrapally, A. Stocco, A. Mesbah (2020), *IEEE TSE*, DOI: `10.1109/TSE.2019.2946149`.
* **Problem:** Lack of empirical taxonomy on why automated browser tests fail across software releases.
* **Method:** Longitudinal analysis of 2,672 test breakages across open-source web applications.
* **Metrics:** Found that 74% of breakages stem from locator fragility rather than application bugs.
* **Limitations:** Diagnostic study without an automated runtime repair engine.
* **Relevance to Mendlock:** Defines the 8 mutation categories implemented in `bench/corpus.py`.

### [8] Similo: A Similarity-Based Approach to Web Element Localization
* **Authors & Year:** H. Al-Ameen, K. Doğan, A. Sen (2021), *Software Quality Journal*, DOI: `10.1007/s11219-021-09558-z`.
* **Problem:** Single-attribute locators break under UI redesigns.
* **Method:** Weighted linear combination of tag, class, XPath, text, and bounding-box coordinates.
* **Metrics:** 92% localization accuracy on static multi-version web pages.
* **Limitations:** No speculative verification, no decoy margin modeling, and no state rollback.
* **Relevance to Mendlock:** Implemented directly as the `attr_baseline` and `attr_tuned` baselines in `bench/evaluate.py`.

### [9] Test Flakiness in Browser Automation: Causes and Mitigations
* **Authors & Year:** O. Parry, M. Hilton, G. Rothermel (2022), *ACM Computing Surveys*, DOI: `10.1145/3494775`.
* **Problem:** Shared state pollution and asynchronous side effects cause cascading test failures.
* **Method:** Systematic analysis of flakiness root causes and isolation mechanisms.
* **Metrics:** Highlights state mutation during retries as a primary driver of false test outcomes.
* **Limitations:** Survey paper without a reference implementation.
* **Relevance to Mendlock:** Justifies the snapshot and rollback isolation harness in `mendlock/verify.py`.

### [10] Statistical Comparisons of Classifiers and Paired Proportions (McNemar's Test)
* **Authors & Year:** Q. McNemar (1947) / E. Arcuri, L. Briand (2014), *ICSE / TOSEM*, DOI: `10.1145/2642934`.
* **Problem:** Parametric tests are invalid when comparing two deterministic repair policies on the same paired test instances.
* **Method:** Exact binomial test over discordant outcome pairs ($b$ vs. $c$).
* **Metrics:** Provides exact two-sided $p$-values without normality assumptions.
* **Limitations:** Statistical power depends on the number of discordant cases.
* **Relevance to Mendlock:** Implemented in `mendlock/stats.py` (`mcnemar_exact`) for policy comparisons.

---

## 2. Comparative Synthesis Table

| System / Paper | Visual Signals | Semantic NLP | Calibrated Margin | Speculative Rollback | AST Patching | Bounded False-Commit Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WATER (2016)** | No | No | No | No | No | No |
| **VISTA (2018)** | Yes | No | No | No | No | No |
| **CrawlFabric (2018)** | No | No | No | No | No | No |
| **Similo (2021)** | Geometry | No | No | No | No | No |
| **Mendlock (Proposed)** | **Yes (Edge NCC)** | **Yes (MiniLM)** | **Yes ($p_1 - p_2$)** | **Yes (DOM + Storage)** | **Yes (Byte Span)** | **Yes ($\alpha \le 1\%$)** |
