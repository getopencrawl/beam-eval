# The note-writing prompts before the correction

The README describes a correction made before publication: two prompts that write memory notes carried benchmark
content as examples. This repository is published as one snapshot, so the earlier text of those prompts is kept
here. The prompts as they are now are in [`harness/facts.py`](../harness/facts.py) and
[`harness/conflicts.py`](../harness/conflicts.py); only the examples differ.

Notes written from the earlier prompts are in [`memory/before-rebuild/`](../memory/), and the runs that searched
them are in `results/opencrawl/full-system-original-notes/` and `results/opencrawl/base-fact-cards/`. How the six
questions scored before and after is in [the log](experiment-log.md), in the entry of 2026-11-12 on the rebuilt
system.

## Fact cards (`facts.py`)

The examples line of the prompt read:

> Examples: "Saturday budget review: now at 5 PM (moved; may clash with tutoring)" - "SD card from TechMart: paid
> $10" - "Nancy's training: May 8, 2024" - "Vector database under evaluation: Milvus 2.3.1, for indexing over 1
> million documents" - "Jet skiing: preferred over parasailing".

and one of its rules read:

> Facts are often mentioned in passing inside a question or request; record them ("How do I use my $15 recorder?"
> -> "Recorder: cost $15").

Each of the five example lines is taken from a benchmark conversation and restates what one test question asks
for. The recorder in the rule also came from a benchmark conversation; no question asks about it.

| Example | Question |
|---|---|
| Saturday budget review: now at 5 PM | 10M `7_knowledge_update_0` |
| SD card from TechMart: paid $10 | 10M `6_information_extraction_1` |
| Nancy's training: May 8, 2024 | 1M `26_information_extraction_0` |
| Vector database under evaluation: Milvus 2.3.1 | 10M `1_information_extraction_1` |
| Jet skiing: preferred over parasailing | 10M `9_preference_following_0` |

They now read:

> Examples: "Choir rehearsal: now Thursday at 7 PM (moved; may clash with the beekeeping class)" - "Bicycle bell
> from Harwick's: paid $9" - "Odalys's glider exam: September 12, 2025" - "Spreadsheet add-in under evaluation:
> Quillon 4.2, for about 300 monthly invoices" - "Oolong: preferred over Earl Grey".

and the rule's illustration is a $40 sewing machine. All of it is invented.

## Conflict notes (`conflicts.py`)

The prompt that restates a conflict in a few words ended:

> each starting with a verb (for example "reported attending a production meeting about the invention" / "says
> they have never attended one").

That is the conflict behind 100K `20_contradiction_resolution_0`. It now reads "reported having adopted a greyhound"
/ "says they have never owned a dog".

## Two docstrings

Neither reached a model. The module docstring of `conflicts.py` illustrated a conflict with "I've never obtained an
API key for this project" after "I got my API key on March 10", the subject of 100K `2_contradiction_resolution_0`;
the docstring of `facts.py` used the "Nancy's training" line above. Both were replaced with invented illustrations.

The quoted lines above are from BEAM conversations and are covered by the dataset's CC BY-SA 4.0 terms
([NOTICE.md](../NOTICE.md)).
