# Mendlock Evaluation Summary

Corpus: 640 usable cases (train: 240, calib: 96, test: 144, test_ood: 160); excluded during collection: none; text backend: `lexical`.

**Model.** tau_commit = 0.977, tau_attempt = 0.05 (alpha = 1%, beta = 10%, top-k = 3); tuned attribute threshold = 0.847.

## Held-out cases, same templates (n = 144)

| Method | Heal rate % | False-commit rate % | False attempts % | Silent false-pass % | Precision % |
|---|---|---|---|---|---|
| No healing | 0.0 [0.0, 3.0] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | n/a |
| Attribute similarity, fixed threshold | 48.4 [39.9, 57.1] | 57.6 [49.5, 65.4] | 57.6 [49.5, 65.4] | 11.8 [7.5, 18.1] | 42.4 [34.6, 50.5] |
| Attribute similarity, tuned threshold | 16.7 [11.2, 24.1] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 100.0 [84.5, 100.0] |
| Learned + calibrated gate (no verification) | 72.2 [63.8, 79.3] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 100.0 [95.9, 100.0] |
| Learned gate + verification | 72.2 [63.8, 79.3] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 0.0 [0.0, 2.6] | 100.0 [95.9, 100.0] |
| Learned, verified top-k | 98.4 [94.4, 99.6] | 0.7 [0.1, 3.8] | 6.2 [3.3, 11.5] | 0.7 [0.1, 3.8] | 99.2 [95.6, 99.9] |

## Held-out cases, unseen templates (n = 160)

| Method | Heal rate % | False-commit rate % | False attempts % | Silent false-pass % | Precision % |
|---|---|---|---|---|---|
| No healing | 0.0 [0.0, 2.7] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | n/a |
| Attribute similarity, fixed threshold | 63.6 [55.3, 71.1] | 44.4 [36.9, 52.1] | 44.4 [36.9, 52.1] | 11.9 [7.7, 17.8] | 55.6 [47.9, 63.1] |
| Attribute similarity, tuned threshold | 21.4 [15.4, 28.9] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 100.0 [88.6, 100.0] |
| Learned + calibrated gate (no verification) | 79.3 [71.8, 85.2] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 100.0 [96.7, 100.0] |
| Learned gate + verification | 79.3 [71.8, 85.2] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 0.0 [0.0, 2.3] | 100.0 [96.7, 100.0] |
| Learned, verified top-k | 100.0 [97.3, 100.0] | 1.2 [0.3, 4.4] | 8.1 [4.8, 13.4] | 1.2 [0.3, 4.4] | 98.6 [95.0, 99.6] |

## All held-out cases (n = 304)

| Method | Heal rate % | False-commit rate % | False attempts % | Silent false-pass % | Precision % |
|---|---|---|---|---|---|
| No healing | 0.0 [0.0, 1.4] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | n/a |
| Attribute similarity, fixed threshold | 56.4 [50.4, 62.2] | 50.7 [45.1, 56.2] | 50.7 [45.1, 56.2] | 11.8 [8.7, 16.0] | 49.3 [43.8, 54.9] |
| Attribute similarity, tuned threshold | 19.2 [14.9, 24.3] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 100.0 [93.0, 100.0] |
| Learned + calibrated gate (no verification) | 75.9 [70.5, 80.7] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 100.0 [98.1, 100.0] |
| Learned gate + verification | 75.9 [70.5, 80.7] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 0.0 [0.0, 1.2] | 100.0 [98.1, 100.0] |
| Learned, verified top-k | 99.2 [97.3, 99.8] | 1.0 [0.3, 2.9] | 7.2 [4.8, 10.7] | 1.0 [0.3, 2.9] | 98.9 [96.7, 99.6] |

## Design target vs measurement

| Method | False commits | Rate % | 95% upper bound % |
|---|---|---|---|
| Attribute similarity, tuned threshold | 0/304 | 0.00 | 0.98 |
| Learned + calibrated gate (no verification) | 0/304 | 0.00 | 0.98 |
| Learned gate + verification | 0/304 | 0.00 | 0.98 |
| Learned, verified top-k | 3/304 | 0.99 | 2.53 |

## By category

| Category | Attribute similarity, tuned threshold | Learned + calibrated gate (no verification) | Learned gate + verification | Learned, verified top-k |
|---|---|---|---|---|
| class_churn | 45% | 89% | 89% | 100% |
| dom_wrap | 0% | 100% | 100% | 100% |
| id_churn | 32% | 100% | 100% | 100% |
| label_shift | 0% | 18% | 18% | 95% |
| removed | 0% wrong | 0% wrong | 0% wrong | 8% wrong |
| reorder | 16% | 63% | 63% | 100% |
| restyle | 42% | 61% | 61% | 100% |
| tag_change | 0% | 100% | 100% | 100% |

## Strong vs weak post-condition

| Method | strong: false commits | strong: silent false-pass | weak: false commits | weak: silent false-pass |
|---|---|---|---|---|
| Learned + calibrated gate (no verification) | 0/241 | 0/241 | 0/63 | 0/63 |
| Learned gate + verification | 0/241 | 0/241 | 0/63 | 0/63 |
| Learned, verified top-k | 0/241 | 0/241 | 3/63 | 3/63 |

## Paired comparisons (exact McNemar)

| Comparison | Outcome | only first | only second | p-value |
|---|---|---|---|---|
| Learned + calibrated gate (no verification) vs Learned gate + verification | false commits | 0 | 0 | 1.0000 |
| Learned gate + verification vs Learned, verified top-k | correct heals | 0 | 62 | 0.0000 |
| Attribute similarity, tuned threshold vs Learned + calibrated gate (no verification) | correct heals | 15 | 166 | 0.0000 |
| Attribute similarity, tuned threshold vs Learned + calibrated gate (no verification) | false commits | 0 | 0 | 1.0000 |

## Calibration of confidence

| Confidence bin | Cases | Mean confidence | Observed accuracy |
|---|---|---|---|
| [0.0, 0.2) | 13 | 0.15 | 0.00 |
| [0.2, 0.4) | 16 | 0.32 | 0.31 |
| [0.4, 0.6) | 18 | 0.48 | 0.44 |
| [0.6, 0.8) | 16 | 0.69 | 0.75 |
| [0.8, 1.0) | 241 | 0.98 | 0.99 |

## Ablation study

| Variant | gate heal | gate FCR | verify heal | verify FCR | top-k heal | top-k FCR |
|---|---|---|---|---|---|---|
| full model | 75.9 | 0.0 | 75.9 | 0.0 | 99.2 | 1.0 |
| without visual | 78.9 | 0.0 | 78.9 | 0.0 | 97.7 | 0.7 |
| without intent | 73.3 | 0.7 | 73.3 | 0.0 | 96.6 | 0.0 |
| without geometry | 87.6 | 0.0 | 87.6 | 0.0 | 95.1 | 1.0 |
| without structure | 75.9 | 0.0 | 75.9 | 0.0 | 99.2 | 1.0 |
| without attributes | 74.1 | 0.0 | 74.1 | 0.0 | 98.1 | 1.0 |
| without text | 71.1 | 0.0 | 71.1 | 0.0 | 97.0 | 2.6 |

## Learned weights (standardised features)

| Feature | Weight |
|---|---|
| tag_match | -0.2815 |
| role_match | 0.0908 |
| text_sim | -0.7144 |
| text_exact | 1.0581 |
| attr_sim | -0.2815 |
| class_sim | 0.2376 |
| id_sim | -0.3212 |
| path_sim | 0.3979 |
| pos_sim | 1.472 |
| size_sim | 0.6833 |
| vis_sim | 0.7561 |
| intent_sim | 0.6318 |
| ctx_sim | 0.8038 |
