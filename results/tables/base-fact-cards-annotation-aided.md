# Base + fact cards (final3) against the reference evidence as first measured, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final3 --first-replays` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.47** | 89.66 (3 runs) | +0.81 (-0.37 to +2.06) | 0.914 | 90.82 | 90.1, 90.9, 90.4 | 0 |
| 500K (700) | **87.78** | 87.22 (3 runs) | +0.56 (-0.59 to +1.69) | 0.827 | 88.64 | 88.0, 87.6, 87.7 | 0 |
| 1M (700) | **88.95** | 87.84 (4 runs) | +1.11 (+0.01 to +2.29) | 0.977 | 89.83 | 89.0, 88.8, 89.0 | 0 |
| 10M (200) | **82.92** | 81.25 (5 runs) | +1.67 (-0.02 to +3.56) | 0.974 | 84.48 | 82.8, 84.0, 81.9 | 0 |
| **All (2000)** | **88.24** | 87.33 | +0.91 (+0.27 to +1.55) | 0.997 | 89.08 | | |

| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |
|---|---:|---:|---|---:|
| 100K (400) | 90.47 | 90.82 | -0.34 (-1.39 to +0.73) | 0.261 |
| 500K (700) | 87.78 | 88.64 | -0.85 (-2.01 to +0.25) | 0.069 |
| 1M (700) | 88.95 | 89.83 | -0.89 (-1.97 to +0.23) | 0.065 |
| 10M (200) | 82.92 | 84.48 | -1.55 (-3.68 to +0.59) | 0.078 |
| **All (2000)** | 88.24 | 89.08 | -0.83 (-1.46 to -0.21) | 0.005 |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 94.2 | 97.5 | 95.8 |
| contradiction_resolution | 72.1 | 71.9 | 74.2 |
| event_ordering | 100.0 | 99.9 | 99.7 |
| information_extraction | 90.5 | 92.5 | 94.3 |
| instruction_following | 96.5 | 94.0 | 94.2 |
| knowledge_update | 89.4 | 83.5 | 89.4 |
| multi_session_reasoning | 69.2 | 64.7 | 67.7 |
| preference_following | 99.8 | 100.0 | 99.2 |
| summarization | 98.1 | 98.4 | 99.4 |
| temporal_reasoning | 95.0 | 94.2 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 90.2 | 91.7 | 91.7 |
| contradiction_resolution | 72.6 | 72.3 | 73.8 |
| event_ordering | 99.6 | 99.5 | 100.0 |
| information_extraction | 81.5 | 83.0 | 85.6 |
| instruction_following | 92.9 | 89.9 | 91.3 |
| knowledge_update | 85.2 | 83.5 | 85.6 |
| multi_session_reasoning | 66.8 | 67.4 | 69.5 |
| preference_following | 98.2 | 98.6 | 98.8 |
| summarization | 98.2 | 94.3 | 96.7 |
| temporal_reasoning | 92.7 | 92.1 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 92.6 | 92.5 | 95.7 |
| contradiction_resolution | 71.2 | 69.0 | 72.3 |
| event_ordering | 99.4 | 99.3 | 99.5 |
| information_extraction | 80.0 | 81.3 | 83.1 |
| instruction_following | 96.2 | 95.2 | 95.8 |
| knowledge_update | 89.4 | 83.4 | 85.7 |
| multi_session_reasoning | 71.4 | 66.1 | 71.5 |
| preference_following | 96.7 | 98.2 | 99.0 |
| summarization | 98.5 | 98.4 | 99.1 |
| temporal_reasoning | 93.8 | 94.9 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 93.3 | 93.0 | 100.0 |
| contradiction_resolution | 70.0 | 67.9 | 72.3 |
| event_ordering | 99.8 | 99.5 | 100.0 |
| information_extraction | 72.5 | 65.8 | 68.8 |
| instruction_following | 92.5 | 90.8 | 93.3 |
| knowledge_update | 89.2 | 91.5 | 92.5 |
| multi_session_reasoning | 27.5 | 22.6 | 27.3 |
| preference_following | 96.2 | 98.0 | 100.0 |
| summarization | 96.1 | 92.0 | 98.5 |
| temporal_reasoning | 92.1 | 91.5 | 92.1 |

