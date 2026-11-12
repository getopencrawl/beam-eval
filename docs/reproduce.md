# Reproducing the results

There are three levels, by what they need, and between the first two a check of the harness itself. Each checks
more of the pipeline than the one before.

| Level | Needs | Checks | Time |
|---|---|---|---|
| 1. Recompute | Python 3.10 or newer | The reported numbers follow from the per-question records | about a minute |
| 1b. Check the harness | Python 3.11 or newer, its requirements; for the loader, the dataset | The published harness gives the scores, conversations, questions and prompts the runs recorded | minutes |
| 2. Answer and judge again | An OpenAI API key | The answer and judge stage from stored inputs: OpenCrawl's from this repository, the reference system's only with its published records, which are not included | minutes to an hour per run |
| 3. Run everything | A machine for the self-hosted stack, an OpenAI API key | Ingest, memory writing, retrieval, answering, judging | days, mostly note writing |

## 1. Recompute the numbers

```sh
git clone https://github.com/getopencrawl/beam-eval && cd beam-eval
python verify.py          # integrity of every run and the reported comparison
python verify.py --all    # every table the script covers; `python verify.py --help` lists them
```

No dependencies, no network. Where a record keeps the judge's verdict beside its score, the script re-derives the
score from it (every OpenCrawl run and the replays of the reference evidence made on 2026-11-12; the earlier replays
and the re-graded published answers keep scores only, and the script prints the counts). It recomputes each table
with three intervals, a t interval over conversations and paired bootstraps over questions and over conversations,
and compares the outcome with
[`results/expected.json`](../results/expected.json), which holds the numbers quoted in the README, the paper and the
log. It also reads the README's result table out of the file. It exits non-zero on any difference. CI runs
`verify.py --all` on every push.

`verify.py` uses none of the harness. The harness can be checked against the same records, still without a model:

```sh
cd harness && pip install -r requirements.txt
python check_harness.py              # every stored verdict gives its stored score under harness/scoring.py
python check_harness.py --dataset    # the loader gives the conversations, questions and prompts the runs recorded
python check_harness.py --prompts    # the prompts are those of ExaBase's published adapter
```

This matters because the runs were made with an earlier version of the harness; [harness/README.md](../harness/README.md)
says what changed and what these checks cover. `--dataset` downloads BEAM (about 1.3 GB).

## 2. Answer and judge again

OpenCrawl's side can be answered and judged again from inputs stored in this repository, without running a memory
system. The reference system's side can be too, but only with its published records, which this repository does not
include.

```sh
cd harness                      # Python 3.11 or newer
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp env.example.sh env.sh        # set OPENAI_API_KEY and BEAM_CACHE; OPENCRAWL_DEPLOY_DIR is not needed here
. ./env.sh
```

**OpenCrawl's side.** Run `a` of the reported system at each length and prompt stores the exact prompt the answer
model received for every question.
`reanswer.py` sends those prompts to the answer model again and judges the answers:

```sh
python reanswer.py --run 10m-search-paper-final5-a --limit 20     # a quick look
python reanswer.py --run 10m-search-paper-final5-a --repeat 2     # 200 questions, two answer runs
```

**The reference system's side.** `replay_reference.py` does the same with the evidence the reference system
published. Those records are not in this repository;
[the note on the reference system](reference-system.md#the-records-the-scripts-read) describes the form the script
reads. With a copy of them:

```sh
export BEAM_REFERENCE_RESULTS=/path/to/those/records
python replay_reference.py --split 10m --variant raw --repeat 2 --prompt paper --tag _mine
```

Without them, what this repository offers for the reference side is the per-question scores of every replay we
made, the answers and verdicts of the replays of 2026-11-12, and the recomputation in level 1.

**The judge alone.** `rejudge.py` grades an existing answer set again, which is how the reference system's published
answers were scored here and how judge variance was measured.

New runs land in `results/local/`. `final_compare.py`, `ab_compare.py` and `pooled_paired.py` find runs by name in
any folder under `results/`.

Expect scores to move by one to two points between answer runs on the 700-question lengths and by two to three at
10M, and by 0.1 to 1.0 between judge passes over identical answers. That is why every reported number is a mean over several
runs with a paired interval.

## 3. Run everything

**The stack.** The evaluated search is the branch
[`search-relevance-stemming`](https://github.com/getopencrawl/opencrawl-core/tree/search-relevance-stemming) of
OpenCrawl core, commit `95863d8`. It adds stemming, time bounds and order, the role filter, learned-sparse retrieval,
passage indexing and neighbour fetch to the search of version 0.2.57. The branch is not merged. The main branch has
since gained some of these in a different form and has neither stemming nor semantic retrieval, so the runs here
cannot be reproduced on it.

```sh
git clone --branch search-relevance-stemming https://github.com/getopencrawl/opencrawl-core && cd opencrawl-core
git rev-parse 'HEAD^{tree}'    # 7f3de1099ffc0920f2cb174686fe052505d85b2a
COMPOSE_FILE=compose.yaml:/path/to/beam-eval/harness/compose.beam.yaml ./deploy/up.sh
```

The runs were made at commit `97ed5b0`, which has this same tree; that repository's history was rewritten on
2026-11-11, and the tree hash above is what identifies the code.

Then enable semantic retrieval as described in that checkout's `docs/self-host.md` ("Optional: semantic
retrieval"). The override in `compose.beam.yaml` gives OpenSearch a 6 GB heap and publishes it on
`127.0.0.1:19200` for the measurement scripts. The reported runs used one machine with 8 vCPUs and 32 GB of memory;
the index reaches about 1.1 million passages and 5.6 GB.

**Ingest and index.** `run.py` uploads each conversation as one captured session through the product's session
capture API and waits until every turn is searchable. The published runs used dataset revisions `3205395e` (100K to
1M) and `9b209619` (10M); `dataset.py` downloads exactly those, and `run.py` prints a note if a cached copy is another.

```sh
cd /path/to/beam-eval/harness && . ./env.sh        # now with OPENCRAWL_DEPLOY_DIR set
for length in 100k 500k 1m 10m; do python run.py --split $length --ingest-only; done
```

**Memory.** Three passes write the notes, in this order, each stored through the product's memory API. This is the
expensive part: about 380 million model tokens for the per-turn notes, 24 million for the fact cards and 4 million
for the conflict pass.

```sh
for length in 100k 500k 1m 10m; do
  python notes.py --split $length --reasoning low && python turn_notes.py --split $length   # per-turn notes
  python facts.py --split $length                                                           # fact cards
  python conflicts.py --split $length --dry --show 0    # find conflicting pairs (searches the user's messages)
  python conflicts.py --split $length --compact         # write the conflict notes
done
```

The notes we wrote are in [`memory/`](../memory/), so the passes can be inspected without being rerun. There is no
importer for those files; a rerun writes its own notes, and note writing is itself a source of run-to-run variation.

**Sparse vectors, last.** Every passage, of the conversations and of the notes, needs its learned-sparse vector
before runs are comparable. The cluster encodes in the background at about ten long passages a second, which takes
more than a day for the 1.1 million passages of the full index. `encode_backfill.py` writes the same vectors in
batches from the host (`pip install torch transformers` first); for the published runs the same encoder ran on a GPU.

```sh
python encode_backfill.py <model id> beam3- notes:beam3-    # conversations, then notes; <model id> as in deploy/.env
```

Searches work before encoding finishes, with lexical ranking for the passages that have no vector yet, so wait until
no passage is left without one.

**Runs and comparison.**

```sh
bash run_config.sh full-system paper       # three runs per length, BEAM's own prompt, written under the tag my-final5
bash run_config.sh full-system exabase     # annotation-aided prompt
python final_compare.py --config my-final5 --paper
python final_compare.py --config my-final5
```

`SAVE_CONTEXT=a bash run_config.sh ...` makes run `a` store the exact prompt of every question, as the published runs
do. The comparison needs the replays of the reference evidence, which are in `results/reference/`.

```sh
python final_compare.py --config final5 --paper            # the published runs, for comparison
```

One question costs seven search queries, each run twice (everything, and the user's messages only), two small model
calls on the retrieval side (about 2,400 tokens together), the reading of up to twelve whole messages, one answer
call with about 11,000 prompt tokens, and on average three judge calls under the annotation-aided prompt and five
under BEAM's own. A 700-question run took about 20 minutes with
five runs in parallel.

## What a rerun will not reproduce exactly

- **Model behaviour.** `gpt-5.6-luna` has no dated snapshot. The reference system's published answers could not be
  regenerated from its own evidence six weeks after they were made
  ([details](reference-system.md#the-gap-between-its-evidence-and-its-answers)); the same can happen to ours.
- **Retrieval.** Query rewrites and follow-up queries come from a model, so two runs retrieve slightly different
  evidence.
- **Notes.** Written by a model once; see above.

The per-question records are the fixed point: they are what was measured, and `verify.py` ties every reported number
to them.
