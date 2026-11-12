# The system before the rebuild (final4) against the reference evidence as first measured, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final4 --paper --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **62.48** | 59.88 (4 runs) | +2.60 (+0.15 to +5.07) | 0.981 | — | 63.3, 61.5, 62.6 | 0 |
| 500K (700) | **62.41** | 60.50 (4 runs) | +1.91 (+0.12 to +3.73) | 0.982 | — | 62.1, 63.4, 61.7 | 0 |
| 1M (700) | **62.14** | 58.87 (4 runs) | +3.27 (+1.58 to +5.00) | 1.000 | — | 62.0, 62.0, 62.4 | 0 |
| 10M (200) | **52.57** | 46.46 (4 runs) | +6.11 (+1.92 to +10.33) | 0.999 | — | 53.0, 51.1, 53.6 | 0 |
| **All (2000)** | **61.34** | 58.40 | +2.94 (+1.87 to +4.03) | 1.000 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 66.7 | 72.8 | — |
| contradiction_resolution | 38.2 | 32.3 | — |
| event_ordering | 56.2 | 52.7 | — |
| information_extraction | 81.4 | 85.5 | — |
| instruction_following | 62.3 | 58.4 | — |
| knowledge_update | 76.9 | 54.2 | — |
| multi_session_reasoning | 54.5 | 54.3 | — |
| preference_following | 83.0 | 81.5 | — |
| summarization | 50.3 | 45.0 | — |
| temporal_reasoning | 55.4 | 62.2 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 66.2 | 66.4 | — |
| contradiction_resolution | 38.2 | 33.2 | — |
| event_ordering | 50.9 | 50.5 | — |
| information_extraction | 79.1 | 78.6 | — |
| instruction_following | 58.7 | 57.5 | — |
| knowledge_update | 75.1 | 69.9 | — |
| multi_session_reasoning | 55.2 | 51.4 | — |
| preference_following | 84.2 | 88.1 | — |
| summarization | 63.1 | 54.6 | — |
| temporal_reasoning | 53.6 | 54.7 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 61.1 | 64.1 | — |
| contradiction_resolution | 36.1 | 33.8 | — |
| event_ordering | 56.9 | 55.0 | — |
| information_extraction | 74.5 | 76.4 | — |
| instruction_following | 66.3 | 59.7 | — |
| knowledge_update | 80.1 | 71.3 | — |
| multi_session_reasoning | 55.9 | 51.7 | — |
| preference_following | 77.8 | 76.9 | — |
| summarization | 58.5 | 50.5 | — |
| temporal_reasoning | 54.3 | 49.2 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 63.3 | 64.4 | — |
| contradiction_resolution | 28.1 | 28.3 | — |
| event_ordering | 46.2 | 41.7 | — |
| information_extraction | 72.1 | 67.2 | — |
| instruction_following | 61.3 | 43.1 | — |
| knowledge_update | 80.0 | 78.8 | — |
| multi_session_reasoning | 17.0 | 14.4 | — |
| preference_following | 70.1 | 59.8 | — |
| summarization | 50.4 | 37.6 | — |
| temporal_reasoning | 37.1 | 29.4 | — |

