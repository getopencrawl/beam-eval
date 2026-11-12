# Base system (final2) against the reference evidence as first measured, BEAM's own prompt

Generated from the per-question records by `python final_compare.py --config final2 --paper --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **60.32** | 59.88 (4 runs) | +0.44 (-1.95 to +2.85) | 0.637 | — | 60.1, 60.6 | 0 |
| 500K (700) | **61.03** | 60.50 (4 runs) | +0.53 (-1.40 to +2.51) | 0.695 | — | 61.2, 60.9 | 0 |
| 1M (700) | **61.17** | 58.87 (4 runs) | +2.31 (+0.65 to +3.97) | 0.997 | — | 61.5, 60.9 | 0 |
| 10M (200) | **49.68** | 46.46 (4 runs) | +3.22 (-1.18 to +7.72) | 0.923 | — | 48.3, 51.1 | 0 |
| **All (2000)** | **59.80** | 58.40 | +1.40 (+0.30 to +2.53) | 0.994 | — | | |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 70.0 | 72.8 | — |
| contradiction_resolution | 27.0 | 32.3 | — |
| event_ordering | 54.9 | 52.7 | — |
| information_extraction | 82.6 | 85.5 | — |
| instruction_following | 58.4 | 58.4 | — |
| knowledge_update | 68.8 | 54.2 | — |
| multi_session_reasoning | 53.5 | 54.3 | — |
| preference_following | 84.1 | 81.5 | — |
| summarization | 50.2 | 45.0 | — |
| temporal_reasoning | 53.8 | 62.2 | — |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 62.9 | 66.4 | — |
| contradiction_resolution | 28.7 | 33.2 | — |
| event_ordering | 50.5 | 50.5 | — |
| information_extraction | 75.5 | 78.6 | — |
| instruction_following | 61.3 | 57.5 | — |
| knowledge_update | 74.7 | 69.9 | — |
| multi_session_reasoning | 55.4 | 51.4 | — |
| preference_following | 85.6 | 88.1 | — |
| summarization | 64.3 | 54.6 | — |
| temporal_reasoning | 51.4 | 54.7 | — |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 59.5 | 64.1 | — |
| contradiction_resolution | 33.2 | 33.8 | — |
| event_ordering | 57.7 | 55.0 | — |
| information_extraction | 74.9 | 76.4 | — |
| instruction_following | 68.0 | 59.7 | — |
| knowledge_update | 74.6 | 71.3 | — |
| multi_session_reasoning | 55.7 | 51.7 | — |
| preference_following | 77.3 | 76.9 | — |
| summarization | 60.0 | 50.5 | — |
| temporal_reasoning | 50.8 | 49.2 | — |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 62.5 | 64.4 | — |
| contradiction_resolution | 21.6 | 28.3 | — |
| event_ordering | 46.5 | 41.7 | — |
| information_extraction | 63.7 | 67.2 | — |
| instruction_following | 63.1 | 43.1 | — |
| knowledge_update | 77.5 | 78.8 | — |
| multi_session_reasoning | 15.9 | 14.4 | — |
| preference_following | 64.0 | 59.8 | — |
| summarization | 47.6 | 37.6 | — |
| temporal_reasoning | 34.4 | 29.4 | — |

