# The system before the rebuild against the reference evidence, answer call through OpenRouter, annotation-aided prompt (1M and 10M)

Generated from the per-question records by `python final_compare.py --config final4or --route or` (run in `harness/`).

| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |
|---|---:|---:|---|---:|---:|---|---:|
| 100K | not run | | | | | | |
| 500K | not run | | | | | | |
| 1M (700) | **89.37** | 88.11 (2 runs) | +1.27 (+0.10 to +2.52) | 0.984 | 89.83 | 89.5, 89.3, 89.4 | 0 |
| 10M (200) | **82.36** | 81.75 (3 runs) | +0.61 (-1.19 to +2.67) | 0.729 | 84.48 | 83.2, 81.9, 81.9 | 0 |
| **All (900)** | **87.82** | 86.69 | +1.12 (+0.14 to +2.17) | 0.986 | 88.64 | | |

| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |
|---|---:|---:|---|---:|
| 1M (700) | 89.37 | 89.83 | -0.46 (-1.58 to +0.73) | 0.217 |
| 10M (200) | 82.36 | 84.48 | -2.12 (-4.53 to +0.30) | 0.041 |
| **All (900)** | 87.82 | 88.64 | -0.83 (-1.85 to +0.25) | 0.063 |

**1M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 92.7 | 91.1 | 95.7 |
| contradiction_resolution | 72.7 | 71.1 | 72.3 |
| event_ordering | 99.4 | 99.5 | 99.5 |
| information_extraction | 81.4 | 82.9 | 83.1 |
| instruction_following | 96.4 | 94.8 | 95.8 |
| knowledge_update | 89.3 | 83.9 | 85.7 |
| multi_session_reasoning | 71.7 | 67.2 | 71.5 |
| preference_following | 97.5 | 97.9 | 99.0 |
| summarization | 99.2 | 97.8 | 99.1 |
| temporal_reasoning | 93.6 | 94.8 | 96.7 |

**10M by ability** (OpenCrawl / reference evidence / reference published answers)

| Ability | OpenCrawl | Reference evidence | Published answers |
|---|---:|---:|---:|
| abstention | 86.7 | 90.0 | 100.0 |
| contradiction_resolution | 68.8 | 70.6 | 72.3 |
| event_ordering | 99.9 | 99.8 | 100.0 |
| information_extraction | 71.2 | 65.4 | 68.8 |
| instruction_following | 94.6 | 90.8 | 93.3 |
| knowledge_update | 90.8 | 92.5 | 92.5 |
| multi_session_reasoning | 25.5 | 24.1 | 27.3 |
| preference_following | 97.9 | 99.6 | 100.0 |
| summarization | 95.7 | 92.2 | 98.5 |
| temporal_reasoning | 92.5 | 92.5 | 92.1 |

