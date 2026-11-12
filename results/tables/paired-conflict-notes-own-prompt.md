# Conflict notes, paired replay on identical retrieval, BEAM's own prompt

Generated from the per-question records by `python pooled_paired.py pv7p all` (run in `harness/`).

| Split | Questions | Evidence changes | Base | Δ (95% CI) | P(Δ>0) |
|---|---:|---:|---:|---|---:|
| 100k | 400 | 100 | 60.21 | +1.10 (+0.14 to +2.12) | 0.988 |
| 500k | 700 | 141 | 60.47 | +1.18 (+0.53 to +1.83) | 1.000 |
| 1m | 700 | 71 | 61.87 | +0.41 (-0.02 to +0.83) | 0.971 |
| 10m | 200 | 22 | 51.57 | +0.73 (+0.02 to +1.60) | 0.978 |
| **All** | 2000 | | | **+0.85 (+0.50 to +1.20)** | 1.000 |

| Ability | Δ, all splits |
|---|---:|
| abstention | +1.0 |
| contradiction_resolution | +7.0 |
| event_ordering | -0.1 |
| information_extraction | -0.2 |
| instruction_following | -0.2 |
| knowledge_update | +0.3 |
| multi_session_reasoning | +0.2 |
| preference_following | +0.0 |
| summarization | -0.1 |
| temporal_reasoning | +0.5 |
