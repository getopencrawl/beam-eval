# Notices

This repository holds our own work next to material that belongs to others. The terms differ by part.

## Code

The code is licensed under the [Apache License 2.0](LICENSE), with one exception.

**The BEAM adapter's prompts.** `harness/exabase_prompts.py` contains the answer-prompt method and the two judge
prompts of a published BEAM adapter ([source](https://fabric.so/p/beam-3VjBcqEVRofZyA5CeazeX)), reproduced unchanged
so that answers are produced and judged the way they are for other published BEAM results that use it. We know
the adapter as ExaBase's from published BEAM work that uses it, and follow that attribution; the page itself names
no organisation and states no license. The SHA-256 of the file is
`584b672d957f3e6f75e96f881ec31da22e1039da1df5fbedb53dc6a9145cfc43`; `python harness/check_harness.py --prompts`
downloads it and compares, and `harness/make_exabase_prompts.py` is how our copy was written from it. The prompts
are not our work and are not covered by this repository's license; this attribution does not relicense them. The
same text appears inside the answer prompts stored with some runs under `results/`. The scoring rules in
`harness/scoring.py` are the ones the adapter implements; that code is ours. If you are the adapter's author and
want the attribution or the reproduction changed, please open an issue.

**Where the harness came from.** The runs in `results/` were made with an earlier version of this harness, which
took its dataset loader, scorer and logging, and in modified form its model client and the frame of its run script,
from the reference system's open-source BEAM harness. That code is not part of this repository. The files that
replaced it (`dataset.py`, `scoring.py`, `llm.py`, `log.py`, `records.py` and the corresponding parts of `run.py`)
are our own implementations; [harness/README.md](harness/README.md) says how they were checked against the versions
the runs used.

## Data

**BEAM.** "Beyond a Million Tokens: Benchmarking and Enhancing Long-Term Memory in LLMs", Mohammad Tavakoli, Alireza
Salemi, Carrie Ye, Mohamed Abdalla, Hamed Zamani and J Ross Mitchell, ICLR 2026
([arXiv:2510.27246](https://arxiv.org/abs/2510.27246)). The dataset
([Mohammadta/BEAM](https://huggingface.co/datasets/Mohammadta/BEAM),
[Mohammadta/BEAM-10M](https://huggingface.co/datasets/Mohammadta/BEAM-10M)) is published under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The harness downloads it from Hugging Face at the
revisions the runs used; the dataset itself is not in this repository.

**Dataset-derived files.** Everything under `results/` and `memory/` contains or is derived from BEAM: questions and
reference answers in the run records, and notes, fact cards and conflict notes written from the conversations. These
files are distributed under CC BY-SA 4.0, including what we added to them (model answers, judge verdicts, notes), and
are not under the Apache license. They are evaluation records and adaptations, not the original dataset files.
`harness/fixtures/dataset-fingerprints.json` holds digests of the conversations and nothing of their text.

**The reference system's published results.** The controlled comparison replays the per-question evidence that one
published memory system released with its BEAM results. This repository does not name that system and does not
redistribute its records. `results/reference/` holds only what this harness produced from them: the answers our
answer call gave on that evidence, the judge's verdicts and scores, and aggregate statistics
([docs/reference-system.md](docs/reference-system.md)).

## Names

OpenCrawl is not affiliated with ExaBase, OpenRouter, OpenAI or the authors of BEAM. Their names are used to say
whose work was used.
