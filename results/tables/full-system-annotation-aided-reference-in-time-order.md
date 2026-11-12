# Reported system against the reference evidence put in time order, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final5 --ref time` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.17** | 89.93 (3 runs) | +0.24 (-0.94 to +1.40) | 0.666 | 90.82 | 89.7, 90.8, 90.0 | 0 |
| 500K (700) | **87.89** | 87.73 (3 runs) | +0.16 (-0.78 to +1.09) | 0.634 | 88.64 | 88.0, 87.5, 88.2 | 0 |
| 1M (700) | **89.46** | 87.79 (3 runs) | +1.67 (+0.69 to +2.67) | 1.000 | 89.83 | 89.0, 89.4, 89.9 | 0 |
| 10M (200) | **81.44** | 81.51 (3 runs) | -0.07 (-2.26 to +2.17) | 0.474 | 84.48 | 80.8, 81.9, 81.6 | 0 |
| **All (2000)** | **88.25** | 87.57 | +0.68 (+0.11 to +1.26) | 0.990 | 89.08 | | |

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
| abstention | 91.7 | 96.2 | 95.8 |
| contradiction_resolution | 71.9 | 71.2 | 74.2 |
| event_ordering | 99.9 | 99.9 | 99.7 |
| information_extraction | 90.7 | 92.7 | 94.3 |
| instruction_following | 96.9 | 92.7 | 94.2 |
| knowledge_update | 89.0 | 88.3 | 89.4 |
| multi_session_reasoning | 68.6 | 65.3 | 67.7 |
| preference_following | 98.8 | 98.5 | 99.2 |
| summarization | 98.3 | 98.8 | 99.4 |
| temporal_reasoning | 96.0 | 95.4 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 89.8 | 94.3 | 91.7 |
| contradiction_resolution | 73.8 | 72.8 | 73.8 |
| event_ordering | 100.0 | 99.8 | 100.0 |
| information_extraction | 82.7 | 81.7 | 85.6 |
| instruction_following | 91.7 | 87.6 | 91.3 |
| knowledge_update | 85.6 | 85.8 | 85.6 |
| multi_session_reasoning | 66.1 | 68.7 | 69.5 |
| preference_following | 98.4 | 98.8 | 98.8 |
| summarization | 98.0 | 95.5 | 96.7 |
| temporal_reasoning | 92.9 | 92.3 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 93.6 | 91.7 | 95.7 |
| contradiction_resolution | 71.9 | 70.1 | 72.3 |
| event_ordering | 99.6 | 99.4 | 99.5 |
| information_extraction | 81.3 | 80.2 | 83.1 |
| instruction_following | 95.8 | 95.3 | 95.8 |
| knowledge_update | 90.1 | 84.0 | 85.7 |
| multi_session_reasoning | 72.0 | 69.3 | 71.5 |
| preference_following | 97.0 | 96.4 | 99.0 |
| summarization | 99.0 | 97.1 | 99.1 |
| temporal_reasoning | 94.3 | 94.3 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 90.8 | 96.7 | 100.0 |
| contradiction_resolution | 68.5 | 68.3 | 72.3 |
| event_ordering | 99.8 | 100.0 | 100.0 |
| information_extraction | 67.5 | 62.1 | 68.8 |
| instruction_following | 94.2 | 91.2 | 93.3 |
| knowledge_update | 89.2 | 92.5 | 92.5 |
| multi_session_reasoning | 24.2 | 22.8 | 27.3 |
| preference_following | 94.2 | 97.5 | 100.0 |
| summarization | 94.4 | 91.9 | 98.5 |
| temporal_reasoning | 91.7 | 92.1 | 92.1 |

