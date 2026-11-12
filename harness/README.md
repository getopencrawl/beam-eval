# Harness

The code that runs the evaluation. To check the reported numbers you do not need any of it: run
[`verify.py`](../verify.py) at the top of the repository. To rerun the evaluation, see
[docs/reproduce.md](../docs/reproduce.md).

## This version and the one the runs used

The reported runs, and every record in [`results/`](../results/) except 18 directories, were made with version 1
of this harness. Version 2 made those 18: the eight runs under `results/opencrawl/published-harness-run/`, the
eight `order-*` paired replays and the two replays of the reference evidence tagged `harness2` (summaries written
by `run.py` say `harnessVersion: opencrawl-1` or `opencrawl-2`). Version 1 loaded the dataset, scored answers, logged, and in adapted form called the model and
framed the run, with modules from the reference system's open-source BEAM harness, so that both systems were shaped
and scored by the same code. That code is not redistributed here. In this version (`opencrawl-2`) `dataset.py`,
`scoring.py`, `llm.py`, `log.py`, `records.py` and the corresponding parts of `run.py` are our own implementations,
and `exabase_prompts.py` is written by `make_exabase_prompts.py` from the published adapter.

The replacements were compared with the modules the runs used, and no difference was found: every turn and question
of all 100 conversations; 25,675 prompts (the answer prompt of each question on three contexts, the judge prompt of
each of its rubric items on three answers, the item-matching prompt of each ordering topic, and three prompts for
abilities the dataset does not have); 14,000 scorings with a stand-in judge; list parsing and order agreement on
every stored answer and verdict; and the model client's requests, byte for byte, on scripted replies under four
settings. [The log](../docs/experiment-log.md) has the table. Those comparisons need the replaced modules, so they
cannot be rerun from this repository. One full run of this version per length and prompt was then set against the
three reported runs; the README gives the outcome. What can be rerun without a model:

```sh
pip install -r requirements.txt      # Python 3.11 or newer
python check_harness.py              # every stored verdict gives its stored score under scoring.py
python check_harness.py --dataset    # the loader against fingerprints of what the runs ingested, and against the
                                     # questions, reference answers, moments and answer prompts the runs stored
python check_harness.py --prompts    # exabase_prompts.py against ExaBase's published file
```

The fingerprints in `fixtures/dataset-fingerprints.json` were made with the loader the runs used: one digest per
conversation over every turn's id, session, position, role, timestamp, BEAM id and text, and one over its questions.
`--dataset` downloads BEAM on first use (about 1.3 GB, most of it the 10M split; `--split 100k` checks one length).

## Files

| File | Role |
|---|---|
| **Dataset, prompts and scoring** | |
| `dataset.py` | Downloads BEAM from Hugging Face at the revisions the runs used; turns a row into dated messages and questions. Its docstring states the three rules that shape the records: ids, time, and the moment a question is asked. |
| `exabase_prompts.py` | The annotation-aided answer prompt and the judge prompts of the published BEAM adapter, unchanged. |
| `make_exabase_prompts.py` | Writes `exabase_prompts.py` from a saved copy of that adapter. |
| `scoring.py` | Rubric judging, Kendall's tau-b for event ordering, run summaries. |
| `check_harness.py` | The checks above. |
| `log.py` | Progress lines. |
| **The run** | |
| `run.py` | Ingest, index, then retrieve, answer and judge every question. All retrieval options are flags here. |
| `records.py` | The results file of a run and the fields every record starts with. |
| `llm.py` | The answer and judge calls (`gpt-5.6-luna`, reasoning off), usage accounting, optional API routes. |
| `opencrawl_api.py` | Every call to OpenCrawl: the session capture API for ingest, the MCP `search` and `fetch` tools for retrieval. |
| `paths.py` | Where run records are read and written. |
| `run_config.sh` | Runs one of the three reported configurations, three answer runs per length. |
| **Memory written before any question is asked** | |
| `notes.py`, `turn_notes.py` | Per-turn notes: a note-taker reads each conversation in windows and writes dated bullets; they are regrouped into one file per turn. |
| `facts.py` | Fact cards: what each of the user's messages states, as short lines. The examples in its prompt are invented. |
| `conflicts.py` | Conflict notes: a later denial of something the user reported earlier. Run it with `--dry` first to find the pairs, then with `--compact` to write the notes. |
| `export_memory.py` | Exports the three kinds of note from the index (the files in [`memory/`](../memory/)). |
| **The comparison** | |
| `replay_reference.py` | Passes the reference system's published evidence through the same answer call and judge. Needs that system's records, which are not in this repository ([docs/reference-system.md](../docs/reference-system.md)). |
| `rejudge.py` | Grades an existing answer set again with this judge. |
| `reanswer.py` | Answers and judges again from the prompts stored by a run made with `--save-context`. |
| `reorder_replay.py` | Paired replay for a flaw in the order of evidence: stored prompts as run, and with their evidence sorted by moment. |
| `reference_context_size.py` | The size of the reference system's contexts, from which OpenCrawl's context caps are taken. Needs the same records. |
| `check_grounding.py` | Counts numbers in the reference system's published answers that occur nowhere in its published evidence. Needs the same records. |
| `final_compare.py` | OpenCrawl against the reference evidence and the published answers: paired bootstrap, by length and ability. |
| `ab_compare.py` | Two OpenCrawl configurations against each other. |
| `replay_variants.py`, `pooled_paired.py` | Paired replay: one retrieval per question, answered under several variants; pooling over lengths. |
| `diag_cited.py` | Coverage diagnostic: are the turns BEAM cites in the evidence the answer model read? |
| **Retrieval measurements without a model** | |
| `retrieval_recall.py` | Recall of BEAM's cited turns in the search results for the question as typed. |
| `proto_search.py`, `proto_sparse.py`, `proto_role.py` | The measurements behind stemming, learned-sparse ranking and the role filter, run against the index directly. |
| `debug_question.py` | Prints the evidence one question would get. |
| **Tested and not adopted** | |
| `state.py`, `ledger.py`, `profile_memory.py` | Writers for state sheets, a fact ledger and an always-loaded profile (Table 8 of the paper). `run.py` keeps their flags. |
| **Setup** | |
| `compose.beam.yaml` | Compose override: more heap for OpenSearch and a loopback port for the measurement scripts. |
| `encode_backfill.py` | Optional: writes the learned-sparse vectors in bulk instead of waiting for the in-cluster encoder. Needs `torch` and `transformers`, which `requirements.txt` does not list. |
| `env.example.sh`, `requirements.txt` | Environment variables and Python dependencies. |

## The reported configurations

All three share these `run.py` flags, with the context cap set per length (11,001, 11,749, 11,339 and 10,467 tokens
for 100K, 500K, 1M and 10M: the reference system's mean context size):

```
--expand 3 --follow-up 3 --point-in-time --memories --deep 12 --deep-whole
--memory-share 0.2 --user-pass 1.0 --order time --context-tokens <cap>
```

| Name in the paper | Tag | Additional flags |
|---|---|---|
| Base system | `final2` | none |
| Base + fact cards | `final3` | `--facts --clean-notes` |
| Full system, original notes | `final4` | `--facts --clean-notes --conflicts --conflicts-share 0.03` |
| Full system (reported) | `final5` | the same flags as `final4`; what differs is the memory it searches |

`final5` searches fact cards and conflict notes rebuilt from the prompts as they are in `facts.py` and `conflicts.py`
now, whose examples are invented. `final3` and `final4` searched the first version of those notes, written from
prompts whose examples were lines from benchmark conversations. Both versions are in [`memory/`](../memory/).

`--prompt paper` selects BEAM's own answer prompt and `--prompt exabase` the annotation-aided one. What each flag does
is in `python run.py --help` and in Table 1 of the paper.

## What the answer model is given

Only the question and the retrieved evidence, formatted as JSON items with rank, timestamp, role, turn number and
text. Under `--prompt exabase` the prompt also receives the dataset annotations that prompt is built around; that is
the property of the prompt the paper measures, not something this harness adds.

Retrieval receives two things: the question text, and the moment the question is asked. It gets no ability label, no
reference answer and no rubric. The moment is the end of the conversation, except for knowledge-update questions,
which are asked as of the turn BEAM marks as the update. That timing comes from the dataset and is set in
`dataset.py`; the reference harness sends the same moment to its system with each question, so both systems get it.
It is the one piece of dataset annotation that reaches retrieval.

`answer_question` in `run.py` is the whole path. Run `a` of the reported system at each length and prompt, in
`results/opencrawl/full-system/`, stores the resulting prompt verbatim, as do the runs in
`results/opencrawl/audit-run/`; `verify.py --all` at the top of the repository checks them.
