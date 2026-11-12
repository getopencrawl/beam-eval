# Reported system (final5) against the reference evidence, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final5 --paper` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **63.05** | 60.05 (6 runs) | +3.00 (+0.62 to +5.40) | 0.993 | — | 62.3, 63.3, 63.5 | 0 |
| 500K (700) | **61.59** | 60.44 (6 runs) | +1.15 (-0.59 to +2.90) | 0.901 | — | 61.0, 62.0, 61.7 | 0 |
| 1M (700) | **62.33** | 58.98 (6 runs) | +3.36 (+1.68 to +5.05) | 1.000 | — | 62.0, 62.4, 62.6 | 0 |
| 10M (200) | **51.88** | 47.02 (6 runs) | +4.86 (+0.68 to +9.10) | 0.988 | — | 53.8, 51.2, 50.6 | 0 |
| **All (2000)** | **61.17** | 58.51 | +2.66 (+1.62 to +3.72) | 1.000 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 66.7 | 71.9 | — |
| contradiction_resolution | 41.4 | 31.8 | — |
| event_ordering | 57.1 | 53.8 | — |
| information_extraction | 78.9 | 86.6 | — |
| instruction_following | 60.4 | 58.4 | — |
| knowledge_update | 76.0 | 54.3 | — |
| multi_session_reasoning | 55.8 | 54.1 | — |
| preference_following | 82.7 | 82.3 | — |
| summarization | 50.9 | 45.2 | — |
| temporal_reasoning | 60.6 | 62.2 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 63.3 | 67.1 | — |
| contradiction_resolution | 37.0 | 33.0 | — |
| event_ordering | 52.3 | 51.2 | — |
| information_extraction | 78.3 | 78.8 | — |
| instruction_following | 57.7 | 57.3 | — |
| knowledge_update | 74.2 | 70.3 | — |
| multi_session_reasoning | 53.0 | 51.1 | — |
| preference_following | 83.7 | 87.1 | — |
| summarization | 64.0 | 54.3 | — |
| temporal_reasoning | 52.4 | 54.2 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 64.3 | 63.9 | — |
| contradiction_resolution | 38.1 | 33.8 | — |
| event_ordering | 59.2 | 55.4 | — |
| information_extraction | 72.5 | 76.5 | — |
| instruction_following | 66.5 | 60.2 | — |
| knowledge_update | 79.5 | 71.1 | — |
| multi_session_reasoning | 53.8 | 51.7 | — |
| preference_following | 78.5 | 77.3 | — |
| summarization | 58.2 | 50.2 | — |
| temporal_reasoning | 52.7 | 49.5 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 61.7 | 65.4 | — |
| contradiction_resolution | 25.6 | 29.1 | — |
| event_ordering | 48.2 | 42.8 | — |
| information_extraction | 66.2 | 69.2 | — |
| instruction_following | 64.2 | 43.3 | — |
| knowledge_update | 80.8 | 79.2 | — |
| multi_session_reasoning | 18.6 | 15.8 | — |
| preference_following | 68.9 | 58.8 | — |
| summarization | 47.0 | 37.6 | — |
| temporal_reasoning | 37.5 | 29.2 | — |

