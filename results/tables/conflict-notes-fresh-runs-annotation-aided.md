# Effect of conflict notes in fresh runs, annotation-aided prompt (final4 against final3)

Generated from the per-question records by `python ab_compare.py final3 final4` (run in `harness/`).

| Split | final3 | final4 | Δ (95% CI) | P(Δ>0) | final3 runs | final4 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 90.47 | 90.27 | -0.20 (-1.12 to +0.64) | 0.331 | 90.1, 90.9, 90.4 | 90.3, 90.3, 90.2 | 0/0 |
| 500k (700) | 87.78 | 87.76 | -0.02 (-0.66 to +0.60) | 0.471 | 88.0, 87.6, 87.7 | 88.0, 87.3, 88.0 | 0/0 |
| 1m (700) | 88.95 | 89.57 | +0.62 (+0.08 to +1.19) | 0.986 | 89.0, 88.8, 89.0 | 89.9, 89.7, 89.2 | 0/0 |
| 10m (200) | 82.92 | 83.69 | +0.77 (-0.35 to +2.01) | 0.905 | 82.8, 84.0, 81.9 | 83.9, 82.5, 84.6 | 0/0 |
| All (2000) | | | +0.25 (-0.11 to +0.61) | 0.910 | | | |

By ability (final4 minus final3, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | -1.2 | +0.0 | +2.0 | +3.3 |
| contradiction_resolution | +0.3 | +0.8 | +0.8 | +0.2 |
| event_ordering | +0.0 | +0.3 | +0.1 | +0.1 |
| information_extraction | -0.1 | +0.5 | +1.5 | -2.1 |
| instruction_following | +0.8 | -3.2 | -0.2 | +4.2 |
| knowledge_update | -0.2 | -0.5 | +0.1 | +0.0 |
| multi_session_reasoning | -2.9 | +0.5 | +0.4 | +1.5 |
| preference_following | +0.2 | +0.4 | +0.4 | +0.4 |
| summarization | -0.0 | +0.1 | +0.4 | +0.8 |
| temporal_reasoning | +1.0 | +0.8 | +0.7 | -0.8 |
