# Effect of fact cards in fresh runs, annotation-aided prompt (final3 against final2)

Generated from the per-question records by `python ab_compare.py final2 final3` (run in `harness/`).

| Split | final2 | final3 | Δ (95% CI) | P(Δ>0) | final2 runs | final3 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 90.01 | 90.47 | +0.47 (-0.30 to +1.25) | 0.883 | 89.6, 90.2, 90.2 | 90.1, 90.9, 90.4 | 0/0 |
| 500k (700) | 87.71 | 87.78 | +0.08 (-0.72 to +0.86) | 0.580 | 88.2, 87.2, 87.7 | 88.0, 87.6, 87.7 | 0/0 |
| 1m (700) | 89.20 | 88.95 | -0.25 (-0.97 to +0.48) | 0.250 | 89.1, 89.0, 89.5 | 89.0, 88.8, 89.0 | 0/0 |
| 10m (200) | 82.20 | 82.92 | +0.72 (-1.08 to +2.77) | 0.770 | 83.4, 81.1, 82.1 | 82.8, 84.0, 81.9 | 0/0 |
| All (2000) | | | +0.10 (-0.34 to +0.56) | 0.674 | | | |

By ability (final3 minus final2, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | +0.8 | +2.4 | -2.6 | -3.3 |
| contradiction_resolution | -0.1 | -0.3 | +0.5 | +0.4 |
| event_ordering | +0.0 | -0.4 | +0.1 | +0.4 |
| information_extraction | +1.1 | -2.1 | -1.0 | +9.2 |
| instruction_following | +0.0 | +0.2 | +0.2 | -4.2 |
| knowledge_update | +2.5 | +0.7 | +2.6 | +3.3 |
| multi_session_reasoning | -0.3 | +1.4 | -0.0 | -1.4 |
| preference_following | +0.4 | -0.5 | +0.3 | +2.5 |
| summarization | -0.4 | +0.0 | -0.5 | +0.3 |
| temporal_reasoning | +0.6 | -0.8 | -2.0 | +0.0 |
