# Base + fact cards (final3) against the reference evidence as first measured, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final3 --paper --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **61.82** | 59.88 (4 runs) | +1.94 (-0.43 to +4.36) | 0.945 | — | 61.2, 61.4, 62.8 | 0 |
| 500K (700) | **61.02** | 60.50 (4 runs) | +0.52 (-1.31 to +2.38) | 0.708 | — | 60.9, 61.0, 61.1 | 0 |
| 1M (700) | **61.77** | 58.87 (4 runs) | +2.90 (+1.18 to +4.63) | 0.999 | — | 61.5, 61.8, 61.9 | 0 |
| 10M (200) | **52.20** | 46.46 (4 runs) | +5.74 (+1.63 to +9.92) | 0.997 | — | 52.5, 51.3, 52.8 | 0 |
| **All (2000)** | **60.56** | 58.40 | +2.16 (+1.08 to +3.27) | 1.000 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 69.2 | 72.8 | — |
| contradiction_resolution | 29.4 | 32.3 | — |
| event_ordering | 54.2 | 52.7 | — |
| information_extraction | 84.2 | 85.5 | — |
| instruction_following | 60.8 | 58.4 | — |
| knowledge_update | 73.8 | 54.2 | — |
| multi_session_reasoning | 53.6 | 54.3 | — |
| preference_following | 84.4 | 81.5 | — |
| summarization | 50.8 | 45.0 | — |
| temporal_reasoning | 57.9 | 62.2 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 62.4 | 66.4 | — |
| contradiction_resolution | 28.5 | 33.2 | — |
| event_ordering | 51.7 | 50.5 | — |
| information_extraction | 78.0 | 78.6 | — |
| instruction_following | 59.3 | 57.5 | — |
| knowledge_update | 76.3 | 69.9 | — |
| multi_session_reasoning | 54.4 | 51.4 | — |
| preference_following | 83.5 | 88.1 | — |
| summarization | 63.4 | 54.6 | — |
| temporal_reasoning | 52.8 | 54.7 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 62.6 | 64.1 | — |
| contradiction_resolution | 31.1 | 33.8 | — |
| event_ordering | 57.5 | 55.0 | — |
| information_extraction | 75.9 | 76.4 | — |
| instruction_following | 67.4 | 59.7 | — |
| knowledge_update | 79.8 | 71.3 | — |
| multi_session_reasoning | 54.8 | 51.7 | — |
| preference_following | 78.7 | 76.9 | — |
| summarization | 59.1 | 50.5 | — |
| temporal_reasoning | 50.8 | 49.2 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 63.3 | 64.4 | — |
| contradiction_resolution | 25.0 | 28.3 | — |
| event_ordering | 45.0 | 41.7 | — |
| information_extraction | 72.1 | 67.2 | — |
| instruction_following | 67.1 | 43.1 | — |
| knowledge_update | 81.2 | 78.8 | — |
| multi_session_reasoning | 16.4 | 14.4 | — |
| preference_following | 62.8 | 59.8 | — |
| summarization | 49.1 | 37.6 | — |
| temporal_reasoning | 40.0 | 29.4 | — |

