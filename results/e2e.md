# End-to-End Live Verification

80 held-out cases sampled evenly.

| Mode | Agreement | Correct heals | Wrong heals | Clean rollbacks | Latency p50 ms | Latency p95 ms |
|---|---|---|---|---|---|---|
| gate | 80/80 | 58 | 0 | 0/0 | 293 | 448 |
| verify | 80/80 | 58 | 0 | 0/0 | 429 | 536 |
| verify_topk | 80/80 | 71 | 0 | 6/6 | 457 | 2135 |
