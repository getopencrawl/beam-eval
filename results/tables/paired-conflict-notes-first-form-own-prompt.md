# Conflict notes in their first form, paired replay, BEAM's own prompt

Generated from the per-question records by `python pooled_paired.py pv6p all` (run in `harness/`).

| Split | Questions | Evidence changes | Base | Δ (95% CI) | P(Δ>0) |
|---|---:|---:|---:|---|---:|
| 100k | 400 | 148 | 61.78 | +0.74 (-0.19 to +1.70) | 0.938 |
| 500k | 700 | 215 | 59.14 | +1.58 (+0.81 to +2.39) | 1.000 |
| 1m | 452 | 76 | 61.45 | -0.39 (-1.27 to +0.35) | 0.170 |
| 10m | 200 | 32 | 50.47 | +0.26 (-0.65 to +1.35) | 0.678 |
| **All** | 1752 | | | **+0.73 (+0.28 to +1.18)** | 0.999 |

| Ability | Δ, all splits |
|---|---:|
| abstention | -0.8 |
| contradiction_resolution | +6.6 |
| event_ordering | -0.1 |
| information_extraction | +0.5 |
| instruction_following | -1.2 |
| knowledge_update | -0.4 |
| multi_session_reasoning | +1.0 |
| preference_following | +0.1 |
| summarization | +0.2 |
| temporal_reasoning | +1.4 |
