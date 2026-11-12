# Effect of fact cards in fresh runs, BEAM's own prompt (final3 against final2)

Generated from the per-question records by `python ab_compare.py final2 final3 --prompt paper` (run in `harness/`).

| Split | final2 | final3 | Δ (95% CI) | P(Δ>0) | final2 runs | final3 runs | failed |
|---|---:|---:|---|---:|---|---|---:|
| 100k (400) | 60.32 | 61.82 | +1.50 (-0.49 to +3.53) | 0.931 | 60.1, 60.6 | 61.2, 61.4, 62.8 | 0/0 |
| 500k (700) | 61.03 | 61.02 | -0.01 (-1.34 to +1.32) | 0.494 | 61.2, 60.9 | 60.9, 61.0, 61.1 | 0/0 |
| 1m (700) | 61.17 | 61.77 | +0.59 (-0.59 to +1.76) | 0.835 | 61.5, 60.9 | 61.5, 61.8, 61.9 | 0/0 |
| 10m (200) | 49.68 | 52.20 | +2.52 (+0.13 to +5.01) | 0.981 | 48.3, 51.1 | 52.5, 51.3, 52.8 | 0/0 |
| All (2000) | | | +0.76 (-0.04 to +1.54) | 0.970 | | | |

By ability (final3 minus final2, points):

| Ability | 100k | 500k | 1m | 10m |
|---|---:|---:|---:|---:|
| abstention | -0.8 | -0.5 | +3.2 | +0.8 |
| contradiction_resolution | +2.3 | -0.2 | -2.1 | +3.4 |
| event_ordering | -0.7 | +1.1 | -0.2 | -1.5 |
| information_extraction | +1.6 | +2.4 | +1.0 | +8.3 |
| instruction_following | +2.4 | -2.0 | -0.6 | +4.0 |
| knowledge_update | +5.0 | +1.6 | +5.1 | +3.7 |
| multi_session_reasoning | +0.1 | -1.0 | -0.9 | +0.4 |
| preference_following | +0.3 | -2.1 | +1.4 | -1.2 |
| summarization | +0.6 | -0.9 | -0.9 | +1.5 |
| temporal_reasoning | +4.2 | +1.4 | -0.0 | +5.6 |
