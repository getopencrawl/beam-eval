# The rebuilt system against the system before the rebuild, BEAM's own prompt (final5 against final4)

Generated from the per-question records by `python ab_compare.py final4 final5 --prompt paper` (run in `harness/`).

| Split | final4 | final5 | Δ (95% CI) | P(Δ>0) | final4 runs | final5 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 62.48 | 63.05 | +0.57 (-0.89 to +2.01) | 0.775 | 63.3, 61.5, 62.6 | 62.3, 63.3, 63.5 | 0/0 |
| 500k (700) | 62.41 | 61.59 | -0.82 (-1.84 to +0.23) | 0.064 | 62.1, 63.4, 61.7 | 61.0, 62.0, 61.7 | 0/0 |
| 1m (700) | 62.14 | 62.33 | +0.20 (-0.92 to +1.27) | 0.636 | 62.0, 62.0, 62.4 | 62.0, 62.4, 62.6 | 0/0 |
| 10m (200) | 52.57 | 51.88 | -0.69 (-2.81 to +1.33) | 0.252 | 53.0, 51.1, 53.6 | 53.8, 51.2, 50.6 | 0/0 |
| All (2000) | | | -0.17 (-0.80 to +0.48) | 0.299 | | | |

By ability (final5 minus final4, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | +0.0 | -2.9 | +3.2 | -1.7 |
| contradiction_resolution | +3.1 | -1.2 | +2.0 | -2.5 |
| event_ordering | +0.9 | +1.4 | +2.3 | +2.0 |
| information_extraction | -2.5 | -0.8 | -1.9 | -5.8 |
| instruction_following | -1.9 | -1.0 | +0.2 | +2.9 |
| knowledge_update | -0.8 | -0.9 | -0.6 | +0.8 |
| multi_session_reasoning | +1.3 | -2.2 | -2.1 | +1.7 |
| preference_following | -0.3 | -0.4 | +0.7 | -1.2 |
| summarization | +0.7 | +0.9 | -0.3 | -3.5 |
| temporal_reasoning | +5.2 | -1.2 | -1.5 | +0.4 |
