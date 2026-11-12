# Base system (final2) against the reference evidence as first measured, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final2 --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.01** | 89.66 (3 runs) | +0.35 (-0.75 to +1.51) | 0.723 | 90.82 | 89.6, 90.2, 90.2 | 0 |
| 500K (700) | **87.71** | 87.22 (3 runs) | +0.49 (-0.72 to +1.64) | 0.794 | 88.64 | 88.2, 87.2, 87.7 | 0 |
| 1M (700) | **89.20** | 87.84 (4 runs) | +1.36 (+0.30 to +2.46) | 0.993 | 89.83 | 89.1, 89.0, 89.5 | 0 |
| 10M (200) | **82.20** | 81.25 (5 runs) | +0.95 (-1.31 to +3.25) | 0.801 | 84.48 | 83.4, 81.1, 82.1 | 0 |
| **All (2000)** | **88.14** | 87.33 | +0.81 (+0.16 to +1.45) | 0.991 | 89.08 | | |

| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |
|---|---:|---:|---|---:|
| 100K (400) | 90.01 | 90.82 | -0.81 (-2.01 to +0.43) | 0.101 |
| 500K (700) | 87.71 | 88.64 | -0.93 (-2.17 to +0.25) | 0.062 |
| 1M (700) | 89.20 | 89.83 | -0.64 (-1.81 to +0.56) | 0.141 |
| 10M (200) | 82.20 | 84.48 | -2.27 (-4.97 to +0.30) | 0.043 |
| **All (2000)** | 88.14 | 89.08 | -0.94 (-1.63 to -0.25) | 0.004 |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 93.3 | 97.5 | 95.8 |
| contradiction_resolution | 72.2 | 71.9 | 74.2 |
| event_ordering | 100.0 | 99.9 | 99.7 |
| information_extraction | 89.4 | 92.5 | 94.3 |
| instruction_following | 96.5 | 94.0 | 94.2 |
| knowledge_update | 86.9 | 83.5 | 89.4 |
| multi_session_reasoning | 69.5 | 64.7 | 67.7 |
| preference_following | 99.4 | 100.0 | 99.2 |
| summarization | 98.5 | 98.4 | 99.4 |
| temporal_reasoning | 94.4 | 94.2 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 87.9 | 91.7 | 91.7 |
| contradiction_resolution | 72.9 | 72.3 | 73.8 |
| event_ordering | 100.0 | 99.5 | 100.0 |
| information_extraction | 83.6 | 83.0 | 85.6 |
| instruction_following | 92.7 | 89.9 | 91.3 |
| knowledge_update | 84.5 | 83.5 | 85.6 |
| multi_session_reasoning | 65.3 | 67.4 | 69.5 |
| preference_following | 98.6 | 98.6 | 98.8 |
| summarization | 98.1 | 94.3 | 96.7 |
| temporal_reasoning | 93.5 | 92.1 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 95.2 | 92.5 | 95.7 |
| contradiction_resolution | 70.7 | 69.0 | 72.3 |
| event_ordering | 99.3 | 99.3 | 99.5 |
| information_extraction | 81.1 | 81.3 | 83.1 |
| instruction_following | 96.1 | 95.2 | 95.8 |
| knowledge_update | 86.8 | 83.4 | 85.7 |
| multi_session_reasoning | 71.5 | 66.1 | 71.5 |
| preference_following | 96.4 | 98.2 | 99.0 |
| summarization | 99.1 | 98.4 | 99.1 |
| temporal_reasoning | 95.8 | 94.9 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 96.7 | 93.0 | 100.0 |
| contradiction_resolution | 69.6 | 67.9 | 72.3 |
| event_ordering | 99.4 | 99.5 | 100.0 |
| information_extraction | 63.3 | 65.8 | 68.8 |
| instruction_following | 96.7 | 90.8 | 93.3 |
| knowledge_update | 85.8 | 91.5 | 92.5 |
| multi_session_reasoning | 28.9 | 22.6 | 27.3 |
| preference_following | 93.8 | 98.0 | 100.0 |
| summarization | 95.8 | 92.0 | 98.5 |
| temporal_reasoning | 92.1 | 91.5 | 92.1 |

