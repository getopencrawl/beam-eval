# Reported system against the reference evidence in OpenCrawl's item format and time order, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final5 --ref ourfmt-time` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.17** | 88.86 (3 runs) | +1.31 (-0.19 to +2.85) | 0.959 | 90.82 | 89.7, 90.8, 90.0 | 0 |
| 500K (700) | **87.89** | 86.61 (3 runs) | +1.28 (+0.30 to +2.29) | 0.994 | 88.64 | 88.0, 87.5, 88.2 | 0 |
| 1M (700) | **89.46** | 87.58 (3 runs) | +1.88 (+0.93 to +2.84) | 1.000 | 89.83 | 89.0, 89.4, 89.9 | 0 |
| 10M (200) | **81.44** | 82.64 (3 runs) | -1.19 (-3.51 to +1.21) | 0.158 | 84.48 | 80.8, 81.9, 81.6 | 0 |
| **All (2000)** | **88.25** | 87.00 | +1.25 (+0.64 to +1.86) | 1.000 | 89.08 | | |

| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |
|---|---:|---:|---|---:|
| 100K (400) | 90.17 | 90.82 | -0.65 (-1.89 to +0.55) | 0.152 |
| 500K (700) | 87.89 | 88.64 | -0.75 (-1.90 to +0.37) | 0.093 |
| 1M (700) | 89.46 | 89.83 | -0.38 (-1.43 to +0.73) | 0.237 |
| 10M (200) | 81.44 | 84.48 | -3.04 (-5.36 to -0.83) | 0.004 |
| **All (2000)** | 88.25 | 89.08 | -0.83 (-1.46 to -0.21) | 0.005 |

**100K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 91.7 | 93.3 | 95.8 |
| contradiction_resolution | 71.9 | 71.9 | 74.2 |
| event_ordering | 99.9 | 99.7 | 99.7 |
| information_extraction | 90.7 | 89.6 | 94.3 |
| instruction_following | 96.9 | 91.9 | 94.2 |
| knowledge_update | 89.0 | 85.2 | 89.4 |
| multi_session_reasoning | 68.6 | 63.8 | 67.7 |
| preference_following | 98.8 | 99.6 | 99.2 |
| summarization | 98.3 | 98.9 | 99.4 |
| temporal_reasoning | 96.0 | 94.8 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 89.8 | 90.7 | 91.7 |
| contradiction_resolution | 73.8 | 71.9 | 73.8 |
| event_ordering | 100.0 | 99.8 | 100.0 |
| information_extraction | 82.7 | 78.6 | 85.6 |
| instruction_following | 91.7 | 89.5 | 91.3 |
| knowledge_update | 85.6 | 83.1 | 85.6 |
| multi_session_reasoning | 66.1 | 66.5 | 69.5 |
| preference_following | 98.4 | 98.6 | 98.8 |
| summarization | 98.0 | 94.1 | 96.7 |
| temporal_reasoning | 92.9 | 93.4 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 93.6 | 92.9 | 95.7 |
| contradiction_resolution | 71.9 | 69.0 | 72.3 |
| event_ordering | 99.6 | 99.7 | 99.5 |
| information_extraction | 81.3 | 80.3 | 83.1 |
| instruction_following | 95.8 | 91.3 | 95.8 |
| knowledge_update | 90.1 | 86.2 | 85.7 |
| multi_session_reasoning | 72.0 | 68.4 | 71.5 |
| preference_following | 97.0 | 97.5 | 99.0 |
| summarization | 99.0 | 96.8 | 99.1 |
| temporal_reasoning | 94.3 | 93.7 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 90.8 | 95.8 | 100.0 |
| contradiction_resolution | 68.5 | 68.1 | 72.3 |
| event_ordering | 99.8 | 98.5 | 100.0 |
| information_extraction | 67.5 | 67.9 | 68.8 |
| instruction_following | 94.2 | 90.4 | 93.3 |
| knowledge_update | 89.2 | 92.5 | 92.5 |
| multi_session_reasoning | 24.2 | 26.7 | 27.3 |
| preference_following | 94.2 | 98.3 | 100.0 |
| summarization | 94.4 | 95.6 | 98.5 |
| temporal_reasoning | 91.7 | 92.5 | 92.1 |

