# Effect of conflict notes in fresh runs, BEAM's own prompt (final4 against final3)

Generated from the per-question records by `python ab_compare.py final3 final4 --prompt paper` (run in `harness/`).

| Split | final3 | final4 | Δ (95% CI) | P(Δ>0) | final3 runs | final4 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 61.82 | 62.48 | +0.66 (-0.76 to +2.14) | 0.805 | 61.2, 61.4, 62.8 | 63.3, 61.5, 62.6 | 0/0 |
| 500k (700) | 61.02 | 62.41 | +1.39 (+0.27 to +2.50) | 0.992 | 60.9, 61.0, 61.1 | 62.1, 63.4, 61.7 | 0/0 |
| 1m (700) | 61.77 | 62.14 | +0.37 (-0.64 to +1.39) | 0.767 | 61.5, 61.8, 61.9 | 62.0, 62.0, 62.4 | 0/0 |
| 10m (200) | 52.20 | 52.57 | +0.37 (-1.64 to +2.40) | 0.640 | 52.5, 51.3, 52.8 | 53.0, 51.1, 53.6 | 0/0 |
| All (2000) | | | +0.78 (+0.16 to +1.41) | 0.993 | | | |

By ability (final4 minus final3, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | -2.5 | +3.8 | -1.5 | +0.0 |
| contradiction_resolution | +8.9 | +9.7 | +4.9 | +3.1 |
| event_ordering | +2.0 | -0.8 | -0.7 | +1.3 |
| information_extraction | -2.8 | +1.1 | -1.4 | +0.0 |
| instruction_following | +1.5 | -0.6 | -1.1 | -5.8 |
| knowledge_update | +3.1 | -1.2 | +0.4 | -1.2 |
| multi_session_reasoning | +0.9 | +0.7 | +1.1 | +0.6 |
| preference_following | -1.4 | +0.7 | -0.9 | +7.4 |
| summarization | -0.5 | -0.3 | -0.5 | +1.3 |
| temporal_reasoning | -2.5 | +0.8 | +3.5 | -2.9 |
