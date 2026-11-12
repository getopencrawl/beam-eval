# Reported system against the reference evidence put in time order, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final5 --paper --ref time` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **63.05** | 60.01 (2 runs) | +3.04 (+0.55 to +5.54) | 0.991 | — | 62.3, 63.3, 63.5 | 0 |
| 500K (700) | **61.59** | 60.73 (2 runs) | +0.86 (-0.96 to +2.66) | 0.827 | — | 61.0, 62.0, 61.7 | 0 |
| 1M (700) | **62.33** | 59.79 (2 runs) | +2.54 (+0.88 to +4.19) | 0.998 | — | 62.0, 62.4, 62.6 | 0 |
| 10M (200) | **51.88** | 46.15 (2 runs) | +5.72 (+1.24 to +10.30) | 0.995 | — | 53.8, 51.2, 50.6 | 0 |
| **All (2000)** | **61.17** | 58.80 | +2.37 (+1.27 to +3.47) | 1.000 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 66.7 | 70.6 | — |
| contradiction_resolution | 41.4 | 35.3 | — |
| event_ordering | 57.1 | 53.6 | — |
| information_extraction | 78.9 | 79.6 | — |
| instruction_following | 60.4 | 55.6 | — |
| knowledge_update | 76.0 | 64.1 | — |
| multi_session_reasoning | 55.8 | 55.4 | — |
| preference_following | 82.7 | 82.7 | — |
| summarization | 50.9 | 45.3 | — |
| temporal_reasoning | 60.6 | 57.8 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 63.3 | 61.4 | — |
| contradiction_resolution | 37.0 | 30.4 | — |
| event_ordering | 52.3 | 50.2 | — |
| information_extraction | 78.3 | 78.1 | — |
| instruction_following | 57.7 | 59.7 | — |
| knowledge_update | 74.2 | 77.0 | — |
| multi_session_reasoning | 53.0 | 51.7 | — |
| preference_following | 83.7 | 87.1 | — |
| summarization | 64.0 | 55.5 | — |
| temporal_reasoning | 52.4 | 56.1 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 64.3 | 66.4 | — |
| contradiction_resolution | 38.1 | 31.1 | — |
| event_ordering | 59.2 | 53.9 | — |
| information_extraction | 72.5 | 74.4 | — |
| instruction_following | 66.5 | 61.7 | — |
| knowledge_update | 79.5 | 78.2 | — |
| multi_session_reasoning | 53.8 | 52.4 | — |
| preference_following | 78.5 | 77.8 | — |
| summarization | 58.2 | 50.6 | — |
| temporal_reasoning | 52.7 | 51.4 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 61.7 | 57.5 | — |
| contradiction_resolution | 25.6 | 28.4 | — |
| event_ordering | 48.2 | 42.4 | — |
| information_extraction | 66.2 | 73.1 | — |
| instruction_following | 64.2 | 41.2 | — |
| knowledge_update | 80.8 | 85.0 | — |
| multi_session_reasoning | 18.6 | 13.5 | — |
| preference_following | 68.9 | 59.8 | — |
| summarization | 47.0 | 36.8 | — |
| temporal_reasoning | 37.5 | 23.8 | — |

