# Reported system (final5) against the reference evidence and the published answers, annotation-aided prompt

Generated from the per-question records by `python final_compare.py --config final5` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K (400) | **90.17** | 89.51 (5 runs) | +0.66 (-0.64 to +1.96) | 0.839 | 90.82 | 89.7, 90.8, 90.0 | 0 |
| 500K (700) | **87.89** | 87.51 (5 runs) | +0.38 (-0.67 to +1.44) | 0.763 | 88.64 | 88.0, 87.5, 88.2 | 0 |
| 1M (700) | **89.46** | 87.75 (6 runs) | +1.70 (+0.66 to +2.80) | 1.000 | 89.83 | 89.0, 89.4, 89.9 | 0 |
| 10M (200) | **81.44** | 81.69 (7 runs) | -0.25 (-1.99 to +1.54) | 0.392 | 84.48 | 80.8, 81.9, 81.6 | 0 |
| **All (2000)** | **88.25** | 87.41 | +0.84 (+0.24 to +1.44) | 0.997 | 89.08 | | |

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
| abstention | 91.7 | 96.5 | 95.8 |
| contradiction_resolution | 71.9 | 71.6 | 74.2 |
| event_ordering | 99.9 | 99.9 | 99.7 |
| information_extraction | 90.7 | 92.5 | 94.3 |
| instruction_following | 96.9 | 93.8 | 94.2 |
| knowledge_update | 89.0 | 82.9 | 89.4 |
| multi_session_reasoning | 68.6 | 64.8 | 67.7 |
| preference_following | 98.8 | 99.8 | 99.2 |
| summarization | 98.3 | 98.6 | 99.4 |
| temporal_reasoning | 96.0 | 94.8 | 94.4 |

**500K by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 89.8 | 92.7 | 91.7 |
| contradiction_resolution | 73.8 | 72.3 | 73.8 |
| event_ordering | 100.0 | 99.4 | 100.0 |
| information_extraction | 82.7 | 83.6 | 85.6 |
| instruction_following | 91.7 | 89.9 | 91.3 |
| knowledge_update | 85.6 | 83.5 | 85.6 |
| multi_session_reasoning | 66.1 | 67.8 | 69.5 |
| preference_following | 98.4 | 98.7 | 98.8 |
| summarization | 98.0 | 94.8 | 96.7 |
| temporal_reasoning | 92.9 | 92.3 | 93.5 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 93.6 | 91.2 | 95.7 |
| contradiction_resolution | 71.9 | 68.9 | 72.3 |
| event_ordering | 99.6 | 99.3 | 99.5 |
| information_extraction | 81.3 | 81.8 | 83.1 |
| instruction_following | 95.8 | 95.4 | 95.8 |
| knowledge_update | 90.1 | 83.3 | 85.7 |
| multi_session_reasoning | 72.0 | 66.1 | 71.5 |
| preference_following | 97.0 | 97.9 | 99.0 |
| summarization | 99.0 | 98.2 | 99.1 |
| temporal_reasoning | 94.3 | 95.3 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 90.8 | 93.9 | 100.0 |
| contradiction_resolution | 68.5 | 67.5 | 72.3 |
| event_ordering | 99.8 | 99.6 | 100.0 |
| information_extraction | 67.5 | 65.9 | 68.8 |
| instruction_following | 94.2 | 90.5 | 93.3 |
| knowledge_update | 89.2 | 91.8 | 92.5 |
| multi_session_reasoning | 24.2 | 24.6 | 27.3 |
| preference_following | 94.2 | 98.4 | 100.0 |
| summarization | 94.4 | 93.0 | 98.5 |
| temporal_reasoning | 91.7 | 91.6 | 92.1 |

