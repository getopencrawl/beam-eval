# Results

Per-question records of every run behind a number in the [README](../README.md) or the [paper](../paper/opencrawl-beam.md):
358 runs, about 270 MB compressed. [`verify.py`](../verify.py) recomputes the reported numbers from these
files and compares them with [`expected.json`](expected.json).

## Layout

| Folder | Runs | What it holds |
|---|---:|---|
| `opencrawl/full-system/` | 24 | The reported system (`final5`): the full system on fact cards and conflict notes rebuilt from the corrected prompts. Three answer runs per conversation length under each prompt; run `a` stores the exact prompt of every question (`answerPrompt`). |
| `opencrawl/full-system-original-notes/` | 24 | The same system as first measured (`final4`), on notes written from prompts that carried six benchmark answers as examples. |
| `opencrawl/audit-run/` | 8 | One more run of `final4` per length and prompt, made on 2026-11-12 before the leak was found, from the harness as first prepared for publication (version 1), storing every prompt. |
| `opencrawl/published-harness-run/` | 8 | One run of the reported system per length and prompt made with the harness as published (version 2), storing every prompt. Set against the three reported runs; not part of any reported number. |
| `opencrawl/base-fact-cards/` | 24 | The system before conflict notes (`final3`), on the original fact cards. |
| `opencrawl/base/` | 20 | The system before fact cards (`final2`). Two runs per length under BEAM's own prompt, three under the annotation-aided prompt. The 10M runs under the latter are lettered c, d and e: a and b were the two runs made before the configuration was fixed, which are `development/10m-search-exabase-t34-user1-time-a` and `-b`. |
| `opencrawl/openrouter-route/` | 6 | `final4` at 1M and 10M with the answer call sent through OpenRouter. |
| `opencrawl/baselines/` | 16 | Stock BM25 search, the no-memory controls, and a tool-using agent, from before any change. |
| `opencrawl/development/` | 95 | Single runs made while the system was built: the ablations and the changes that were tested and not adopted. |
| `opencrawl/paired-replays/` | 33 | Paired tests on identical retrieval: one retrieval per question, answered under several variants (`pv-*`, on the original notes), and the replay for the order of evidence on the stored prompts of the reported system (`order-*`). |
| `opencrawl/rejudged/` | 17 | Earlier OpenCrawl answer sets graded again by the same judge (three passes), to measure judge variance. |
| `opencrawl/excluded/` | 18 | Runs that are invalid and enter no reported number: 16 development runs (tags `t26` to `t31`) ran against a memory pool that still contained files from an abandoned experiment, and two 1M runs (`t32`) lost 73 and 49 questions to search timeouts. Kept so that the exclusion can be checked. |
| `reference/evidence-replays/` | 57 | The reference system's published evidence, answered by this harness's answer call and judged by its judge. |
| `reference/published-answers/` | 8 | The reference system's published answers, graded by this harness's judge (three passes; one pass in `-first-pass`). |
| `reference/context-tokens.json` | | Size of the context string the reference system's answer model read, per length. OpenCrawl's context is capped at the mean. |
| `diagnostics/` | | Coverage of BEAM's cited evidence turns: `cited-turn-coverage-*` for the base system's evidence, `bm25-retrieval-recall-*` for the baseline's search results. |
| `tables/` | | The comparison tables as the harness scripts print them, with the interval used while the system was developed (bootstrap over questions). `verify.py` adds the two intervals over conversations. |
| `expected.json` | | The numbers quoted in the README, the paper and the log, as `verify.py` wrote them. |
| `local/` | | Where the harness writes new runs. Ignored by git. |

## A run

Each run is a directory with `results.jsonl.gz` (one JSON record per question), `summary.json` (scores by ability, the
full configuration, model names, dataset revision, token usage, wall-clock time) and, for OpenCrawl runs, `usage.json`.

A record of an OpenCrawl run:

| Field | Meaning |
|---|---|
| `questionId`, `conversationId`, `category` | BEAM's identifiers and the ability the question tests. Question ids repeat across lengths. |
| `question`, `goldAnswers` | The question and BEAM's reference answer. |
| `asOf` | The moment the question is asked. Retrieval sees nothing later. |
| `retrieval.queries` | Every search query issued: the question, the rewrites, the follow-ups. |
| `retrieval.turns` | The turn number of each evidence item, in the order shown to the answer model; `null` marks a memory note. |
| `retrieval.results`, `evidenceTokens`, `contextTokens` | Number of evidence items, and the size of the evidence and of the whole context string in `o200k_base` tokens. |
| `answer` | The answer model's reply. |
| `judge` | For rubric questions (`method: rubric`), every rubric item with the judge's score (0, 0.5 or 1) and its stated reason. For event ordering, the reference sequence and the sequence found in the answer, from which Kendall's tau-b is computed. `verify.py` re-derives every score from this field. |
| `score` | The question's score: the mean over rubric items, or the mapped tau-b. |
| `answerPrompt` | Only in runs made with `--save-context`: the complete prompt the answer model received. |
| `error` | Present when a question failed and was scored 0. No reported run has one. |

A record of a replay of the reference evidence carries `scores`, one per answer run made in that directory, their mean
as `score`, and the last `answer`. The replays made on 2026-11-12 (`_1112`) also carry every answer (`answers`) and
every verdict (`verdicts`); the earlier ones do not. A record of a paired replay carries one entry per variant under
`variants`, with `changed` (whether the variant altered that question's context) and, if it did, three `scores` and
`answers` (two in the `order-*` replays, whose variants are `as-run` and `by-moment`).

## Run names

`<length>-<retrieval>-<prompt>-<tag>`

- `<length>`: `100k`, `500k`, `1m`, `10m` (400, 700, 700 and 200 questions).
- `<retrieval>`: `search` (the harness retrieves, one answer call), `none` (empty evidence), `agent` (the model drives
  `search` and `fetch` itself and answers freely), `agentrecall` (the model investigates, then the fixed answer prompt).
- `<prompt>`: `paper` is BEAM's own answer prompt; `exabase` is the annotation-aided prompt, named after the adapter
  it comes from.
- `<tag>`: `final2` to `final5` are the configurations that were fixed before their runs; the letter after them is
  the run. `final5` is `final4` on rebuilt notes; `final4or` is `final4` through OpenRouter; `audit` is the audit run
  of `final4`; `harness2` is the run of `final5` made with the published harness. `t1` to `t39` are development runs, described in [the experiment log](../docs/experiment-log.md) under
  the same tags. No tag means the untouched baseline.

`replay-<length>-<variant><suffix>` is the reference evidence answered by this harness.

Version 2 of the harness, the one published, made 18 of the run directories: the eight runs and the two replays
tagged `harness2`, and the eight `order-*` paired replays. Version 1 made all the others.

- Variants: `raw` (exactly as published), `time` (sorted by time), `ourfmt` and `ourfmt-time` (rewritten into
  OpenCrawl's item format), `sources` (whole source messages only), `artifacts` (typed extractions only),
  `trunc800` (source messages cut to 800 characters), `noexcerpts` (extractions without their excerpts).
- Suffixes: none, `_more` and `_x3` are the annotation-aided prompt on 2026-11-10 (one to three answer runs);
  `_paper` and `_paper2` are BEAM's own prompt on 2026-11-10 (two runs each); `_1112` and `_paper_1112` are the two
  prompts again on 2026-11-12 (two runs each); `_rlow` and `_rmed` set the answer model's reasoning to low and
  medium; `_resp` uses the provider's Responses API; `_or` and `_or2` send the answer call through OpenRouter.
  `_harness2` and `_harness2_paper` are one answer run each at 100K under the two prompts, made with the published
  harness on 2026-11-12 and not pooled into the reference side.

`pv-<length>-pv<N><p|x>` is a paired replay; `p` and `x` mark BEAM's own and the annotation-aided prompt.

| Paired replay | Base evidence | Variants |
|---|---|---|
| `pv1` (10M) | base + fact cards | dropping or qualifying absence clauses in notes; best-ranked items first; notes first |
| `pv2` (10M), `pv4` (1M) | the same retrieval without fact cards | fact cards sharing the notes budget, or as their own layer |
| `pv3` (100K, 500K) | base | a legend describing the entries; role labels spelled out |
| `pv5` (500K, 1M) | base | evidence restricted to the user's words when the question is about the user |
| `pv6p` | base + fact cards | conflict notes, first form (1M stopped at 452 questions) |
| `pv7p`, `pv7x` | base + fact cards | conflict notes, final form: the test the adoption rule was written for |
| `pv8p` (100K; 500K stopped at 158 questions) | `final4` | a timeline layer of fact cards |
| `pv9p`, `pv9x` (1M, 10M) | `final4` | dropping absence clauses from notes |

## Which runs back which table of the paper

| Paper | Runs |
|---|---|
| Table 2, baselines | `opencrawl/baselines/` |
| Table 2, the configurations | `opencrawl/base/`, `base-fact-cards/`, `full-system-original-notes/`, `full-system/` |
| Table 3 (BEAM's own prompt) | `full-system/*-paper-final5-*` against `replay-*-raw_paper`, `raw_paper2` and `raw_paper_1112`; re-presented: `time_paper`, `ourfmt-time_paper` |
| Table 4 (annotation-aided prompt) | `full-system/*-exabase-final5-*` against `replay-{100k,500k}-raw_x3`, `replay-1m-raw` and `raw_x3`, `replay-10m-raw` and `raw_more`, and `replay-*-raw_1112`; published answers: `reference/published-answers/published-answers-*` |
| The system before the rebuild | `full-system-original-notes/` and `audit-run/` against the replays of 2026-11-10 |
| Table 5 (API router) | `openrouter-route/` against `replay-*-raw_or` and `raw_or2`; other checks: `replay-10m-raw_rlow`, `raw_rmed`, `raw_resp` |
| Table 6 (ablation) | `baselines/`, then `development/` tags `t1`, `t2`, `t3-stem`, `t4-follow`, `t5-pit`, `t9-semantic`, `t10-mem`, `t13-notes2` |
| Role-aware recall at 10M | `development/10m-*-t32-*`, `t34-*`, and `base/10m-*` |
| Table 7 | fresh runs: `base/`, `base-fact-cards/`, `full-system-original-notes/`; paired: `pv4`, `pv2`, `pv6p`, `pv7p`, `pv7x` |
| Table 8 (not adopted) | `pv9*`, `pv3`, `pv5`, `pv4`, `pv2`, `pv1`, `pv8p`; `development/` tags `t37`, `t38`, `t7`, `t19`, `t20`, `t11`, `t25`, `t15`, `t33`, `t35-recent`, `t36`, `t17`, `t34`, `t14` |
| Table 9 (coverage) | `diagnostics/cited-turn-coverage-*` joined with `base/*-exabase-final2-*` |
| Appendix C | `replay-10m-*` variants |

Tables 6 and 8 and Appendix C are single runs or small sets of runs; the harness scripts that print them are
`final_compare.py`, `ab_compare.py` and `pooled_paired.py`, and each run's own `summary.json` holds its score by
ability.

## What is not here

- The paired replays of one test of a third-party relevance model as a filter between search and evidence assembly.
  The test was withdrawn within the hour and its records were never analysed.
- The partial records of one development run (`t28`), stopped and discarded on 2026-11-10 when its memory was found
  to be contaminated by an earlier experiment. With the item above, these are the run records left out.
- Two development runs (`t33`, pinned state sheets) were stopped after 240 of 700 questions. They are included,
  marked `"partial": true` in a summary generated from their records, because one line of Table 8 rests on them.
- The reference system's own published records. They are not redistributed here; see
  [the note on the reference system](../docs/reference-system.md).
- The evidence text of runs made without `--save-context`. Their records name the turns and queries, not the text.
  The notes the system wrote are in [`memory/`](../memory/).

## License

The records contain BEAM's questions and reference answers and text derived from its conversations. BEAM is published
under CC BY-SA 4.0, and these files are distributed under the same license. See [NOTICE.md](../NOTICE.md).
