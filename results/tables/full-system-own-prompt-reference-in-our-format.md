# Reported system against the reference evidence in OpenCrawl's item format and time order, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final5 --paper --ref ourfmt-time` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **63.05** | 60.02 (2 runs) | +3.03 (+0.64 to +5.41) | 0.993 | — | 62.3, 63.3, 63.5 | 0 |
| 500K (700) | **61.59** | 60.25 (2 runs) | +1.35 (-0.41 to +3.08) | 0.933 | — | 61.0, 62.0, 61.7 | 0 |
| 1M (700) | **62.33** | 58.43 (2 runs) | +3.91 (+2.27 to +5.57) | 1.000 | — | 62.0, 62.4, 62.6 | 0 |
| 10M (200) | **51.88** | 46.05 (2 runs) | +5.82 (+1.67 to +10.01) | 0.998 | — | 53.8, 51.2, 50.6 | 0 |
| **All (2000)** | **61.17** | 58.14 | +3.03 (+2.00 to +4.08) | 1.000 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 66.7 | 73.1 | — |
| contradiction_resolution | 41.4 | 33.9 | — |
| event_ordering | 57.1 | 52.9 | — |
| information_extraction | 78.9 | 80.8 | — |
| instruction_following | 60.4 | 58.1 | — |
| knowledge_update | 76.0 | 65.6 | — |
| multi_session_reasoning | 55.8 | 51.5 | — |
| preference_following | 82.7 | 83.0 | — |
| summarization | 50.9 | 41.8 | — |
| temporal_reasoning | 60.6 | 59.4 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 63.3 | 71.1 | — |
| contradiction_resolution | 37.0 | 30.4 | — |
| event_ordering | 52.3 | 48.6 | — |
| information_extraction | 78.3 | 79.9 | — |
| instruction_following | 57.7 | 56.0 | — |
| knowledge_update | 74.2 | 75.1 | — |
| multi_session_reasoning | 53.0 | 51.6 | — |
| preference_following | 83.7 | 86.4 | — |
| summarization | 64.0 | 53.9 | — |
| temporal_reasoning | 52.4 | 49.5 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 64.3 | 61.3 | — |
| contradiction_resolution | 38.1 | 32.1 | — |
| event_ordering | 59.2 | 52.0 | — |
| information_extraction | 72.5 | 73.0 | — |
| instruction_following | 66.5 | 59.7 | — |
| knowledge_update | 79.5 | 75.2 | — |
| multi_session_reasoning | 53.8 | 52.3 | — |
| preference_following | 78.5 | 81.3 | — |
| summarization | 58.2 | 48.7 | — |
| temporal_reasoning | 52.7 | 48.7 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 61.7 | 66.2 | — |
| contradiction_resolution | 25.6 | 28.7 | — |
| event_ordering | 48.2 | 41.5 | — |
| information_extraction | 66.2 | 65.0 | — |
| instruction_following | 64.2 | 40.0 | — |
| knowledge_update | 80.8 | 78.8 | — |
| multi_session_reasoning | 18.6 | 11.3 | — |
| preference_following | 68.9 | 63.7 | — |
| summarization | 47.0 | 37.8 | — |
| temporal_reasoning | 37.5 | 27.5 | — |

