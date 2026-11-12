# The rebuilt system against the system before the rebuild, annotation-aided prompt (final5 against final4)

Generated from the per-question records by `python ab_compare.py final4 final5` (run in `harness/`).

| Split | final4 | final5 | Δ (95% CI) | P(Δ>0) | final4 runs | final5 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 90.27 | 90.17 | -0.10 (-0.93 to +0.75) | 0.404 | 90.3, 90.3, 90.2 | 89.7, 90.8, 90.0 | 0/0 |
| 500k (700) | 87.76 | 87.89 | +0.13 (-0.54 to +0.78) | 0.654 | 88.0, 87.3, 88.0 | 88.0, 87.5, 88.2 | 0/0 |
| 1m (700) | 89.57 | 89.46 | -0.11 (-0.73 to +0.53) | 0.356 | 89.9, 89.7, 89.2 | 89.0, 89.4, 89.9 | 0/0 |
| 10m (200) | 83.69 | 81.44 | -2.25 (-3.62 to -1.06) | 0.000 | 83.9, 82.5, 84.6 | 80.8, 81.9, 81.6 | 0/0 |
| All (2000) | | | -0.24 (-0.62 to +0.14) | 0.109 | | | |

By ability (final5 minus final4, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | -1.3 | -0.5 | -1.1 | -5.8 |
| contradiction_resolution | -0.5 | +0.4 | -0.2 | -1.7 |
| event_ordering | -0.1 | +0.1 | +0.1 | -0.1 |
| information_extraction | +0.2 | +0.7 | -0.3 | -2.9 |
| instruction_following | -0.4 | +2.0 | -0.2 | -2.5 |
| knowledge_update | -0.2 | +0.8 | +0.6 | +0.0 |
| multi_session_reasoning | +2.3 | -1.1 | +0.2 | -4.8 |
| preference_following | -1.2 | -0.2 | -0.1 | -2.5 |
| summarization | +0.2 | -0.3 | +0.0 | -2.6 |
| temporal_reasoning | +0.0 | -0.6 | -0.2 | +0.4 |
