# Memory written for the benchmark

The notes that the three note-writing passes produced from the BEAM conversations, exported from the search index
with `harness/export_memory.py`. They are what the `--memories`, `--facts` and `--conflicts` options of the harness
search. The passes are given the conversation and nothing else: no question, no reference answer, no rubric, no
ability label. A reader can check that here.

| File | Passages | Written by | Content |
|---|---:|---|---|
| `notes-<length>.jsonl.gz` | 317,474 | `harness/notes.py`, regrouped by `harness/turn_notes.py` | Per-turn notes: dated bullets about what was said, decided, changed or advised in a turn. |
| `fact-cards-<length>.jsonl.gz` | 155,572 | `harness/facts.py` | What each of the user's messages states or takes for granted, as short lines. |
| `conflict-notes-<length>.jsonl.gz` | 1,355 | `harness/conflicts.py` | A later denial of something the user reported earlier, naming both claims without their values. |
| `conflict-pairs-<length>.jsonl.gz` | 2,895 | `harness/conflicts.py` | The conflicting pairs behind the conflict notes: both turns, the claims as first extracted, and as restated for the note. |

One line per indexed passage: `session` (`beam3-<length>-<conversation number>`), `path` (the memory file, named after
the turn it describes), `modifiedAt` (the time of that turn, which is what point-in-time search filters on), `chunk`
and `text`. Only the current generation of each file is exported, which is what search returns.

## Two versions of the fact cards and conflict notes

The files above are the ones the reported system (`final5`) searches. They were written on 2026-11-12 from prompts
whose examples are invented.

`before-rebuild/` holds the first version: 154,892 fact-card passages, 1,327 conflict notes and 2,783 pairs, written
on 2026-11-10. The prompts that wrote them used lines from benchmark conversations as examples, and those lines
restated what six test questions ask for. Every run tagged `final3` or `final4`, the audit runs and the paired
replays searched that version. [The log](../docs/experiment-log.md) has the details and the questions concerned.

The per-turn notes are the same for both: their prompt contains no example, and they were not rebuilt.

## License

Derived from BEAM and distributed under CC BY-SA 4.0. See [NOTICE.md](../NOTICE.md).

The notes contain what the simulated users of BEAM typed, including made-up credentials in code samples (the AWS
documentation's example access key, placeholder tokens). None is real.
