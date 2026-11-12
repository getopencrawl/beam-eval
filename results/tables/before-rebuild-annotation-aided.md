# The system before the rebuild (final4) against the reference evidence as first measured, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final4 --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.27** | 89.66 (3 runs) | +0.61 (-0.67 to +1.92) | 0.822 | 90.82 | 90.3, 90.3, 90.2 | 0 |
| 500K (700) | **87.76** | 87.22 (3 runs) | +0.54 (-0.57 to +1.63) | 0.829 | 88.64 | 88.0, 87.3, 88.0 | 0 |
| 1M (700) | **89.57** | 87.84 (4 runs) | +1.73 (+0.69 to +2.87) | 0.999 | 89.83 | 89.9, 89.7, 89.2 | 0 |
| 10M (200) | **83.69** | 81.25 (5 runs) | +2.44 (+0.62 to +4.52) | 0.996 | 84.48 | 83.9, 82.5, 84.6 | 0 |
| **All (2000)** | **88.49** | 87.33 | +1.16 (+0.52 to +1.80) | 1.000 | 89.08 | | |

| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |
|---|---:|---:|---|---:|
| 100K (400) | 90.27 | 90.82 | -0.55 (-1.89 to +0.78) | 0.210 |
| 500K (700) | 87.76 | 88.64 | -0.88 (-1.97 to +0.18) | 0.053 |
| 1M (700) | 89.57 | 89.83 | -0.26 (-1.32 to +0.83) | 0.309 |
| 10M (200) | 83.69 | 84.48 | -0.79 (-2.97 to +1.47) | 0.242 |
| **All (2000)** | 88.49 | 89.08 | -0.59 (-1.21 to +0.05) | 0.033 |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 92.9 | 97.5 | 95.8 |
| contradiction_resolution | 72.4 | 71.9 | 74.2 |
| event_ordering | 100.0 | 99.9 | 99.7 |
| information_extraction | 90.5 | 92.5 | 94.3 |
| instruction_following | 97.3 | 94.0 | 94.2 |
| knowledge_update | 89.2 | 83.5 | 89.4 |
| multi_session_reasoning | 66.3 | 64.7 | 67.7 |
| preference_following | 100.0 | 100.0 | 99.2 |
| summarization | 98.1 | 98.4 | 99.4 |
| temporal_reasoning | 96.0 | 94.2 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 90.2 | 91.7 | 91.7 |
| contradiction_resolution | 73.4 | 72.3 | 73.8 |
| event_ordering | 99.9 | 99.5 | 100.0 |
| information_extraction | 82.0 | 83.0 | 85.6 |
| instruction_following | 89.7 | 89.9 | 91.3 |
| knowledge_update | 84.8 | 83.5 | 85.6 |
| multi_session_reasoning | 67.3 | 67.4 | 69.5 |
| preference_following | 98.6 | 98.6 | 98.8 |
| summarization | 98.3 | 94.3 | 96.7 |
| temporal_reasoning | 93.5 | 92.1 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 94.6 | 92.5 | 95.7 |
| contradiction_resolution | 72.1 | 69.0 | 72.3 |
| event_ordering | 99.5 | 99.3 | 99.5 |
| information_extraction | 81.6 | 81.3 | 83.1 |
| instruction_following | 96.0 | 95.2 | 95.8 |
| knowledge_update | 89.5 | 83.4 | 85.7 |
| multi_session_reasoning | 71.8 | 66.1 | 71.5 |
| preference_following | 97.1 | 98.2 | 99.0 |
| summarization | 99.0 | 98.4 | 99.1 |
| temporal_reasoning | 94.5 | 94.9 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 96.7 | 93.0 | 100.0 |
| contradiction_resolution | 70.2 | 67.9 | 72.3 |
| event_ordering | 99.9 | 99.5 | 100.0 |
| information_extraction | 70.4 | 65.8 | 68.8 |
| instruction_following | 96.7 | 90.8 | 93.3 |
| knowledge_update | 89.2 | 91.5 | 92.5 |
| multi_session_reasoning | 29.0 | 22.6 | 27.3 |
| preference_following | 96.7 | 98.0 | 100.0 |
| summarization | 96.9 | 92.0 | 98.5 |
| temporal_reasoning | 91.2 | 91.5 | 92.1 |

