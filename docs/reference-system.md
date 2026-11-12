# The reference system

The comparison in this repository is against one published BEAM result. The system behind it is not named here or in
the paper; it is called the reference system. This note says why it was chosen, what of it was used, what this
repository contains of it and what it does not, and what that means for checking the comparison.

## Why this one

Two reasons.

1. **It publishes the evidence.** Its developers released a BEAM harness and, for each of the 2,000 questions, a
   record holding the exact evidence their answer model read. That is what makes a controlled comparison possible.
2. **Its scores are the highest we know of** under the annotation-aided prompt: about 90 over all questions by its
   own report.

Other vendors report BEAM scores too (see [the experiment log](experiment-log.md#other-published-beam-numbers)).
Those numbers come from protocols that are not fully stated, so they are not comparable with the ones here, in either
direction. Nothing in this repository ranks OpenCrawl among them.

## What it published, and what we did with it

Its harness answers and judges with `gpt-5.6-luna`, reasoning off, through an API router (OpenRouter), using the
prompts of ExaBase's BEAM adapter. Recall runs at the moment the question is asked, for up to 100 results within
8,000 tokens of evidence. Its runs were made about six weeks before ours.

We use its records in three ways. None of them runs its system.

| | What is compared with OpenCrawl | Script | Result, all 2,000 questions |
|---|---|---|---|
| 1 | Its **evidence**, passed unmodified through our answer call and judge, several times | `harness/replay_reference.py` | BEAM's own prompt: 58.51 against OpenCrawl's 61.17. Annotation-aided prompt: 87.41 against 88.25. |
| 2 | Its **published answers**, graded by our judge, three passes | `harness/rejudge.py` | 89.08 against OpenCrawl's 88.25 |
| 3 | Its **own reported score**, from its own judge run | none | about 90 |

Row 1 is the controlled comparison: one answer call and one judge for both sides, with only the evidence differing.
It is the only row that isolates the memory system, and it is the one the README reports. The two sides were not
always answered on the same day; a comparison restricted to runs of one day is reported next to it. The replays pooled on
the reference side are the ones made with this same answer call; replays made to test other settings (reasoning
levels, another API surface, the API router) are kept apart, and so are two replays of the 100K evidence made
later that day with the published harness to check it (pooled in, they would move the 100K leads from +3.00 to
+3.15 and from +0.66 to +0.68).

Rows 2 and 3 compare OpenCrawl's answers with answers generated on another day through another route, and row 3 also
with another judge run. In both, the reference system is ahead.

## What is in this repository, and what is not

Not here: the reference system's name, a link to its repository, the scores it reports per length, and its published
records themselves (the evidence and the answers).

Here, under [`results/reference/`](../results/reference/):

- **For every replay of its evidence:** each question's score in each answer run and the last answer. The replays of
  2026-11-12 also keep every answer and the judge's verdicts.
- **For its published answers:** our judge's score for each question in each of three passes. The answers are not
  included.
- **The size of its contexts:** `context-tokens.json`, the mean and spread of the context its answer model read at
  each length, which is where OpenCrawl's context caps come from.

And the scripts that make such files from its records: `replay_reference.py`, with every transformation it can
apply to the evidence, `rejudge.py` and `reference_context_size.py`. The files themselves, except the two replays tagged `harness2`, were written by version 1
of the harness ([harness/README.md](../harness/README.md)). `check_grounding.py` is the check in the table further
down; it prints its counts and writes nothing.

What follows for a reader:

- **Recomputing works.** `verify.py` recomputes every reference-side number from those per-question scores, and
  re-derives the scores of the 2026-11-12 replays from their verdicts.
- **Regenerating does not, from this repository alone.** Answering the reference evidence again needs that system's
  published records. The scripts read them from a directory you supply (below).
- **So one thing is taken on trust:** that the scores stored under `results/reference/` came from the evidence the
  reference system published, unmodified. OpenCrawl's side carries no such gap: its prompts are stored and can be
  answered again.

## The records the scripts read

One file per length, `<length>/results.jsonl` with `<length>` one of `100k`, `500k`, `1m`, `10m`, one JSON object per
question:

| Field | Used by | Content |
|---|---|---|
| `questionId` | all | BEAM's question as `<conversation>_<ability>_<index>`, the ids `harness/dataset.py` writes |
| `recall` | `replay_reference.py`, `check_grounding.py`, `reference_context_size.py` | The evidence object as that system's API returned it. The `raw` variant, the one behind the README's result table, passes it to the prompt as compact JSON, untouched. The other variants re-present its list of results; `transform()` in `replay_reference.py` shows what each reads |
| `answer` | `rejudge.py`, `check_grounding.py` | Its answer model's answer |
| `category` | `check_grounding.py` | The ability, as in BEAM |

```sh
export BEAM_REFERENCE_RESULTS=/path/to/those/records
cd harness && pip install -r requirements.txt
export OPENAI_API_KEY=... BEAM_CACHE=$HOME/.cache/beam-eval
python replay_reference.py --split 10m --variant raw --repeat 2 --prompt paper --tag _mine   # BEAM's own prompt
python replay_reference.py --split 10m --variant raw --repeat 3 --tag _mine_aided            # annotation-aided prompt
```

This needs an OpenAI key and the dataset, which the harness downloads; it does not need OpenCrawl. A 10M replay is
200 questions per answer run. The same scripts work on any system's records in this form.

## The gap between its evidence and its answers

Its published answers score 89.08 under our judge. Its published evidence, answered by the same model with the
same prompt six weeks later, scores 87.41 (87.33 on 2026-11-10, 87.57 on 2026-11-12). The gap is 1.1 to 2.8 points depending on the length, and it is the reason row 1
and row 2 point in different directions.

What we checked:

| Possible cause | Check | Outcome |
|---|---|---|
| The API route | Sent the answer call of both systems through OpenRouter with the reference harness's exact request, at 1M and 10M only (the account was limited to 20 requests a minute) | Its evidence scores the same on both routes: 88.11 and 87.84 at 1M, 81.75 and 81.25 at 10M. Published answers: 89.83 and 84.48. |
| A pinned model snapshot | Looked for dated snapshots of the model at the provider | None is listed. OpenRouter resolves the name to an id that the provider's API does not accept. |
| A reasoning setting | Answered its 10M evidence with reasoning low and medium | 77.5 and 78.3: lower, not higher. `minimal` is not supported by the model. |
| The provider's other API surface | Responses API, 10M | 82.3 |
| Evidence the records do not show | Counted numbers in the answers that occur nowhere in the published evidence (`harness/check_grounding.py`) | About as rare in its published answers as in our replays: 4.7% against 2.7% at 10M, 3.8% against 4.9% at 1M. Its harness builds the prompt from exactly the saved object. |
| A different answer style | Compared the texts | 141 of 700 answers at 1M are identical strings to a replay. |
| The judge | Its own judge run scored its answers 0.5 to 1.3 points above what the same judge prompt gives now, depending on the length | Explains row 3 against row 2, not this gap. |

What remains is consistent with the model having behaved differently on the day those answers were generated. We do
not know that, and we are not claiming an error on the reference system's side. The practical point is narrower: a
published answer set is a sample from one model state on one day, and a later run cannot be compared with it fairly.
A published evidence set can be.

## Limits of the comparison

- **Unnamed, and its records are not here.** See above: the reference side can be recomputed from this repository
  but not regenerated from it.
- **A snapshot.** The evidence is what its system retrieved for its publication. The system may have changed since.
- **We could not run it.** Everything rests on the published records being what its answer model read, which the
  checks above support but cannot prove.
- **Budget parity is on average.** OpenCrawl's context is capped at the mean size of the reference context for each
  length (11.0k, 11.7k, 11.3k and 10.5k tokens), not question by question. The reference harness budgets 8,000 tokens
  of evidence text, as this harness does by default; the cap used here is on the whole string the model reads,
  serialization included, so that both contexts are the same size.
- **Presentation.** Its evidence arrives in its own serialization and in rank order; OpenCrawl's is in time
  order. Re-presenting its evidence in time order, and in OpenCrawl's item format, moves the overall lead under BEAM's
  own prompt to +2.37 (+1.13 to +3.61) and +3.03 (+1.88 to +4.18). Single lengths are less stable; the
  README and `verify.py --all` give every one of them. "Time order" in both systems' evidence means sorted by the
  timestamp as written, which is not always the order of the moments: the README's limits say how often and what
  it costs.
- **The same timing rule.** Both systems are asked knowledge-update questions as of the turn BEAM marks as the
  update; that is the reference harness's protocol and it is kept unchanged.
- **Developed on these questions.** BEAM has no held-out split, and OpenCrawl's configuration was developed on the
  questions it is reported on. We do not know how the reference system was developed. See the README on how
  selection was limited.

If something here misdescribes the reference system, please open an issue; we will correct it.
