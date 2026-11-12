# Conflict notes, paired replay on identical retrieval, annotation-aided prompt

Generated from the per-question records by `python pooled_paired.py pv7x all` (run in `harness/`).

| Split | Questions | Evidence changes | Base | Δ (95% CI) | P(Δ>0) |
|---|---:|---:|---:|---|---:|
| 100k | 400 | 105 | 90.21 | -0.26 (-0.90 to +0.20) | 0.177 |
| 500k | 700 | 140 | 87.63 | -0.16 (-0.44 to +0.11) | 0.127 |
| 1m | 700 | 81 | 89.58 | +0.04 (-0.13 to +0.20) | 0.678 |
| 10m | 200 | 18 | 81.75 | -0.29 (-0.73 to +0.02) | 0.032 |
| **All** | 2000 | | | **-0.12 (-0.30 to +0.03)** | 0.057 |

| Ability | Δ, all splits |
|---|---:|
| abstention | -1.1 |
| contradiction_resolution | +0.4 |
| event_ordering | +0.0 |
| information_extraction | -0.0 |
| instruction_following | -0.0 |
| knowledge_update | -0.2 |
| multi_session_reasoning | -0.5 |
| preference_following | +0.0 |
| summarization | +0.1 |
| temporal_reasoning | +0.2 |
