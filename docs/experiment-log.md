# Experiment log

The chronological record of the work, written as it happened between 2026-11-09 and 2026-11-12: every configuration
tried, what it scored, what was adopted and what was dropped. A last entry holds corrections made on 2026-11-14, and
one earlier entry was corrected in place that day, with a note. It is the long form of Sections 5.5 to 5.7 of the
[paper](../paper/opencrawl-beam.md). Entries were edited for publication to remove references to private
infrastructure, to point paths at this repository's layout, and to leave out the name of the system we compare
with, which is called the reference system throughout, together with the scores it reports for itself by length
(one rounded figure, about 90 over all questions, is kept). No number we measured was changed.

How to read it:

- **Tags** (`t1` to `t39`, `final2`, `final3`, `final4`) name configurations. Their runs are under
  [`results/`](../results/) with the tag in the directory name; `final2`, `final3` and `final4` are the base system,
  base + fact cards and the full system on the first version of the notes; `final5`, the reported system, is the
  full system on the notes rebuilt on 2026-11-12.
- **Prompts.** "Reference protocol", "hinted prompt" and "leaderboard prompt" all mean the annotation-aided prompt
  (`--prompt exabase`). "Hint-free", "paper prompt" and "BEAM's own prompt" mean the benchmark's own prompt
  (`--prompt paper`).
- **Abbreviations** in tables: KU knowledge update, IE information extraction, MH multi-session reasoning, IF
  instruction following, PF preference following.
- **Commit hashes** refer to the development history, which is not part of this repository. They are kept where an
  entry records that a rule or a plan was written down before its results.
- Some entries name one-off maintenance scripts (index clean-up, batch encoding on a GPU, re-linking notes after a
  re-ingest) that are not in this repository.
- Runs marked invalid here are in `results/opencrawl/excluded/` and enter no reported number.
- Intervals of paired replays in entries before 2026-11-12 were computed with one random stream shared across lengths. The published scripts restart the stream for every interval, which moves a few bounds by 0.01 or 0.02.

| Version | Core | Change | 100K | 500K | 1M | 10M | All (reference protocol) | Hint-free all |
|---|---|---|---:|---:|---:|---:|---:|---:|
| v0-baseline | 5258f09 (0.2.54) | stock BM25 search, top 40 excerpts | 84.8 | 83.0 | 84.2 | 80.5 | 83.5 | 53.6 (search) / 62.1 (agent) |

## Experiments on 100K (400 questions; ±~1.5 pt noise)

| Tag | Change vs previous | 100K | KU | IE | MH | Note |
|---|---|---:|---:|---:|---:|---|
| v0 | baseline | 84.8 | 49.4 | 81.6 | 61.2 | |
| t1 | evidence in conversation order | 85.3 | 59.4 | 82.9 | 62.0 | |
| t2 | + 3 LLM keyword rewrites, RRF fusion | 86.9 | 64.4 | 80.5 | 60.4 | 1M 84.9 / 500K 83.9 with core stemming (t3) |
| t3 | + core stemming (PR #137) | 86.3 | 63.1 | 83.1 | 62.0 | retrieval recall +1–3 pts; QA within noise |
| t4 | + iterative follow-up queries (LLM reads top 25, asks for what's missing) | 87.7 | 66.9 | 87.9 | 65.6 | evidence now in context for ~95% of answerable Qs |
| t5 | + point-in-time recall (core `before` bound, PR #137) | **90.0** | **88.7** | 82.3 | 68.9 | matches the reference system's point-in-time protocol |
| t6 | + fetch top 6 passages (3,000 chars) | 89.1 | 86.9 | 87.4 | 63.7 | within noise; A/B on 500K |

Findings:
- Contradiction is capped near 75% by the fixed ExaBase prompt: 61/71 lost rubric points at 1M are "asks which statement is correct", which the prompt never requests.
- Knowledge update needed point-in-time recall: BEAM's gold is the value as of the update turn, and the conversation often changes it again later. The reference system asks those questions as of that moment; OpenCrawl now supports `before`.

## Full splits and semantic retrieval (2026-11-09 early morning)

| Tag | Config | 100K | 500K | 1M | 10M | All |
|---|---|---:|---:|---:|---:|---:|
| t5-pit | expand 3 + follow-up 3 + time order + point-in-time | 90.0 | 87.2 | 86.6 | 81.9 | **87.0** |
| t6-fetch | t5 + fetch top 6 | 89.1 | 86.0 | — | — | dropped |
| t7-sel | t5 + LLM evidence selection (+fill / only) | — | 87.0 / 84.7 | — | — | dropped |
| t8-wide | expand 5 + follow-up 5 + 2 pages | — | — | 86.2 | — | dropped |
| t9-semantic | t5 + core semantic retrieval (learned sparse) | 88.8 | pending | pending | pending | |
| t9 hint-free | BEAM paper prompt, t9 retrieval | 59.1 (v0: 55.8) | | | | |

- At 1M, losses concentrate where cited evidence is incomplete in context (multi-hop 62/70 incomplete; contradiction 44/70). Wider BM25 doesn't fix it; semantic retrieval raises evidence recall@40 from 0.572 to 0.678 at 100K.
- Semantic backfill: host CPU encodes ~9 passages/s (verified identical to OpenSearch's sparse_encoding output: log(1+log(1+relu)), prune < 0.1·max). 1M+10M (282,652 passages) were encoded on one GPU instance with the same encoder.

## Agent memories (notes.py), 07:10

OpenCrawl indexes agent memory files beside sessions. `notes.py` plays the agent's note-taker: per ~6k-token window it writes dated, atomic notes (generic memory policy; no benchmark categories), one memory file per window with `originSessionId` frontmatter, uploaded through `/api/sessions/memories`. Core PR #137 now dates memory passages by file `modifiedAt` and lets `sessionId` scope memories written from that session.

| Tag | 100K reference protocol | 100K hint-free (paper prompt) |
|---|---:|---:|
| t5-pit | 90.0 | — |
| t9-semantic | 88.8 | 59.1 |
| t10-mem (t9 + memories) | 89.9 (IE 80→89) | **61.5** |

Note cost: 100K 2.8M prompt tokens (487 files); 500K 19.1M (3,269 files).

## Same-judge comparison (07:55)

LLM judging is nondeterministic: near-identical contradiction answers got 0.5 (the reference system's run) vs 0.0 (ours) on the "which statement is correct?" item. `rejudge.py` re-grades the reference system's **published answers** with this harness's judge (same model, prompt and scoring rules). The scores it reports for itself are higher at each length and are left out:

| Split | Reference system's published answers, re-judged (same judge as ours) | OpenCrawl (best so far) |
|---|---:|---:|
| 100K | 91.1 | 90.0 (t5) / 89.9 (t10) |
| 500K | 88.4 | **88.2** (t10, re-judged 88.2) |
| 1M | 90.1 | 86.6 (t5); t10 pending |
| 10M | 84.5 | 81.9 (t5); t10 pending |
| All | **89.1** | |

Memory-first evidence (t11) scored 86.5 at 500K (vs 88.2): raw excerpts carry detail the notes drop. Dropped.

## 08:20

| Tag | 500K | 1M | Note |
|---|---:|---:|---|
| t10-mem (semantic + memories) | 88.2 | **88.4** (from 86.6) | reference system, same judge: 88.4 / 90.1 |
| t12-nofollow | 87.7 | | follow-up queries are not the multi-hop problem |
| t12-plain (question only) | 87.5 | | |
| t13-notes2 (precision note prompt + low reasoning note-taker) | **89.0** | | beats the reference system's same-judge 88.4 at 500K |

## 09:55

| Tag | 100K | 500K | 1M | 10M |
|---|---:|---:|---:|---:|
| t10-mem | 89.9 | 88.2 | 88.4 | 80.7 |
| t13-notes2 (precision notes, low reasoning) | 90.0 | **89.0** | 88.1 | 10M notes v2 in progress |
| t14-solnotes (gpt-5.6-sol note-taker) | **90.3** | | | |
| t15-profile (always-loaded profile memory, ~900 words) | | | 88.1 (IF 94→96, PF 96→99; abstention/IE/KU dip from budget) | |
| t15b-leanprofile (instructions + preferences only) | | | pending | |
| Reference system, same judge | 91.1 | 88.4 | 90.1 | 84.5 |

## Final (11:40)

Same judge, 3 passes, OpenCrawl mean of 2 answer runs vs the reference system's published answers: **87.98 vs 89.08** (100K 90.66/90.82, 500K 88.46/88.64, 1M 87.99/89.83, 10M 80.89/84.48). Hint-free final system: 60.1% (100K 61.4, 500K 59.9, 1M 61.9, 10M 51.4).

## Passage-level indexing (core PR #137), beam3 sessions

Diagnosis at 10M: information-extraction questions lost 6 of 20 points with the cited turn *in context*. The turn's 800-char excerpt missed the fact, and the 512-token sparse encoder only saw the first ~2,000 chars of long turns. Core now indexes ≤2,000-char boundary-aware passages that exactly partition each event or memory file (593k session passages vs 327k events). Notes v2 were re-linked to the beam3 sessions without regeneration. Everything was encoded on GPUs. BM25-only evidence recall@40: 1M hit 0.650 → 0.669, 10M 0.523 → 0.545. Final t16 = t13 config on beam3: two runs per split, 3-pass same-judge grading.

## Push for 1M/10M (night 2)

| Tag | 1M | 10M | Note |
|---|---:|---:|---|
| t19 quote curation (luna, top 150, verbatim-verified spans + fill) | **88.9** | 80.8 | IE 1M 80→86; 10M abstention 100→80 (near-miss quotes) |
| t19 curation only (no fill) | 84.7 | | KU 66: needs raw context |
| t20 sol curator + strict relevance | 87.9 | 79.2 | abstention 10M 70 |
| t21 per-turn-dated notes | pending | pending | see below |

Pooling seven 10M runs: the reference system's single run beats *every* one of ours on only 2 of 200 questions. Their lead is consistency, not unreachable questions. The systematic gaps are knowledge update (−7.9) and abstention (curation runs only).

Bug found: notes were dated by window end. A knowledge-update question asked mid-window couldn't see that window's notes, while earlier windows' notes restating the old value stayed visible, biasing answers toward stale values. `turn_notes.py` regroups bullets into per-turn memory files dated at their own turn.

| Tag | 1M | 10M | Note |
|---|---:|---:|---|
| t21 per-turn-dated notes | 88.0 | 81.1 | KU unchanged |
| t22 per-turn notes + memory-first | | 81.6 | **KU 92** (matches the 92.5 reference) but abstention 80 |
| t23 per-turn notes + curation | 87.9 | 80.7 | |

Across 14 configurations, 10M lands between 79.2 and 81.7 (the same-judge reference is 84.5). Every change that makes evidence denser (curation, memory-first notes) raises KU or IE and costs abstention: dense near-miss facts tempt the reader to answer questions about details the history lacks.
| t24 hybrid budget (≤50% notes, rest verbatim) | 88.6 | **81.8** | balanced: abstention 95, KU 88, IE 69 at 10M |
| t25 entity-state ledger + key expansion (on t24) | pending | pending | normalized dated records; value histories |
| t25 ledger (1M) | 87.2 | pending | KU 76, abstention 90: loosely matched histories mix planned/proposed values |
| t26 hybrid budget + pinned lean profile | 88.7 | 80.2 | IF 95 at 10M (> 93 reference); abstention 85 |

10M across 15 configurations: 79.2–81.9 (mean ≈ 80.8; single-run sd ≈ 1). No change has moved the 10M mean beyond noise.
| t27 t24 + answer temperature 0 (BEAM paper §4.1 decoding; disclosed, not identical to the reference harness) | 88.0 / 88.2 | 82.3 / 81.7 | 10M mean 82.0 vs 80.8 plateau |
| t28 t24 + pinned point-in-time state sheet (state.py; core order=newest) | pending | building | |

## Night 3 (2026-11-10): what the reference system's context actually looks like

Measured from the reference system's published per-question results (same message ids as ours):

1. **Context size.** Its answer model reads a mean of 11,001 / 11,749 / 11,339 / 10,467 context tokens (100K / 500K / 1M / 10M), max ~20k; the "8,000 evidence tokens" counter covers only part of the JSON. Ours was ~10.0k (8,000 text tokens + JSON). `--context-tokens N` now budgets the whole context string; we cap at the reference's per-split **mean** (`results/reference/context-tokens.json`).
2. **No profile leakage.** The dataset's user profile, which its harness passes to its system, never appears in its evidence (0 of 900 questions checked).
3. **Composition: narrow and deep.** Per question it shows ~11 (10M) to ~15 (1M) **whole source messages** (mean 600 / 370 tokens, up to 7.8k) plus ~8–14 short typed extractions with ~60–100-token excerpts. Ours was ~50 excerpts of ≤800 characters. BEAM assistant replies have a median of ~3,950 characters, so an excerpt shows ~20% of a reply.
4. **Retrieval is not the difference.** Coverage of BEAM's cited evidence turns in context: 10M 0.38 (reference) vs 0.38 (ours); 1M 0.50 vs 0.46. At 10M knowledge update we cover *more* (0.82 vs 0.75) and score lower (0.85 vs 0.93).

Consequences: `--deep N` (top N transcript hits as full passages) and `--deep-whole` (whole messages assembled through core's new fetch `previousId`/`nextId`), run with the matched context cap.

| Tag | 1M | 10M | Note |
|---|---:|---:|---|
| t29 matched context cap only (t24 + cap) | pending | 81.4 / 81.1 | cap alone: no change at 10M |
| t30 deep passages (10M: deep10-s25 / deep10-s50 / deep15-s25) | | 81.8 / 81.7 / 82.0 | pool still contained ledger + profile files (see below) |
| t31 whole messages (10M: whole10-s25 / whole12-s20 / whole8-s40) | | 81.9 / 82.8 / 82.2 | same contaminated pool; multi-hop 28–37 (from ~22–28) |
| t29 matched context (1M) | 88.9 / 87.9 | | |

### Pool contamination found and fixed (04:50)

`debug_question.py` (replays one question and prints the evidence) showed ledger lines from the t25 experiment — and, for 1M, every state sheet — were still live in the same memory pool as the notes, so t26–t31 retrieved them as "memory notes". Fix: the ledger and profile files were retired with an empty newer generation; state sheets moved to their own memory space `<session>-state`, looked up explicitly with core's `order=newest` + `before`; run.py also drops any stray state/ledger/profile hit from ordinary results. t28 (contaminated state runs) was killed and discarded.

Clean-pool reruns (whole12, share 0.2, matched context), 10M: rank order 81.2, time order 80.5.

### Who said it: 94% of cited evidence at 10M is user messages

BEAM's cited evidence turns are user messages 94% of the time at 10M and 73% at 1M (100% for contradiction, knowledge update, temporal, instruction and preference questions); assistant replies (median ~3,950 characters) dominate the index by volume. Core now filters session search by message role (PR #137). Prototype (`proto_role.py`, question as query, top 40, as-of bounded): recall of cited turns 0.46 → 0.59 at 1M, 0.40 → 0.49 at 10M; full coverage 0.28 → 0.42 and 0.28 → 0.35. `--user-pass W` runs every recall query a second time with `role=user` and fuses it with weight W.

Also measured: the reference system's retrieval covers cited turns no better than ours did before this (10M 0.38 vs 0.38; 1M 0.50 vs 0.46) — its edge was presentation (whole messages, relevance order), not recall.

### User pass at 10M (clean pool; whole12, share 0.2, matched context)

| Config | 10M runs | mean | multi-hop | IE |
|---|---|---:|---:|---:|
| no user pass, rank / time (t32) | 81.2 / 80.5 | 80.9 | 22 | 62 |
| user pass 1.0, rank (t34) | 82.0, 80.1 | 81.0 | 30 | 68 |
| user pass 1.0, time (t34) | 81.4, 82.8 | **82.1** | 28 | 66 |
| user pass 2.0, rank (t34) | 81.7, 81.9 | 81.8 | 30 | 66 |

1M t32 runs (rank / time, no user pass) were invalid: 73 and 49 questions failed with "search failed" because OpenSearch timed out under ten concurrent runs plus a vector import. Partial scores before the overload: time 88.6 (540 Q), rank 87.6 (500 Q). Index then cleaned of superseded passages (1.55M → 955k passages, 3 segments).

### The decisive control: the reference's own evidence, answered today (`replay_reference.py`)

The reference's published results contain, for every question, the exact evidence its answer model read. Passing that evidence **verbatim** through the same answer call (same prompt function, `gpt-5.6-luna`, reasoning none, OpenAI API) and the same judge we use for OpenCrawl:

| Split | Reference published answers (same judge, 3 passes) | Reference published evidence, answered today |
|---|---:|---:|
| 1M | 89.83 | **88.08** (1 run) |
| 10M | 84.48 | **81.32** (mean of 2 runs) |

So the reference's lead over OpenCrawl at 1M/10M is in its *answer set* (generated about six weeks earlier through OpenRouter), not in its *memory*: with identical answering and judging its evidence scores where OpenCrawl's does (1M ~88.0–88.9; 10M ~81–82.8).

Ablations of the reference's evidence at 10M (2 answer runs each): time order 82.1 (vs rank 81.3); OpenCrawl's item format 82.0 (rank) / 82.5 (time); source messages cut to 800 chars 81.0; no excerpts on extractions 80.8; whole messages only 79.1; typed extractions only 75.3. At 1M (1 run): raw 88.1, time 88.5, OpenCrawl format 86.6, sources only 86.9.

Open question being tested: whether answer reasoning effort (OpenRouter may not have honoured "none") reproduces the published answers' level.

### Reasoning effort is not the explanation (replay, 10M, 2 answer runs each)

Reference evidence answered with reasoning low / medium: 77.5 / 78.3 (summarization falls to ~57: with reasoning the model stops restating hinted aspects the evidence does not support). Three more plain replays: 81.21. So the reference's own evidence, answered today, is 81.2–81.3 at 10M across five runs; its published answers (84.48 under our judge) cannot be reproduced from that evidence with today's API.

Reference-evidence replays on the other splits (3 answer runs each): 100K 89.66, 500K 87.22, 1M 87.84 (4 runs).

### More candidates (10M unless noted)

| Config | Runs | Mean | Note |
|---|---|---:|---|
| user pass 1.0, time (t34) + recent 6 user messages (t35) | 80.7, 80.9 | 80.8 | KU +2.5, others down; not adopted |
| user pass 1.0, time + verbatim-supersedes-notes (t36) | 80.1, 82.5, 81.4 | 81.3 | fixes the "price not provided" note commentary (KU 85.0), abstention swings; not adopted |
| 1M: user pass 1.0, time (t35-a/b) | 89.5, 89.0 | 89.2 | vs reference evidence 87.84 |
| 1M: + recent 6 (t35-recent-a) | (partial) | | |

Notes defect found with `debug_question.py`: 0.3% of note bullets add the note-taker's own commentary ("the original price was not provided"), which the answer model repeats even when the evidence contains the value. `--dedupe-notes` drops notes about turns whose own message is in the evidence.

### Frozen configuration "final2" (06:02)

`--expand 3 --follow-up 3 --point-in-time --memories --deep 12 --deep-whole --memory-share 0.2 --user-pass 1.0 --order time --context-tokens <reference mean for the split>`, per-turn notes, passage index. Headline numbers use only runs launched after the freeze (tag `final2`); `final_compare.py` computes means, a paired bootstrap over questions against the reference-evidence replay, and per-ability tables (`--paper` for the annotation-free prompt, `--with-selection` to include the earlier runs of the same configuration).

## Final2: controlled comparison, post-freeze runs (2026-11-10 07:10)

Three answer runs per split, launched after the freeze, zero failed questions (`results/tables/base-annotation-aided.md`):

| Split | OpenCrawl | Reference evidence, same answer call | Δ (95% CI) | Reference published answers |
|---|---:|---:|---|---:|
| 100K | 90.01 (89.6, 90.2, 90.2) | 89.66 | +0.35 (−0.75 to +1.51) | 90.82 |
| 500K | 87.71 (88.2, 87.2, 87.7) | 87.22 | +0.49 (−0.72 to +1.64) | 88.64 |
| 1M | 89.20 (89.1, 89.0, 89.5) | 87.84 | +1.36 (+0.30 to +2.46) | 89.83 |
| 10M | 82.20 (83.4, 81.1, 82.1) | 81.25 | +0.95 (−1.31 to +3.25) | 84.48 |
| All | 88.14 | 87.33 | +0.81 (+0.16 to +1.45) | 89.08 |

Pre-freeze runs of the same configuration agree: 1M 89.5, 89.0; 10M 81.4, 82.8.

After the freeze, tested and not adopted:
- Collapse (core: one passage per message), 500K: 87.8 (87.9, 87.7) vs 87.7; with notes share 0.4: 87.4. Abstention 87.9 → 93.9, multi-hop 65.3 → 61.7.
- Dedupe notes at 10M: abstention 85–90 in all three runs vs 95–100 in all five runs without it.
- Pinned state sheets at 1M (paired, 240 questions): 88.6 vs 90.2 without. The 10M state build was stopped; sheets moved out of the pool.

Small splits: the frozen configuration is below the 2026-11-09 one there (100K 90.01 vs 90.66; 500K 87.71 vs 88.46), mostly abstention (whole assistant messages tempt the reader). A no-whole-messages variant is being tested at 500K (t38).

## Annotation-free controlled comparison and presentation robustness (2026-11-10 08:20)

**Annotation-free (BEAM's own prompt), final2, 2 answer runs per split, 0 failed** (`results/tables/base-own-prompt.md`):

| Split | OpenCrawl | Reference evidence, same answer call | Δ (95% CI) |
|---|---:|---:|---|
| 100K | 60.32 (60.1, 60.6) | 59.67 | +0.64 (−1.75 to +3.10) |
| 500K | 61.03 (61.2, 60.9) | 60.51 | +0.52 (−1.51 to +2.56) |
| 1M | 61.17 (61.5, 60.9) | 58.89 | +2.28 (+0.49 to +4.06) |
| 10M | 49.68 (48.3, 51.1) | 46.66 | +3.03 (−1.24 to +7.36) |
| All | 59.80 | 58.39 | +1.41 (+0.27 to +2.56) |

The frozen configuration is not better than the 2026-11-09 one hint-free (59.8 vs 60.1).

**Presentation robustness** (reference evidence re-presented, 3 answer runs per variant; `final_compare.py --ref time|ourfmt-time`):

| Split | OpenCrawl | as published | time order | our format + time order |
|---|---:|---:|---:|---:|
| 100K | 90.01 | 89.66 | 89.93 | 88.86 |
| 500K | 87.71 | 87.22 | 87.73 | 86.61 |
| 1M | 89.20 | 87.84 | 87.79 | 87.58 |
| 10M | 82.20 | 81.25 | 81.51 | 82.64 |
| All | 88.14 | 87.33 | 87.57 | 87.00 |
| Δ All (95% CI) | | +0.81 (+0.16 to +1.45) | +0.57 (−0.08 to +1.20) | +1.13 (+0.49 to +1.77) |

Reading: the 1M lead is in the evidence (+1.36 / +1.41 / +1.61, all intervals above zero). 100K and 500K are ties once the reference evidence is time-ordered. 10M is a tie under every presentation (−0.43 to +0.95). The earlier 2-run 10M ablation that put "our format, time order" at 82.5 is confirmed by 3 fresh runs (82.64).

**Post-freeze variants at 500K, not adopted:** no whole messages (t38) 87.4 (2 runs); no whole messages + collapse 87.7 (2 runs); final2 is 87.7.

## Where the remaining losses are (2026-11-10 08:30–09:00)

`diag_cited.py` replays retrieval for every question of the frozen configuration and records whether BEAM's cited evidence turns are in the evidence the answer model reads (as a transcript passage or as a note about that turn). Joined with the three final2 runs:

| Split | Questions-equivalent lost with every cited turn present | Lost with some cited turn missing |
|---|---:|---:|
| 100K | 26.5 | 10.8 |
| 500K | 60.9 | 16.7 |
| 1M | 38.5 | 33.8 |
| 10M | 17.1 | 17.8 |

Most of what is still lost is lost with the cited turns in front of the reader. By ability:
- **Contradiction** (100K 10.2, 500K 15.2, 1M 11.2 lost with full coverage): the rubric ceiling, same for every system.
- **Multi-session reasoning** (500K 19.3 lost with full coverage): mostly questions where the gold is a sum over a subset the question does not identify, or is arithmetically wrong (e.g. gold "$770" for $340 + $70 + $180); the reference's published answers score 0 on the same questions.
- **Information extraction at 10M** (5.7 lost with the cited turn present): several near-identical statements with different values ("mocked 5,000 sensor inputs" vs "simulated 10,000 points" for a question about mocking sensor APIs); the reference loses the same questions.
- **Information extraction at 1M** is the one place retrieval still costs: 20 of 70 questions miss a cited turn and score 0.62, against 0.89 for the 50 with full coverage. Most are "How did you recommend ..." questions that describe an assistant reply abstractly, without its nouns.
- **Knowledge update / extraction, reader side**: the fact is present but stated in passing inside a request ("worried that moving my Saturday budget review to 5 PM might conflict ...", "Nancy's training on May 8, 2024"), and the reader hedges or prefers an older, more explicit value. The reference system's evidence leads with a normalized one-line claim for the same turn, stating the event and its new time, and its reader commits.

Gap to the reference's published answers is about 4.5 questions at 1M and 4.5 at 10M, spread thinly: preference following (answers mention the option the user rejected; rubric says "avoids suggesting ..."), knowledge update at 10M, extraction.

Checks on the unreproducible published answers:
- `gpt-5.6-luna` has no dated snapshots on the API, so a silently changed model is not visible from here.
- Their harness code builds the context from exactly the saved evidence object.
- Numbers in their published 10M answers are found in their published evidence at the same rate as in our replays (0.047 vs 0.027 ungrounded, the difference being computed totals in multi-session answers), so the published evidence is what their model read.

### Fact cards (new, 09:00)

`facts.py`: one pass over the user's messages only (windows of 12 messages, `gpt-5.6-luna`, reasoning low), writing what each message states or takes for granted as short lines, "Saturday budget review: moved to 5 PM, but the user is concerned it might conflict with their tutoring schedule". One memory file per user turn, dated at the turn, stored through the memories API beside the notes. Run flags `--facts --clean-notes` (the latter drops the notes' file front matter from what the reader sees).

Configuration "final3" = final2 + `--facts --clean-notes`, fixed before any run (`harness/run_config.sh base-fact-cards`).

## final3 (fact cards) complete; paired presentation replays; contradiction ceiling (2026-11-10 10:35)

**final3** = final2 + `--facts --clean-notes`, fixed before any run; 3 runs per split, 0 failed questions (`results/opencrawl/base-fact-cards/`):

| Split | final2 | final3 | Δ (95% CI) | final3 runs | vs reference evidence | vs published answers |
|---|---:|---:|---|---|---|---|
| 100K | 90.01 | 90.47 | +0.47 (−0.30 to +1.25) | 90.1, 90.9, 90.4 | +0.81 (−0.37 to +2.06) | −0.34 (−1.39 to +0.73) |
| 500K | 87.71 | 87.78 | +0.08 (−0.72 to +0.86) | 88.0, 87.6, 87.7 | +0.56 (−0.59 to +1.69) | −0.85 (−2.01 to +0.25) |
| 1M | 89.20 | 88.95 | −0.25 (−0.97 to +0.48) | 89.0, 88.8, 89.0 | +1.11 (+0.01 to +2.29) | −0.89 (−1.97 to +0.23) |
| 10M | 82.20 | 82.92 | +0.72 (−1.08 to +2.77) | 82.8, 84.0, 81.9 | +1.67 (−0.02 to +3.56) | −1.55 (−3.68 to +0.59) |
| All | 88.14 | 88.24 | +0.10 (−0.34 to +0.56) | | +0.91 (+0.27 to +1.55) | −0.83 (−1.46 to −0.21) |

By ability, final3 minus final2: knowledge update +2.5 / +0.7 / +2.6 / +3.3; extraction +1.1 / −2.1 / −1.0 / +9.2; abstention +0.8 / +2.4 / −2.6 / −3.3; temporal +0.6 / −0.8 / −2.0 / 0.0. Build: 154,883 cards, ~25M tokens, 35 minutes; sparse-encoded on one GPU instance.

**Paired presentation replay** (`replay_variants.py`: retrieve once per question, answer under each variant 3 times; unchanged contexts reuse the base answers). 10M:

| Base | Variant | Δ (95% CI) |
|---|---|---|
| final3 evidence (82.36) | lint: drop absence clauses from notes | +0.64 (−0.17 to +1.90) |
| | qualify: keep them, marked as scoped to the message | +0.33 (−0.37 to +1.42) |
| | five best-ranked items first | +0.08 (−1.79 to +1.90) |
| | notes first | −0.10 (−1.93 to +1.67) |
| no cards (82.89) | lint | −0.17 (−0.50 to +0.12) |
| | cards share the notes budget (= final3) | +0.45 (−1.33 to +2.26) |
| | cards as their own 8% layer | +0.71 (−1.08 to +2.72) |
| | 8% layer + lint | +0.61 (−1.10 to +2.48) |

**Contradiction ceiling, measured**: in 1M run final2-a the rubric item "which statement is correct?" fails in 65 of 70 contradiction questions; "states there is a contradiction" fails in 0 of 70. Premise check for conflict notes (hand-built from the cited turns of four 100K questions, not scored into any result): with a note stating the conflict "needs the user's clarification", and with a note-to-self "ask the user which statement is correct", the reader still does not ask (scores 1.00/0.75/0.75/0.50 and 1.00/0.75/0.75/0.62 against 0.75/1.00/0.75/0.75 without). Not built.

Also: `profile.py` → `profile_memory.py` (it shadowed the stdlib module and broke torch imports); host CPU sparse encoding is 1–3 docs/s while runs are active.

## Paired replays complete; drift checks (2026-11-10 11:15)

- **Role clarity** (final2 evidence, 3 answers per arm): legend 100K −0.34 (−1.18 to +0.53), 500K +0.02 (−0.72 to +0.73); role labels 100K −0.10 (−1.05 to +0.92), 500K −0.89 (−1.74 to −0.09). Abstention +2 to +2.6 with the legend, other abilities down. Not adopted.
- **Card designs at 1M** (700 questions, base = same search results without cards, 88.79): shared budget +0.56 (−0.20 to +1.30); 8% layer +0.48 (−0.38 to +1.34). Pooled with 10M: +0.53 (−0.17 to +1.25) and +0.53 (−0.26 to +1.30).
- **Published answers**: `minimal` reasoning is not supported for `gpt-5.6-luna`; their 10M evidence through the Responses API scores 82.29 (3 runs; Chat Completions 81.25, published 84.48); their answers are stylistically indistinguishable from our replays (141 of 700 identical at 1M); their summaries carry no call counts; all four splits finished on one day, about six weeks before ours.
- `llm.py`: `BEAM_ANSWER_API=responses` sends the answer call through the Responses API (check only; default unchanged).

## Role focus (2026-11-10 11:40)

`replay_variants.py` design `rolefocus`: an LLM call on the question alone returns user / assistant / both (500K: 61% user, 24% assistant, 15% both); for "user" questions the evidence is rebuilt from the same search results without assistant passages. 3 answers per arm, 700 questions each: 500K −0.26 (−1.05 to +0.51), 1M +0.17 (−0.61 to +0.93). By ability at about 500 questions: abstention +0.3 / +2.4, extraction +0.7 / +1.5, multi-session −3.3 / −4.1. Not adopted; 100K and 10M replays cancelled.

OpenCrawl's hosted search is lexical BM25 without reranking, so there is no hosted reranker to mirror in the evaluation.

## Fact cards under BEAM's own (annotation-free) prompt (2026-11-10 12:20)

final3 with `--prompt paper`, two answer runs per split, 0 failed questions (`harness/run_config.sh base-fact-cards paper`):

| Split | final2 | final3 | Δ (95% CI) | final3 runs | Reference evidence, same answer call (2 runs) | final3 − reference (95% CI) |
|---|---:|---:|---|---|---:|---|
| 100K | 60.32 | 61.31 | +0.99 (−1.11 to +3.13) | 61.2, 61.4 | 59.67 | +1.64 (−0.86 to +4.16) |
| 500K | 61.03 | 60.97 | −0.06 (−1.53 to +1.40) | 60.9, 61.0 | 60.51 | +0.45 (−1.51 to +2.41) |
| 1M | 61.17 | 61.69 | +0.52 (−0.77 to +1.82) | 61.5, 61.8 | 58.89 | +2.80 (+0.97 to +4.60) |
| 10M | 49.68 | 51.91 | +2.23 (−0.17 to +4.68) | 52.5, 51.3 | 46.66 | +5.25 (+1.29 to +9.30) |
| All | 59.80 | 60.38 | +0.58 (−0.29 to +1.42) | | 58.39 | +1.99 (+0.87 to +3.13) |

By ability, final3 minus final2: information extraction +3.3 / +2.3 / +1.2 / +5.0 and knowledge update +3.1 / +1.1 / +3.9 / +5.0 on every split.

**Replication, declared before it is run (commit cdcf362, 12:20; runs launched after it):** this is two runs per split and the second configuration looked at under this prompt, so before it is quoted anywhere:
- one more final3 answer run per split under the paper prompt (tag `final3-c`);
- two more replays per split of the reference evidence under the paper prompt (`replay-<split>-raw_paper2`);
- every run is reported and pooled, whatever it shows.

## Hint-free replication complete (2026-11-10 13:05)

As declared in commit `cdcf362`: third final3 run per split under the paper prompt (100K 62.8, 500K 61.1, 1M 61.9, 10M 52.8) and two more replays per split of the reference evidence (100K 60.09, 500K 60.49, 1M 58.84, 10M 46.27). Pooled, 0 failed questions:

| Split | final3 (3 runs) | Reference evidence (4 runs) | Δ (95% CI) | P(Δ>0) |
|---|---:|---:|---|---:|
| 100K | 61.82 (61.2, 61.4, 62.8) | 59.88 | +1.94 (−0.43 to +4.36) | 0.945 |
| 500K | 61.02 (60.9, 61.0, 61.1) | 60.50 | +0.52 (−1.31 to +2.38) | 0.708 |
| 1M | 61.77 (61.5, 61.8, 61.9) | 58.87 | +2.90 (+1.18 to +4.63) | 0.999 |
| 10M | 52.20 (52.5, 51.3, 52.8) | 46.46 | +5.74 (+1.63 to +9.92) | 0.997 |
| All | 60.56 | 58.40 | +2.16 (+1.08 to +3.27) | 1.000 |

Presentation robustness under the same prompt (reference evidence re-presented, 2 runs per split): time order 60.01 / 60.73 / 59.79 / 46.15 (All 58.80; Δ +1.76, +0.69 to +2.82); OpenCrawl's item format in time order 60.02 / 60.25 / 58.43 / 46.05 (All 58.14; Δ +2.42, +1.40 to +3.45). 1M and 10M stay significant under both.

final3 vs final2 hint-free: +1.50 / −0.01 / +0.59 / +2.52, All +0.76 (−0.04 to +1.54).

## Conflict notes (2026-11-10 12:30–13:05)

`conflicts.py`: candidates are fact cards in which the user says they have never / not yet done, used or had something (3,448 of 248,213 facts); the product's search (role=user, before the candidate's time) returns the user's earlier messages on the topic; one LLM call decides whether an earlier message reports what the later one denies; each conflict becomes a memory file dated at the later turn, quoting both messages. 2,783 conflicts (141 / 633 / 587 / 1,422), 1,327 files. A first version dropped most conflicts because the verifier answered with turn numbers and the code expected list positions; fixed before the build.

- Diagnostic against BEAM's cited turns at 100K (not used by the system): the mined conflicts cover both sides of 25 of the 40 contradiction questions and one side of 6. The other 88 mined conflicts are genuine too (sampled); the conversations contain many more denials than the benchmark asks about.
- Premise check under BEAM's own prompt, hand-built notes on 16 questions: contradiction 23.0 → 37.5. (Under the hinted prompt the same notes change nothing: its guidance already tells the reader what to say.)
- Paired replay, hint-free, identical retrieval (`--base noconf --variants all`): 100K +0.74 (−0.19 to +1.70), contradiction +4.9; 500K +1.50 at 448 questions (+0.45 to +2.59), contradiction +8.2. 1M, 10M and the hinted prompt are running.

## Conflict notes, first form: mixed (2026-11-10 13:10)

Paired replay under BEAM's own prompt, identical retrieval, notes quoting both messages at length and sharing the notes budget:

| Split | Questions whose evidence changes | Δ (95% CI) | Contradiction Δ |
|---|---:|---|---:|
| 100K (400) | 148 | +0.74 (−0.19 to +1.70) | +4.9 |
| 500K (700) | 215 | +1.58 (+0.83 to +2.39) | +8.2 |
| 1M (452 of 700, stopped) | 76 | −0.39 (−1.28 to +0.35) | +2.3 |
| 10M (200) | 32 | +0.26 (−0.68 to +1.37) | +1.0 |

Why 1M lost: BEAM packs a denial and an updated value into one message ("I have never received any client feedback ..., which seems strange given that the number of reviews received in June increased to 7"). The note quoted the earlier message with the old value ("reviews from 5 clients") and the reader then answered 5. The long notes (about 180 tokens) also pushed two or three other notes out of the 20% share.

**Second form (generation 2, built 13:12):** one short bullet per denial naming the two claims without numbers, dates or versions and pointing at the turns ("Earlier (turn 1234 on 2024-06-20, turn 1298 on 2024-06-20) the user reported receiving positive client reviews; here (turn 1378) the user says they have never received client feedback or reviews. Both cannot be true, and the user has not said which is correct."), and its own budget layer (`--conflicts-share 0.03`), so it displaces nothing from the notes share. The product's search returns only the current generation (checked).

**Adoption rule, written before any second-form result was read:** conflict notes go into a new configuration (final4 = final3 + `--conflicts --conflicts-share 0.03`) only if the paired replays over all four splits show
1. under BEAM's own prompt, a pooled effect whose 95% interval is above zero, and
2. under the hinted prompt, a pooled effect whose interval's lower end is above −0.5.

If adopted, final4 gets three fresh runs per split under each prompt, reported whatever they show. If not, conflict notes are reported as tested and final3 stays.

## Conflict notes, second form: adopted as final4 (2026-11-10 14:05)

Paired replays on identical retrieval, 3 answers per arm, all 2,000 questions under each prompt (`pooled_paired.py pv7p all`, `pv7x all`):

| Split | BEAM's own prompt: Δ (95% CI) | Hinted prompt: Δ (95% CI) | Questions whose evidence changes (own / hinted) |
|---|---|---|---:|
| 100K | +1.10 (+0.14 to +2.12) | −0.26 (−0.90 to +0.20) | 100 / 105 |
| 500K | +1.18 (+0.54 to +1.84) | −0.16 (−0.45 to +0.11) | 141 / 140 |
| 1M | +0.41 (−0.00 to +0.84) | +0.04 (−0.13 to +0.20) | 71 / 81 |
| 10M | +0.73 (+0.02 to +1.62) | −0.29 (−0.73 to +0.00) | 22 / 18 |
| All | **+0.85 (+0.51 to +1.20)** | −0.12 (−0.30 to +0.03) | |

By ability under BEAM's own prompt: contradiction resolution +7.0, abstention +1.0, temporal +0.5, everything else within ±0.3. Under the hinted prompt: abstention −1.1, multi-session −0.5, contradiction +0.4.

Both conditions of the rule written at 13:20 (commit `fd9d3d6`) hold: the interval under BEAM's own prompt is above zero, and the lower end under the hinted prompt (−0.30) is above −0.5. **final4 = final3 + `--conflicts --conflicts-share 0.03`** (`harness/run_config.sh full-system`). Fresh runs, three per split under each prompt, launched 14:06; they are reported whatever they show.

## final4 under BEAM's own prompt: ahead on every split (2026-11-10 15:00)

Three fresh runs per split, 0 failed questions (`harness/run_config.sh full-system paper`; `results/opencrawl/full-system/`):

| Split | final4 | Runs | Reference evidence (4 runs) | Δ (95% CI) | vs final3 (95% CI) |
|---|---:|---|---:|---|---|
| 100K | 62.48 | 63.3, 61.5, 62.6 | 59.88 | +2.60 (+0.15 to +5.07) | +0.66 (−0.76 to +2.14) |
| 500K | 62.41 | 62.1, 63.4, 61.7 | 60.50 | +1.91 (+0.12 to +3.73) | +1.39 (+0.27 to +2.50) |
| 1M | 62.14 | 62.0, 62.0, 62.4 | 58.87 | +3.27 (+1.58 to +5.00) | +0.37 (−0.64 to +1.39) |
| 10M | 52.57 | 53.0, 51.1, 53.6 | 46.46 | +6.11 (+1.92 to +10.33) | +0.37 (−1.64 to +2.40) |
| All | 61.34 | | 58.40 | +2.94 (+1.87 to +4.03) | +0.78 (+0.16 to +1.41) |

Contradiction resolution, final4 minus final3: +8.9 / +9.7 / +4.9 / +3.1. Presentation robustness (reference evidence re-presented): time order All +2.55 (+1.48 to +3.61), 500K +1.68 (−0.12 to +3.49); OpenCrawl's format in time order All +3.20 (+2.15 to +4.25), every split significant.

Hinted final4 runs (`run_config.sh full-system exabase`) started 14:57.

Side test, not adopted so far: a "timeline" layer (fact cards about the question's subject, fetched oldest-first, at most 10% of the evidence), paired replay under BEAM's own prompt at 100K: +0.93 (−1.15 to +3.01) on the first 164 questions, with event ordering, its target, at −1.8.

Timeline layer, complete 100K paired replay under BEAM's own prompt (400 questions): +0.23 (−1.11 to +1.59); event ordering −0.6, contradiction +2.4, knowledge update +1.3. Not adopted; the 500K replay was cancelled at 156 questions.

## final4 under the leaderboard prompt (2026-11-10 15:52)

Three fresh runs per split, 0 failed questions (`run_config.sh full-system exabase`):

| Split | final4 | Runs | Reference evidence | Δ (95% CI) | Published answers | Δ (95% CI) | vs final3 (95% CI) |
|---|---:|---|---:|---|---:|---|---|
| 100K | 90.27 | 90.3, 90.3, 90.2 | 89.66 | +0.61 (−0.67 to +1.92) | 90.82 | −0.55 (−1.89 to +0.78) | −0.20 (−1.12 to +0.64) |
| 500K | 87.76 | 88.0, 87.3, 88.0 | 87.22 | +0.54 (−0.57 to +1.63) | 88.64 | −0.88 (−1.97 to +0.18) | −0.02 (−0.66 to +0.60) |
| 1M | 89.57 | 89.9, 89.7, 89.2 | 87.84 | +1.73 (+0.69 to +2.87) | 89.83 | −0.26 (−1.32 to +0.83) | +0.62 (+0.08 to +1.19) |
| 10M | 83.69 | 83.9, 82.5, 84.6 | 81.25 | +2.44 (+0.62 to +4.52) | 84.48 | −0.79 (−2.97 to +1.47) | +0.77 (−0.35 to +2.01) |
| All | 88.49 | | 87.33 | +1.16 (+0.52 to +1.80) | 89.08 | −0.59 (−1.21 to +0.05) | +0.25 (−0.11 to +0.61) |

1M + 10M: +1.89 over the reference evidence (+0.96 to +2.87); −0.38 against the published answers (−1.32 to +0.60). Reference evidence re-presented: time order All +0.92 (+0.34 to +1.50), 1M +1.78, 10M +2.18 (+0.12 to +4.49); OpenCrawl's format in time order All +1.49 (+0.89 to +2.08), 1M +1.99, 10M +1.05 (−1.03 to +3.34). final4 vs final2: +0.35 (−0.11 to +0.82); 10M +1.49 (−0.03 to +3.38).

The fresh-run step from final3 (+0.25) is larger than the paired estimate for conflict notes under this prompt (−0.12, −0.30 to +0.03); the difference is within run-to-run noise.

## OpenRouter route (2026-11-10 16:10–)

`llm.py`: `BEAM_ANSWER_API=openrouter` / `BEAM_JUDGE_API=openrouter` send the answer / judge call to OpenRouter with exactly the reference harness's payload (`openai/gpt-5.6-luna`, reasoning `{"effort": "none"}`, usage included, one user message; only the Authorization header). OpenRouter resolves the model to `openai/gpt-5.6-luna-20260709` and limits this new account to 20 requests a minute, so requests are spaced at 18 a minute and runs go one at a time. That dated id is not callable on the OpenAI API (404).

**Reference evidence at 10M, answered through OpenRouter, same judge as everything else: 81.60** (2 runs, 400 answers, all served by provider OpenAI). Direct OpenAI route: 81.25 (5 runs); Responses API: 82.29; reference published answers: 84.48. The route does not explain the published answers.

Queue on the OpenRouter route: OpenCrawl final4 at 10M (2 runs, running), reference evidence at 1M, OpenCrawl final4 at 1M, then a judge-route check.

## Note lint on final4 evidence: rule written before results (16:50)

Remaining gap to the reference's published answers under the leaderboard prompt: 1M −0.26, 10M −0.79, spread over single questions. One has a known cause: `10_knowledge_update_0` (10M) fails in two of three final4 runs because a narrative note says the original price "was not provided" although it is in the evidence. The lint (drop note clauses that assert absence) was mixed earlier (+0.64 on evidence with cards, −0.17 without, both at 10M).

Rule: lint goes into a configuration final5 = final4 + lint only if, on final4 evidence with identical retrieval (3 answers per arm),
1. the pooled effect over 1M and 10M under the leaderboard prompt has a 95% interval above zero, and
2. the pooled effect over 1M and 10M under BEAM's own prompt has an interval whose lower end is above −0.5;
and then only if the same two checks on 100K and 500K leave the all-split pooled lower ends above −0.3 under each prompt. Otherwise final4 stays as it is.

## OpenCrawl at 10M through OpenRouter; lint rule not met (2026-11-10 17:12)

**Both systems at 10M with the answer call on the reference harness's route (OpenRouter), same judge as everywhere else:**

| | Runs | Score | By ability (abstention / contradiction / extraction / knowledge update / multi-session) |
|---|---|---:|---|
| OpenCrawl final4 | 83.25, 81.93 | 82.59 | 85 / 68 / 70 / 92 / 29 |
| Reference evidence | 2 runs | 81.60 | 95 / 69 / 64 / 92 / 22 |
| Difference | | +0.99 (−1.37 to +3.45), P = 0.80 | |
| Reference published answers | | 84.48 | OpenCrawl −1.89 (−4.58 to +0.73) |

Zero failed questions. On the direct route the same comparison is 83.69 (83.9, 82.5, 84.6) against 81.25: +2.44 (+0.62 to +4.52). The reference evidence scores the same on both routes (81.60 / 81.25). OpenCrawl's two OpenRouter runs sit at the low end of its direct-route range, mostly through abstention (85 in both, against 96.7 direct: six failures in 40 answers against two in 60, on questions that are also unstable on the direct route). Two runs do not establish a route effect.

The first OpenRouter run's summary step crashed on the new usage keys after all questions were scored; `run.py` now merges them, and the two summaries were rebuilt from the saved results (with `scoring.summarize`).

**Lint on final4 evidence** (rule written at 16:43, commit `5b210e8`), pooled over 1M and 10M, identical retrieval, 3 answers per arm: leaderboard prompt +0.01 (−0.37 to +0.44); BEAM's own prompt −0.39 (−1.02 to +0.21). It fixes `10_knowledge_update_0` in every run (0, 0, 0 → 1, 1, 1) and gives the same amount back elsewhere. Condition 1 is not met; final4 stays as it is.

Still queued on OpenRouter (18 requests a minute): reference evidence at 1M (1 run), then OpenCrawl final4 at 1M (2 runs).

## OpenRouter route, 1M (2026-11-10 19:25)

Answers through OpenRouter (`openai/gpt-5.6-luna`, the reference harness's payload), same judge as everywhere else, 0 failed questions:

| Split | OpenCrawl final4 (runs) | Reference evidence | Δ (95% CI) | P(Δ>0) | Reference published answers | Δ (95% CI) |
|---|---|---:|---|---:|---:|---|
| 1M | 89.38 (89.5, 89.3) | 88.24 (1 run) | +1.15 (−0.09 to +2.48) | 0.965 | 89.83 | −0.45 (−1.58 to +0.77) |
| 10M | 82.59 (83.2, 81.9) | 81.60 (2 runs) | +0.99 (−1.37 to +3.45) | 0.795 | 84.48 | −1.89 (−4.58 to +0.73) |
| 1M + 10M | 87.87 | 86.76 | +1.11 (+0.01 to +2.24) | 0.977 | 88.64 | −0.77 (−1.85 to +0.35) |

Reference evidence on the two routes: 1M 88.24 (OpenRouter) / 87.84 (direct); 10M 81.60 / 81.25. OpenCrawl final4: 1M 89.38 / 89.57; 10M 82.59 / 83.69. The route does not reproduce the reference's published answers (89.83, 84.48) at either split. Every call was served by provider OpenAI.

## A third-party relevance model as a retrieval-side filter: stopped (2026-11-10 19:50–19:59)

A third-party model that scores a passage's relevance to a question was tried as a filter or re-ranker between
search and evidence assembly, as a paired replay on the full system's evidence at 1M and 10M. The test was stopped
by decision while the 1M replays were under way (the 10M replays had finished) and its results were never analysed.
Nothing from it is reported, no configuration uses it, and its code and records are not in this repository.

More OpenRouter-route runs at 1M and 10M were queued instead (one more reference replay and one more OpenCrawl run at each size).

## OpenRouter route, final for 1M and 10M (2026-11-10 21:52)

Leaderboard prompt, answer call through OpenRouter (`openai/gpt-5.6-luna`, the reference harness's payload, 18 requests a minute), same judge as everywhere else, 0 failed questions:

| Split | OpenCrawl final4 (runs) | Reference evidence (runs) | Δ (95% CI) | P(Δ>0) | Reference published answers | Δ (95% CI) |
|---|---|---|---|---:|---:|---|
| 1M | 89.37 (89.5, 89.3, 89.4) | 88.11 (88.24, 87.98) | +1.27 (+0.10 to +2.52) | 0.984 | 89.83 | −0.46 (−1.58 to +0.73) |
| 10M | 82.36 (83.2, 81.9, 81.9) | 81.75 (82.06, 81.15, 82.05) | +0.61 (−1.19 to +2.67) | 0.729 | 84.48 | −2.12 (−4.53 to +0.30) |
| 1M + 10M | 87.82 | 86.69 | +1.12 (+0.14 to +2.17) | 0.986 | 88.64 | −0.83 (−1.85 to +0.25) |

For comparison, the direct OpenAI route: 1M 89.57 against 87.84 (+1.73), 10M 83.69 against 81.25 (+2.44). The reference evidence scores the same on both routes (88.11 / 87.84; 81.75 / 81.25); OpenCrawl is 0.2 lower at 1M and 1.3 lower at 10M on OpenRouter, the 10M difference being abstention (85, 85, 90 against 96.7 direct).

## Lead by ability; size of the conversations (2026-11-11)

**Lead by ability, all 2,000 questions, BEAM's own prompt.** final4 (3 runs per split) against the reference evidence (4 replays per split), paired bootstrap over the 200 questions of each ability (`verify.py --all`). Ten looks at the same data, so the borderline ones should be read with care.

| Ability | OpenCrawl | Reference evidence | Δ (95% CI) |
|---|---:|---:|---|
| knowledge update | 77.7 | 68.1 | +9.6 (+4.2 to +14.8) |
| summarization | 57.7 | 49.6 | +8.1 (+6.4 to +9.9) |
| instruction following | 62.3 | 57.0 | +5.3 (+1.1 to +9.5) |
| contradiction resolution | 36.4 | 32.7 | +3.7 (+1.1 to +6.4) |
| multi-session reasoning | 51.5 | 48.4 | +3.1 (+0.5 to +5.8) |
| event ordering | 53.6 | 51.6 | +1.9 (+0.3 to +3.6) |
| temporal reasoning | 52.5 | 51.8 | +0.8 (−3.1 to +4.5) |
| preference following | 80.3 | 80.0 | +0.3 (−2.3 to +2.9) |
| information extraction | 77.2 | 78.1 | −0.8 (−4.3 to +2.7) |
| abstention | 64.2 | 66.7 | −2.5 (−6.7 to +1.6) |

Six of the ten intervals clear zero; none of the four others is a significant deficit.

**Size of the conversations, measured from the dataset** (means per conversation): 100K 287 messages, 90k words, 172 days; 500K 1,087 messages, 336k words, 294 days; 1M 2,132 messages, 681k words, 226 days; 10M 20,870 messages, 6.76M words, 348 days. The evidence handed to the answer model at 10M is about 10.5k tokens, roughly one part in a thousand of the conversation.

## Other published BEAM numbers

Found by web search on 2026-11-11. All are self-reported, each under its own protocol, so none is comparable with ours or with each other.

*Corrected on 2026-11-14. As first written, this entry said that the protocols were mostly not stated, and of Hindsight and Mem0 that answer model, prompt and judge were not stated. They are stated, in the benchmark repositories behind the two posts, which we had not read. The two bullets and the closing paragraph now say what those repositories record; the scores are as first written.*

- Hindsight (Vectorize; [post of 2026-04-02](https://hindsight.vectorize.io/blog/2026/04/02/beam-sota)): 73.4 / 71.1 / 73.9 / 64.1 at 100K / 500K / 1M / 10M. The [Agent Memory Benchmark's repository](https://github.com/vectorize-io/agent-memory-benchmark) holds, for each question, the context, the answer and the score, and records Gemini 3.1 Pro (preview) as the answer model and Gemini 2.5 Flash-Lite as the judge. The results were added on 2026-04-01 together with the benchmark's BEAM adapter of that day, whose category-keyed answer prompt adds guidance from the dataset's annotations as the annotation-aided prompt here does. The benchmark has since replaced that prompt with a single one without that guidance and changed how it judges (its commit of 2026-06-23); the published results predate those changes. The post lists Honcho at 63.0 / 64.9 / 63.1 / 40.6.
- Mem0 ([post of April 2026](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)): 64.1 at 1M and 48.6 at 10M with one retrieval call and under 7,000 tokens per question. Its [benchmark repository](https://github.com/mem0ai/memory-benchmarks) holds the harness and, for each question, the answer and its scores: GPT-5 answers under Mem0's own answer prompt, GPT-5 judges, and a question's score is the mean over its rubric items.
- The reference system of this repository publishes about 90 under the annotation-aided prompt.

What follows: the controlled result here is a head-to-head with one system, not a ranking of the field. Our scores under BEAM's own prompt (62.1 at 1M, 52.6 at 10M, reader without reasoning) are below Hindsight's self-reported ones on their face; those were made, as far as its repository shows, under a prompt of the annotation-aided kind, by another answer model, and graded by another judge. Whether a difference between two such numbers reflects memory or protocol cannot be read off them. It takes putting their evidence, or their system, through the same answer call and judge.

## Audit run from the harness as prepared for publication (2026-11-12)

For publication the harness was moved to one results layout and cleared of machine-specific paths; apart from that the code was only reformatted, which was checked by comparing syntax trees before and after. To confirm that the code so prepared (still version 1 of the harness, with the loader, scorer and model client the earlier runs used; see the last entries of this log for version 2) still produced the system that was measured, the full system (final4) was run once more per length under each prompt from that code, with `--save-context`, which stores the exact answer prompt of every question. These runs were set apart from the reported numbers before they were made (`results/opencrawl/audit-run/`).

| | 100K | 500K | 1M | 10M | All |
|---|---:|---:|---:|---:|---:|
| BEAM's own prompt, audit run | 60.46 | 61.98 | 62.66 | 52.71 | 60.99 |
| the three reported runs | 63.3, 61.5, 62.6 | 62.1, 63.4, 61.7 | 62.0, 62.0, 62.4 | 53.0, 51.1, 53.6 | 61.34 |
| Annotation-aided prompt, audit run | 91.19 | 87.88 | 89.83 | 82.00 | 88.64 |
| the three reported runs | 90.3, 90.3, 90.2 | 88.0, 87.3, 88.0 | 89.9, 89.7, 89.2 | 83.9, 82.5, 84.6 | 88.49 |

Four of the eight fall outside the range of their three reported runs, two above (1M under BEAM's own prompt, 100K under the annotation-aided prompt) and two below (100K under BEAM's own prompt, 10M under the annotation-aided prompt). That is what exchangeable runs give: a fourth draw falls outside the range of three half the time.

Pooled in as a fourth run, against the reference evidence:

- BEAM's own prompt: All +2.85 (+1.81 to +3.91); 100K +2.09 (−0.33 to +4.49); 500K +1.80 (+0.01 to +3.58); 1M +3.40 (+1.74 to +5.11); 10M +6.14 (+1.97 to +10.31). The 100K interval now reaches zero, and 500K barely clears it: the leads at the two shorter lengths are marginal.
- Annotation-aided prompt: All +1.20 (+0.58 to +1.82); 1M +1.80 (+0.78 to +2.90); 10M +2.02 (+0.21 to +4.00); 100K +0.84 (−0.38 to +2.13) and 500K +0.57 (−0.49 to +1.64), ties as before. Against the published answers: −0.55 (−1.16 to +0.06).

The stored prompts were checked (`verify.py --all`): 4,000 prompts, 313,857 evidence items, every item with exactly rank, timestamp, role, turn and text, and none dated after the moment its question is asked. Under BEAM's own prompt every prompt is the benchmark's template around the evidence and the question, with nothing added.

Two corrections made while preparing the release:

- The base system's lead under BEAM's own prompt is +1.40 (+0.30 to +2.53) against the four reference replays. The +1.41 (+0.27 to +2.56) in the entry of 2026-11-10 08:20 was computed when only two replays existed.
- The remark that answer temperature 0 made no difference rested on runs against the contaminated memory pool (t27). It was removed from the paper's table of changes that did not help.

## A leak in two note-writing prompts, found in review; rebuild declared before it is run (2026-11-12 09:16)

An independent read of this repository before publication found that the example lines inside two prompts had been taken from benchmark conversations.

- **`facts.py`.** Its five example fact cards restated, with their values, what five test questions ask for: "Saturday budget review: now at 5 PM (moved; may clash with tutoring)" (10M `7_knowledge_update_0`), "SD card from TechMart: paid $10" (10M `6_information_extraction_1`), "Nancy's training: May 8, 2024" (1M `26_information_extraction_0`), "Vector database under evaluation: Milvus 2.3.1, for indexing over 1 million documents" (10M `1_information_extraction_1`) and "Jet skiing: preferred over parasailing" (10M `9_preference_following_0`). A sixth example, "How do I use my $15 recorder?", also came from a benchmark conversation; no question asks about it. They were copied from the failure cases studied on 2026-11-10 ("Where the remaining losses are").
- **`conflicts.py`.** The example in the prompt that restates a conflict, "reported attending a production meeting about the invention" / "says they have never attended one", was the conflict of 100K `20_contradiction_resolution_0`.

The note-writing passes never received a question or a reference answer as input, but their instructions carried the answers to these six questions. Every result that involves fact cards or conflict notes was produced with these prompts: final3, final4, the paired replays, the audit run. The statement that the passes see no reference answer was therefore wrong for these six questions, and the three 10M questions cited in the paper as fixed by fact cards "in every run" were among them.

What is done about it, written down before any of it is run:

1. The examples are replaced with invented ones that match no question and no reference answer (checked against all 2,000 questions and their reference answers). Nothing else in the prompts changes.
2. The fact cards are rebuilt from the new prompt, and the conflict notes are mined again from the new cards. The per-turn notes are untouched: their prompt contains no example.
3. The full system is run again on the rebuilt memory: three answer runs per length under each prompt, tag `final5`, run `a` storing its prompts. The reference evidence is replayed twice more per length under each prompt on the same day, with every answer and verdict stored.
4. `final5` replaces `final4` as the reported system, whatever it scores. The reference side of the reported comparison pools every replay of the unmodified reference evidence, the earlier ones and the new ones; a comparison with the same-day replays alone is reported next to it. `final4` stays in the repository as what was measured before, together with its comparison recomputed without the six questions.

## The rebuilt system (final5) and what else the review changed (2026-11-12)

**Rebuild.** As declared above. Fact cards: 155,572 passages (154,892 before). Conflicting pairs: 2,895 (2,783 before), written as 1,355 conflict notes (1,327 before). The per-turn notes were not touched, and an export of them after the rebuild is identical to the published one. The new passages were encoded in the cluster and on the host CPU. The driver script stopped once on a shell error after the cards had been encoded and was resumed at the conflict-note stage; nothing was rerun.

**Reference evidence, replayed again today** (two answer runs per length, every answer and verdict stored): BEAM's own prompt 60.38 / 60.33 / 59.20 / 48.14 at 100K / 500K / 1M / 10M (58.72 over all questions; 58.40 on 2026-11-10); annotation-aided prompt 89.29 / 87.93 / 87.59 / 82.78 (87.57; 87.33 on 2026-11-10). The first version of the replay script stored the verdicts in a field the unchanged summary code could not read, so the summary step failed after every answer and verdict had been written; the field was renamed and the summaries were written from the records.

**final5 under BEAM's own prompt**, three runs per length, 0 failed questions:

| Split | final5 | Runs | Reference evidence, all replays | Δ (95% CI over questions) | CI over conversations | final4 as first measured |
|---|---:|---|---:|---|---|---|
| 100K | 63.05 | 62.3, 63.3, 63.5 | 60.05 | +3.00 (+0.62 to +5.40) | +0.60 to +5.48 | +2.60 (+0.15 to +5.07) |
| 500K | 61.59 | 61.0, 62.0, 61.7 | 60.44 | +1.15 (−0.59 to +2.90) | −0.31 to +2.62 | +1.91 (+0.12 to +3.73) |
| 1M | 62.33 | 62.0, 62.4, 62.6 | 58.98 | +3.36 (+1.68 to +5.05) | +1.52 to +5.24 | +3.27 (+1.58 to +5.00) |
| 10M | 51.88 | 53.8, 51.2, 50.6 | 47.02 | +4.86 (+0.68 to +9.10) | +0.47 to +9.59 | +6.11 (+1.92 to +10.33) |
| All | 61.17 |  | 58.51 | +2.66 (+1.62 to +3.72) | +1.58 to +3.78 | +2.94 (+1.87 to +4.03) |

**final5 under the annotation-aided prompt**, three runs per length, 0 failed questions:

| Split | final5 | Runs | Reference evidence, all replays | Δ (95% CI over questions) | CI over conversations | final4 as first measured | Published answers | Δ |
|---|---:|---|---:|---|---|---|---:|---|
| 100K | 90.17 | 89.7, 90.8, 90.0 | 89.51 | +0.66 (−0.64 to +1.96) | −0.54 to +1.92 | +0.61 (−0.67 to +1.92) | 90.82 | −0.65 (−1.89 to +0.55) |
| 500K | 87.89 | 88.0, 87.5, 88.2 | 87.51 | +0.38 (−0.67 to +1.44) | −0.58 to +1.28 | +0.54 (−0.57 to +1.63) | 88.64 | −0.75 (−1.90 to +0.37) |
| 1M | 89.46 | 89.0, 89.4, 89.9 | 87.75 | +1.70 (+0.66 to +2.80) | +0.71 to +2.73 | +1.73 (+0.69 to +2.87) | 89.83 | −0.38 (−1.43 to +0.73) |
| 10M | 81.44 | 80.8, 81.9, 81.6 | 81.69 | −0.25 (−1.99 to +1.54) | −1.67 to +1.45 | +2.44 (+0.62 to +4.52) | 84.48 | −3.04 (−5.36 to −0.83) |
| All | 88.25 |  | 87.41 | +0.84 (+0.24 to +1.44) | +0.26 to +1.43 | +1.16 (+0.52 to +1.80) | 89.08 | −0.83 (−1.46 to −0.21) |

- Against the replays of the same day alone: +2.45 (+1.31 to +3.58) under BEAM's own prompt, +0.68 (+0.03 to +1.34) under the annotation-aided prompt.
- final5 against final4, question by question: −0.17 (−0.80 to +0.48) under BEAM's own prompt, −0.24 (−0.62 to +0.14) under the annotation-aided prompt.
- Without the knowledge-update questions: +1.98 (+0.97 to +2.98) and +0.48 (−0.13 to +1.08).

**The six questions of the leak**, mean score over three runs, before the rebuild (final4) and after (final5):

| Question | Own prompt, before | after | Annotation-aided, before | after |
|---|---:|---:|---:|---:|
| 100k 20_contradiction_resolution_0 | 45.8 | 66.7 | 83.3 | 66.7 |
| 10m 1_information_extraction_1 | 0.0 | 0.0 | 0.0 | 0.0 |
| 10m 6_information_extraction_1 | 100.0 | 100.0 | 100.0 | 100.0 |
| 10m 7_knowledge_update_0 | 0.0 | 0.0 | 100.0 | 100.0 |
| 10m 9_preference_following_0 | 25.0 | 41.7 | 100.0 | 83.3 |
| 1m 26_information_extraction_0 | 100.0 | 100.0 | 50.0 | 50.0 |

**Reading.** The six questions did not move, so the leak did not produce the earlier scores on them: the rebuilt cards state the same facts, because the facts are in the user's messages. Over all questions the rebuilt system is within noise of the earlier one.

The exception is 10M under the annotation-aided prompt: 81.44 against 83.69 (−2.25, −3.62 to −1.06), spread over abstention (96.7 → 90.8), multi-session reasoning (29.0 → 24.2), extraction (70.4 → 67.5), instruction and preference following (−2.5 each) and summarization (96.9 → 94.4). The audit run, made on the earlier notes two days after the three final4 runs and on the same day as final5, scored 82.00 at 10M, with abstention at 90.0 and summarization at 94.2. So the drop cannot be pinned on the notes. One run does not settle whether the answer model behaved differently that day or the three final4 runs at 10M were high. The reference evidence moved the other way at 10M between the two days (81.25 → 82.78 under this prompt, 46.46 → 48.14 under BEAM's own).

Consequences. The lead at 10M under the annotation-aided prompt that final4 showed (+2.44) is not supported: with all runs it is −0.25 (−1.99 to +1.54). Under BEAM's own prompt the 500K lead no longer clears zero (+1.15, −0.59 to +2.90), while 100K now does. Against the published answers the rebuilt system is 0.83 behind, with an interval that excludes zero (−1.46 to −0.21).

**Other points of the review**, and what was done:

- *Questions are not independent.* The twenty questions of a conversation share its index and notes, so intervals that resample questions are too narrow. Every comparison now carries a second interval that resamples conversations.
- *The timing of knowledge-update questions is a hint.* They are asked as of the turn BEAM marks as the update (the reference harness's protocol). In the final4 runs that turn was in OpenCrawl's evidence, and was its newest transcript item, for 182 of the 200 such questions. The comparison is now also reported without those questions.
- *BEAM's cited turns were used during development*, to measure search recall (stemming, the sparse weight, the user-only pass), not only for the coverage diagnostic. The paper said otherwise and was corrected.
- *"All records are published" was not true.* 18 invalid runs had been left out; they are now in `results/opencrawl/excluded/`. The records of the withdrawn relevance-model test remain an exception, and so do the partial records of t28, which was stopped and discarded on 2026-11-10 (see above).
- *The verification script did not cover what the README said it covered.* It now re-derives scores from the stored verdicts where verdicts were stored, reads the README's table from the file, covers Tables 6 and 7 and Appendix C of the paper, and states what it does not cover.
- *Two prompts of experiments that were not adopted* (the fact ledger and the timeline variant) also quote benchmark content as examples. They are left as they were run and marked in the code.

## A second independent read, and a more cautious interval (2026-11-12, evening)

A second cold read of the committed tree confirmed the numbers of the result table, the leak disclosure (the new examples match none of the 2,000 questions, answers or rubric items; the old ones match exactly the six named) and the declaration (unchanged since its 09:16 commit; the final5 runs finished between 11:40 and 13:04). It found one false statement and several that were firmer than the data.

- *"Re-derives every score" was false.* Verdicts were stored only by the runs and by the replays of 2026-11-12. `verify.py` now counts: 257,584 scores are stored, 121,158 have a verdict beside them and are re-derived from it; in the reported comparison that is 12,000 of 12,000 OpenCrawl scores, 8,000 of 23,100 reference-evidence scores and none of the 6,000 published-answer scores. The documents say so.
- *The leads at 100K and 10M were stated more firmly than they hold.* With ten conversations at 10M a percentile bootstrap over conversations runs narrow. Every comparison now also carries a Student t interval over the per-conversation mean differences, and the README quotes that interval. A lead is called clear only when the t interval and both bootstrap intervals exclude zero.

| BEAM's own prompt, all replays pooled | Lead | Bootstrap over questions | t over conversations |
|---|---:|---|---|
| 100K | +3.00 | +0.62 to +5.40 | +0.36 to +5.64 |
| 500K | +1.15 | −0.59 to +2.90 | −0.41 to +2.71 |
| 1M | +3.36 | +1.68 to +5.05 | +1.38 to +5.33 |
| 10M | +4.86 | +0.68 to +9.10 | −0.72 to +10.44 |
| All | +2.66 | +1.62 to +3.72 | +1.55 to +3.78 |
| Annotation-aided prompt, all | +0.84 | +0.24 to +1.44 | +0.25 to +1.43 |
| …1M | +1.70 | +0.66 to +2.80 | +0.63 to +2.78 |
| Against the published answers, all | −0.83 | −1.46 to −0.21 | −1.49 to −0.16 |

  So the 10M lead under BEAM's own prompt (+4.86) is not clear. Across the four set-ups of the reference side (all replays pooled, same-day replays alone, evidence in time order, evidence in OpenCrawl's format) the overall lead and the lead at 1M are clear every time under both prompts; under BEAM's own prompt 100K is clear in one and 10M in one of the four.
- *Two docstrings still quoted benchmark conversations* (`facts.py`, `conflicts.py`), one of them the subject of a seventh question, 100K `2_contradiction_resolution_0`. Neither text reached a model. Both are replaced with invented illustrations.
- *Tone and precision.* "Its answers cannot be regenerated" became "we could not regenerate its answers", with the sentence that no error on the reference system's side is claimed. "Every replay is pooled" became "every replay made with the same answer call". The conclusion now states the one benchmark-specific input the system takes when it runs, the timing of knowledge-update questions. A figure typed by hand in the previous entry was corrected (58.72, not 58.73), and the statement that the 10M drop "goes with the day" was withdrawn: it rested on one run.

- *The core pull request.* While checking links we found that pull request #137 of opencrawl-core, which this log calls a draft throughout, had been closed without merging on 2026-11-11, when that repository's history was rewritten, and that its main branch has since gained its own time bounds, role filter and neighbour links (but no stemming and no semantic retrieval). The evaluated code is the branch `search-relevance-stemming` at commit `95863d8`, the same tree as the `97ed5b0` the runs were made at. The README, the reproduction guide and the paper now say so.

Noted and left as they are: the invented examples share generic values with unrelated reference answers ("$40", "September 12"); the format example in the note-taker's prompt uses the date 2024-03-15, on which 37 conversations begin, and carries no content. Changing either would mean another rebuild of the notes.

## The reference system is no longer named; third-party harness modules replaced (2026-11-12, night)

Two changes to the repository before publication. Neither touches a run or a reported number.

**The name.** The repository no longer names the system it compares with, links to its repository, or quotes the
scores it reports for itself. This log was edited accordingly (see the note at its top), and the repository is
published as one snapshot, without the commits that came before. The consequence for a reader is spelled out in
[the note on the reference system](reference-system.md): its published records are not here, so the reference side
can be recomputed from the per-question scores in `results/reference/` but not generated again from this repository
alone; and the commits this log cites for plans written before their results belong to a history that is not
published, so their timing rests on our word.

**The harness.** Every run in `results/` was made with a harness that took its dataset loader, its scorer, its
logging and, in modified form, its model client and the frame of its run script from the reference system's
open-source BEAM harness. Those modules are not redistributed. `dataset.py`, `scoring.py`, `llm.py`, `log.py`,
`records.py` and the corresponding parts of `run.py` were written again, and `exabase_prompts.py` is now written by
`make_exabase_prompts.py` directly from the published adapter. The summary of a run made with this version says `harnessVersion: opencrawl-2`; the
published runs say `opencrawl-1`.

What was compared between the modules the runs used and their replacements, with no difference found:

| | Compared | Cases |
|---|---|---:|
| Loader | Every turn (id, session, position, role, timestamp, BEAM's turn id, text) and every question (id, ability, text, reference answers, annotations, moment asked) of all 100 conversations | 327,116 turns, 2,000 questions |
| Prompts | The answer prompt of every question on three contexts (6,000), the judge prompt for every rubric item on three answers (18,138), the item-matching prompt for every ordering topic (1,534), and three prompts for abilities the dataset does not have | 25,675 prompts |
| Scorer | Score and stored verdict for seven answers to every question, with a stand-in judge whose replies depend only on the prompt and which fails on some calls | 14,000 scorings, 46,079 judge calls |
| | List parsing on every stored answer; order agreement on every stored event-ordering verdict and four rearrangements of it, and on all orders of up to three items; run summaries of every stored run | 145,958 / 60,580 / 13,260 / 315 |
| Model client | Request bodies byte for byte, headers, retries and waits, results and errors, usage totals, on scripted replies (success, rate limit, server error, refusals of the account, replies that are not JSON, empty and wrapped replies, dropped connections) under four settings (default, Responses API, API router, temperature and reasoning set) | 113 calls per setting |

The comparison scripts need the replaced modules and are not in this repository. What a reader can run is
`harness/check_harness.py`: it recomputes the scores of the stored verdicts with `scoring.py` (then 121,158 of them), compares the loader with
fingerprints of every conversation as the runs ingested it (made with the replaced loader) and with the questions,
reference answers, moments and 8,000 answer prompts the runs stored, and compares the prompts with ExaBase's
published file.

Two live checks with the new version came first. One 100K conversation was run end to end under each prompt; its
records and summary have the same fields as the published runs, and the prompt text around the evidence is
identical for all 20 questions (superseded by the full run of the next entry; not kept). And the reference evidence
of 100K was answered and judged once under each prompt: 59.03 under BEAM's own prompt and 89.40 under the
annotation-aided one (`replay-100k-raw_harness2_paper` and `replay-100k-raw_harness2` in
`results/reference/evidence-replays/`). The six and five stored single runs range from 59.09 to 61.55 and from 88.91
to 89.83, so the first is just below the lowest of them. Question by question it differs from the stored replay of
the same day by −1.35 (95% interval over questions −3.02 to +0.32), and the two answer runs of that stored replay
differ from each other by 2.34: within what one answer run varies. These two replays are not pooled into the
reference side and are not part of any reported number; the next entry says what pooling them would change.

## A third independent read before publication: an ordering flaw, and a full run of the published harness (2026-11-12, night)

Before this snapshot was pushed anywhere, a fresh reviewer read it cold, with instructions to distrust it.
It recomputed the README's result table with its own code and found no error in a reported number. It found a flaw
in the harness that predates every run, the absence of any full run of the published harness, and a list of
statements that had become false or were imprecise. The two measurements below were declared, with their rules,
at 20:44 UTC, before either was run: neither changes the reported comparison whatever it shows.

**The order of evidence.** `run.py` sorts the evidence it shows by timestamp and compares the timestamps as text.
A timestamp on a whole second is written without a fraction ("…T12:00:00Z" next to "…T12:00:00.008000Z") and, as
text, sorts after every other timestamp of its second. Turns are spaced a millisecond apart, so this misplaces the
first message of a conversation and turns 1000, 2000 and so on, and the notes dated at them. In the stored prompts
of the reported system (run `a` at each length under each prompt) the evidence is out of the order of its moments in
867 of 4,000; in 698 of the 704 prompts that hold a conversation's first message, that message is shown
after a later one. The harness has done this since the first run, in both versions.

To learn what it cost, every affected prompt was answered again twice as stored and twice with the same evidence
sorted by moment, same answer call and judge (`harness/reorder_replay.py`; records in
`results/opencrawl/paired-replays/order-*`):

| Sorted by moment, against the order as run | Prompts out of order | Mean difference over those questions (95% bootstrap interval) | Mean of the per-conversation differences (95% t interval) |
|---|---:|---|---|
| BEAM's own prompt | 436 of 2,000 | +0.06 (−1.28 to +1.42) | +0.24 (−1.25 to +1.73) |
| Annotation-aided prompt | 431 of 2,000 | +0.12 (−0.69 to +1.02) | −0.31 (−1.15 to +0.53) |

The two columns weigh the same differences differently: conversations hold between one and fifteen affected
questions, and the second column gives each conversation one vote. No interval excludes zero: on this evidence the flaw did not move the reported scores by an amount we can measure. Spread over all 2,000 questions the first column is +0.01 and +0.03. Two limits of this replay: only the
one run per length that stores its prompts could be replayed, and the replay keeps scores and answers but not the
judge's verdicts (its logs show one transient server error, retried, and no failed call). The published harness
keeps the order the runs used, so that it remains their code; a corrected order would be a new version with runs of
its own.

The same kind of flaw is in two of the four set-ups of the reference side, the re-presentations of its evidence
"in time order" and "in OpenCrawl's format and time order" (`replay_reference.py` variants `time` and
`ourfmt-time`): its timestamps drop trailing zeros, and sorted as text they differ from the order of the moments in
1,258 of the 2,000 questions (272, 476, 444 and 66 by length). Those set-ups were not rerun. They are two of the
four behind the README's "what holds under every check", and one of them gives the only clear lead at 10M. The
reported table uses the reference evidence in the order its harness passes it and is not affected on that side.

**A full run of the published harness.** Until now version 2 had been compared with the replaced modules piece by
piece and run on one conversation. One run of the reported system per length under each prompt was made with it
(`results/opencrawl/published-harness-run/`, tag `harness2`, prompts stored). The rule written beforehand: the
published harness is taken to reproduce the reported system if, under each prompt over all 2,000 questions, the
difference between this run and the mean of the three reported runs has a 95% t interval over conversations that
includes zero.

| Run of the published harness | 100K | 500K | 1M | 10M | All | Against the three reported runs, all questions |
|---|---:|---:|---:|---:|---:|---|
| BEAM's own prompt | 62.93 (−0.12) | 60.75 (−0.84) | 61.41 (−0.92) | 51.99 (+0.11) | 60.54 | 60.54 against 61.17: −0.63 (−1.52 to +0.26) |
| Annotation-aided prompt | 90.17 (−0.00) | 87.65 (−0.24) | 89.35 (−0.10) | 81.92 (+0.48) | 88.18 | 88.18 against 88.25: −0.07 (−0.61 to +0.46) |

(In brackets by length: the difference from the mean of the three reported runs.) Both intervals include zero, so the rule is met. What that supports is that no difference was detected, not that there is none: one run against three resolves about a point.

What a skeptic would add, and what speaks against a defect in the harness. Under BEAM's own prompt this run is
below each of the three reported runs (60.91, 61.33, 61.27), and the replay of the reference evidence made with
version 2 earlier that evening was the lowest of its seven single runs (59.03, previous entry). But the stored
prompts of a reported run, answered again that evening for the order replay, also scored lower than their first
answers under that prompt, −0.57 (−2.31 to +1.14; annotation-aided +0.10, −1.02 to +1.21), with byte-identical
prompts; under the annotation-aided prompt the run sits inside the three reported ones (87.96, 88.28, 88.51); and
with version 2 on both sides at 100K, its run against its replay, the lead is +3.90 (+0.40 to +7.40) and +0.76
(−0.72 to +2.25), against +3.00 and +0.66 as reported. So three things answered that evening under BEAM's own
prompt came out a little low, on both sides and none of them clearly; nothing here separates the harness from the day. The two version 2 replays of 100K are
not pooled into the reference side: with them the reported 100K leads would be +3.15 and +0.68.

**Statements corrected.**

- *"Made from the published code."* The audit run of 2026-11-12 was made from the harness as first prepared for
  publication, which was still version 1. The paper, `results/README.md`, `verify.py` and the entry above now say
  so.
- *"Conversation order."* The documents said OpenCrawl's evidence is shown in conversation order. It is shown in
  the order of its timestamps as written, with the flaw above; they now say "time order" and point to the limits.
- *The timing of knowledge-update questions.* For 10 of the 200 the dataset cites no turn that can be found, and
  they are asked at the end of the conversation like every other question. BEAM's turn ids also repeat inside four
  1M conversations (5, 26, 33, 34), where the latest turn with a cited id is taken, and in four 10M conversations
  (1, 3, 4, 5) BEAM dates a batch of turns before the batch that precedes it, so that their timestamps do not
  follow conversation order. All of this is in the loader the runs used and applies to both systems;
  `harness/dataset.py` now states it.
- *Judge calls per question* are 3.0 on average under the annotation-aided prompt and 5.3 under BEAM's own, not
  "five to six". Rubric questions take 2.5 calls under either prompt; the difference comes from event ordering,
  where each item of an answer is compared with the reference topics one at a time until one matches, and answers
  written without the list of topics need more comparisons.
- *Records left out.* Besides the withdrawn relevance-model test, the partial records of `t28` were discarded on
  2026-11-10; the documents now name both.
- *Table 5 of the paper* marked two leads in bold whose intervals over conversations include zero; the emphasis is
  removed and the text says the leads are not clear.
- *By ability*, the README and the paper printed event ordering as 55.2 where the appendix table prints 55.3 (the
  value is 55.25): they rounded a value that had already been rounded. Both now print two decimals. On information
  extraction OpenCrawl is behind by 3.39 and two of the three intervals exclude zero; the README and the paper now
  say so instead of only "not clearly behind".
- *The adapter's authorship.* The page the prompts come from names no organisation and states no licence; the
  attribution to ExaBase is the one the reference system's harness gives, and `NOTICE.md` now says that.
- *`check_harness.py`* said it re-scored 121,158 verdicts with `scoring.py`. For the 109,042 rubric verdicts among
  them it had averaged the stored item scores itself; it now calls `scoring.rubric_mean`, compares whole run
  summaries, and says that the judge's stored numbers are all exactly 0, 0.5 or 1, so the rounding rule is checked
  on fixed values. With the records added in this entry it covers 113,362 rubric verdicts, 12,596 event-ordering
  verdicts, 325 run summaries, 171,290 stored records and 12,000 stored answer prompts.
- *The figure's description* said every interval under BEAM's own prompt lies above zero; it is now computed from
  the plotted intervals.
- `verify.py` now also recomputes the paired fact-card row of the paper's Table 7, which it had not covered.

A second reviewer then read these changes. It reproduced both measurements with its own code and found no blocker.
From its list: the t intervals of the order replay had been quoted next to means they are not centred on (the table
above now gives both statistics); "every replay is pooled" needed the exception of the two version 2 replays;
"reproduces" claimed more than one run shows (the paragraph above); 18 run directories, not eight, come from version
2; and the 10M lead that is clear in one set-up contradicted "no lead there is clear" in the limits.

Not done: the two time-ordered set-ups of the reference side were not rerun with the order corrected, and the
replay above measures the flaw on stored prompts, not in fresh runs of a corrected harness.

## Corrections on the day of publication (2026-11-14)

Corrections of what the repository says, made after the last review and before publication. None touches a run or a reported number; `verify.py` and the harness are unchanged.

- *Other vendors' protocols.* The README, the note on the reference system, the paper and this log said that other vendors' BEAM protocols were not stated, or not fully. For two of them that was wrong: we had read their posts and not the benchmark repositories behind them. Hindsight's results are in the Agent Memory Benchmark's repository with, for each question, the context, the answer and the score (Gemini 3.1 Pro answering under the category-keyed BEAM prompt that benchmark had at the time, since replaced; Gemini 2.5 Flash-Lite judging). Mem0's are in its benchmark repository with per-question answers and scores (GPT-5 answering under Mem0's own prompt, GPT-5 judging, a question's score being the mean over its rubric items). The documents now say what the two protocols we have read are, instead of calling them unstated, and make no statement about the protocols we have not read. The entry "Other published BEAM numbers" above is corrected in place, with a note.
- *A claim of the paper that was too strong.* Its related-work section called the reference system "the one system whose published records make such a comparison possible". Hindsight publishes the context of every question too. The sentence now says only that the comparison is with one system that publishes the evidence its answer model read, and the note on the reference system says that it is not the only one.
- *Where the adapter's prompts come from.* The adapter file whose prompts we reproduce matches the BEAM adapter of the Agent Memory Benchmark, as added to that repository on 2026-04-01, in 24 of its 25 function definitions, the code that holds both judge prompts included; the answer-prompt method differs in 29 lines, and the page it is published on was created on 2026-07-12. `NOTICE.md` and the README's credits now say so, and four places that called the adapter ExaBase's outright no longer do. Neither source states a licence.
- *Wording.* "Published as one snapshot" became "published without its development history; its first commit is a snapshot made on 2026-11-12", because this entry is a second commit. The README mentions the closed pull request of opencrawl-core without linking it; the branch it proposed is linked as before. `CITATION.cff` carries the date of this entry.

**Work after the reported runs, not in this repository.** On 2026-11-13, after the reported system and its numbers were final, the evidence of the reported system was answered and judged under other vendors' published protocols, one vendor's published contexts were replayed under our answer call and judge, and a variant with an always-loaded profile memory (`harness/profile_memory.py`, the experiment recorded as t15 and t26 above) was run again and not adopted: under our two prompts it made no difference we could measure, which agrees with the line on it in Table 8 of the paper. The records of those runs are not included, nothing reported here rests on them, and no claim is made from them here.

One thing that rerun showed about the published harness: `run.py --profile` reads the passages of the profile file that a single search returns, which with the present index can be only part of the file (the rerun read each file whole, by following the links between its passages). The flag belongs to an experiment that was not adopted and no reported run uses it; whoever reuses it should read the file whole.
