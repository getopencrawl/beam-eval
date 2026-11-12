#!/usr/bin/env python3
"""Recompute the reported numbers from the per-question records in results/.

Standard library only: no API key, no dataset download, no network.

    python verify.py          # integrity of every run, and the reported comparison (about a minute)
    python verify.py --all    # also every other table this script covers (a few minutes)

What is checked

1. Integrity. Where a record stores the judge's verdict beside its score, the score is re-derived from the
   verdict. That covers every OpenCrawl run and the replays of the reference evidence made on 2026-11-12; the
   earlier replays, the re-graded answer sets and the paired replays keep scores only, and the script prints how
   many scores it could and could not re-derive. Every run's summary must follow from its records; the reported
   runs must cover every question of their length, and none of them may have failed a question.
2. The controlled comparison. A question's score is averaged over a system's answer runs, and the difference
   between the two systems is given three 95% intervals:
     - a paired bootstrap over questions (10,000 resamples, fixed seed; percentile interval from the 250th to the
       9,750th of the sorted resampled means), the statistic used while the system was developed;
     - the same bootstrap over conversations, because the twenty questions of a conversation share its index and
       its notes and are not independent;
     - a Student t interval over the per-conversation mean differences, the most cautious of the three when the
       conversations are few (ten at 10M), where a bootstrap over clusters runs narrow.
   The README quotes the t interval.
3. The result table of README.md, read from the file, shows the recomputed numbers.
4. With --all, the other tables named under "Covered" below, and the prompts stored by the runs that keep them.

Every recomputed number is compared with results/expected.json, which holds the numbers quoted in the README, the
paper and the experiment log. That file was written by this script (--write-expected) when the numbers were
published, so a pass means that the records, this code and the quoted numbers still agree; whether the statistics
are the right ones is for the reader of this file to judge. Numbers quoted in prose are not read back from the
documents; only the README's result table is.

Exit status: 0 if everything matches at the printed precision, 1 otherwise.
"""

import argparse
import functools
import gzip
import json
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path

COVERAGE = """Covered: the result table of README.md; paper Tables 2 to 5, the build-up and by-ability numbers of
Section 5.2, Table 6, Table 7, Table 9 and Appendix C; the comparison with the same-day replays only, without
knowledge-update questions, and for the system before the rebuild with and without the six questions of the prompt
leak; the run made with the published harness; the paired replay for the order of evidence; the runs that store
their prompts.
Not covered: the single-run rows of Table 8 and the per-length cells of Tables B1 and B2. Their runs are under
results/ and the harness scripts named in results/README.md print them."""

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
EXPECTED_FILE = RESULTS / "expected.json"
SPLITS = ("100k", "500k", "1m", "10m")
QUESTIONS = {"100k": 400, "500k": 700, "1m": 700, "10m": 200}
RESAMPLES, SEED = 10_000, 7
PROMPT_NAME = {"paper": "BEAM's own prompt", "exabase": "Annotation-aided prompt"}

# --- Which runs make up each side ---------------------------------------------------------------------------------

# The reported system (tag of its answer runs, folder under results/opencrawl/): the full system on memory notes
# rebuilt after a leak was found in two note-writing prompts. EARLIER is the same system as first measured.
REPORTED = {"tag": "final5", "folder": "full-system"}
EARLIER = {"tag": "final4", "folder": "full-system-original-notes"}

# The reference system's published evidence, answered by the same answer call as OpenCrawl. One directory holds
# several answer runs (each record carries a list of scores); the directories of a length are pooled.
REPLAYS_FIRST = {  # made on 2026-11-10, with the earlier runs
    "paper": {split: [f"replay-{split}-raw_paper", f"replay-{split}-raw_paper2"] for split in SPLITS},
    "exabase": {"100k": ["replay-100k-raw_x3"], "500k": ["replay-500k-raw_x3"],
                "1m": ["replay-1m-raw", "replay-1m-raw_x3"], "10m": ["replay-10m-raw", "replay-10m-raw_more"]},
}
REPLAYS_SAME_DAY = {  # made on 2026-11-12, the day of the reported runs
    "paper": {split: [f"replay-{split}-raw_paper_1112"] for split in SPLITS},
    "exabase": {split: [f"replay-{split}-raw_1112"] for split in SPLITS},
}
REFERENCE = {prompt: {split: REPLAYS_FIRST[prompt][split] + REPLAYS_SAME_DAY[prompt][split] for split in SPLITS}
             for prompt in ("paper", "exabase")}
REFERENCE_ROUTER = {split: [f"replay-{split}-raw_or", f"replay-{split}-raw_or2"] for split in ("1m", "10m")}

# Questions whose answers stood as examples in the first version of two note-writing prompts
# (docs/experiment-log.md, 2026-11-12).
LEAKED = {("10m", "7_knowledge_update_0"), ("10m", "6_information_extraction_1"), ("10m", "1_information_extraction_1"),
          ("10m", "9_preference_following_0"), ("1m", "26_information_extraction_0"), ("100k", "20_contradiction_resolution_0")}


# --- Reading run records ------------------------------------------------------------------------------------------

def read_rows(run: Path) -> list[dict]:
    with gzip.open(run / "results.jsonl.gz", "rt", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def run_dirs(folder: str, pattern: str) -> list[Path]:
    """Run directories of one folder under results/ whose name matches, in name order."""
    found = sorted(d for d in (RESULTS / folder).iterdir() if d.is_dir() and fnmatchcase(d.name, pattern))
    if not found:
        raise SystemExit(f"no run matches {pattern} in results/{folder}")
    return found


def opencrawl(tag: str, prompt: str, split: str, folder: str) -> list[Path]:
    return run_dirs(f"opencrawl/{folder}", f"{split}-search-{prompt}-{tag}-*")


def reported(prompt: str):
    return lambda split: opencrawl(REPORTED["tag"], prompt, split, REPORTED["folder"])


def earlier(prompt: str):
    return lambda split: opencrawl(EARLIER["tag"], prompt, split, EARLIER["folder"])


def reference(names: list[str]) -> list[Path]:
    return [RESULTS / "reference/evidence-replays" / name for name in names]


def published_answers(split: str) -> list[Path]:
    return [RESULTS / "reference/published-answers" / f"published-answers-{split}"]


def scores_by_question(runs: list[Path]) -> dict[str, list[float]]:
    """Every score each question received across the given runs."""
    scores: dict[str, list[float]] = {}
    for run in runs:
        for row in read_rows(run):
            scores.setdefault(row["questionId"], []).extend(row["scores"] if "scores" in row else [row["score"]])
    return scores


# --- Scores from verdicts -----------------------------------------------------------------------------------------

def kendall_tau_b(x: list[int], y: list[int]) -> float | None:
    concordant = discordant = ties_x = ties_y = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 or dy == 0:
                ties_x += dx == 0
                ties_y += dy == 0
            elif (dx > 0) == (dy > 0):
                concordant += 1
            else:
                discordant += 1
    pairs = len(x) * (len(x) - 1) / 2
    denominator = math.sqrt((pairs - ties_x) * (pairs - ties_y))
    return None if denominator == 0 else (concordant - discordant) / denominator


def ordering_score(reference_order: list[str], answer_order: list[str]) -> float:
    """The event-ordering score of harness/scoring.py: Kendall's tau-b between the two orders, mapped to 0..1."""
    if not reference_order or not answer_order:
        return 0.0
    topics = list(dict.fromkeys(reference_order + answer_order))

    def ranks(order: list[str]) -> list[int]:
        position = {topic: index + 1 for index, topic in enumerate(order)}
        return [position.get(topic, len(topics) + 1) for topic in topics]

    tau = kendall_tau_b(ranks(reference_order), ranks(answer_order))
    return 0.0 if tau is None else (tau + 1) / 2


def score_from_verdict(verdict: dict) -> float | None:
    """A question's score as it follows from its stored verdict, or None where the record holds no verdict."""
    if verdict.get("method") == "rubric" and "items" in verdict:
        return math.fsum(item["score"] for item in verdict["items"]) / len(verdict["items"])
    if verdict.get("method") == "event_ordering" and "note" not in verdict:
        return ordering_score(verdict.get("reference") or [], verdict.get("answer") or [])
    return None


# --- Statistics ---------------------------------------------------------------------------------------------------

def mean(values) -> float:
    values = list(values)
    return math.fsum(values) / len(values)


def percentile_interval(means: list[float]) -> tuple[float, float]:
    means.sort()
    return means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES)]


def interval_over_questions(differences: list[float]) -> tuple[float, float]:
    """Resample questions with replacement."""
    rng = random.Random(SEED)
    count = len(differences)
    return percentile_interval([math.fsum(differences[rng.randrange(count)] for _ in range(count)) / count
                                for _ in range(RESAMPLES)])


def interval_over_conversations(clusters: list[list[float]]) -> tuple[float, float]:
    """Resample conversations with replacement, each bringing all of its questions."""
    rng = random.Random(SEED)
    totals = [(math.fsum(cluster), len(cluster)) for cluster in clusters]
    means = []
    for _ in range(RESAMPLES):
        drawn = [totals[rng.randrange(len(totals))] for _ in range(len(totals))]
        means.append(math.fsum(total for total, _ in drawn) / sum(size for _, size in drawn))
    return percentile_interval(means)


@functools.lru_cache(maxsize=None)
def t_quantile(probability: float, degrees: int) -> float:
    """Quantile of Student's t distribution: bisection on a Simpson integral of its density."""
    log_norm = math.lgamma((degrees + 1) / 2) - math.lgamma(degrees / 2) - 0.5 * math.log(degrees * math.pi)

    def density(x: float) -> float:
        return math.exp(log_norm - (degrees + 1) / 2 * math.log1p(x * x / degrees))

    def cdf(x: float, steps: int = 2000) -> float:
        width = x / steps
        total = density(0.0) + density(x) + sum((4 if i % 2 else 2) * density(i * width) for i in range(1, steps))
        return 0.5 + total * width / 3

    low, high = 0.0, 50.0
    for _ in range(60):
        middle = (low + high) / 2
        low, high = (middle, high) if cdf(middle) < probability else (low, middle)
    return (low + high) / 2


def interval_t(clusters: list[list[float]]) -> tuple[float, float]:
    """95% Student t interval for the mean of the per-conversation mean differences."""
    means = [mean(cluster) for cluster in clusters]
    centre = mean(means)
    deviation = math.sqrt(math.fsum((value - centre) ** 2 for value in means) / (len(means) - 1))
    half = t_quantile(0.975, len(means) - 1) * deviation / math.sqrt(len(means))
    return centre - half, centre + half


@dataclass
class Pair:
    """One question: where it is from, and each side's mean score on it."""
    split: str
    question: str
    ours: float
    theirs: float

    @property
    def conversation(self) -> tuple[str, str]:
        return self.split, self.question.split("_")[0]


@dataclass
class Comparison:
    questions: int
    ours: float
    theirs: float
    lead: float
    interval: tuple[float, float]                  # bootstrap over questions
    interval_by_conversation: tuple[float, float]  # bootstrap over conversations
    interval_t: tuple[float, float]                # Student t over per-conversation means

    def points(self) -> list:
        """[ours, theirs, lead, then low and high of the three intervals in the order above], in points."""
        values = (self.ours, self.theirs, self.lead, *self.interval, *self.interval_by_conversation, *self.interval_t)
        return [round(100 * value, 2) for value in values]


def compare(pairs: list[Pair]) -> Comparison:
    differences = [pair.ours - pair.theirs for pair in pairs]
    clusters: dict[tuple, list[float]] = {}
    for pair, difference in zip(pairs, differences):
        clusters.setdefault(pair.conversation, []).append(difference)
    ours, theirs = mean(pair.ours for pair in pairs), mean(pair.theirs for pair in pairs)
    by_conversation = list(clusters.values())
    return Comparison(len(pairs), ours, theirs, ours - theirs, interval_over_questions(differences),
                      interval_over_conversations(by_conversation), interval_t(by_conversation))


def question_pairs(split: str, ours: list[Path], theirs: list[Path]) -> list[Pair]:
    """Per-question mean scores of two sides, in question-id order. Both must have answered the same questions."""
    a, b = scores_by_question(ours), scores_by_question(theirs)
    if set(a) != set(b):
        raise SystemExit(f"{split}: the two sides do not cover the same questions ({len(a)} and {len(b)})")
    return [Pair(split, question, mean(a[question]), mean(b[question])) for question in sorted(a)]


def by_split(ours_of, theirs_of, splits=SPLITS, keep=lambda pair: True) -> dict[str, Comparison]:
    """One comparison per length, then all of them pooled."""
    rows, pooled = {}, []
    for split in splits:
        pairs = [pair for pair in question_pairs(split, ours_of(split), theirs_of(split)) if keep(pair)]
        rows[split] = compare(pairs)
        pooled += pairs
    rows["all"] = compare(pooled)
    return rows


# --- Output and checking ------------------------------------------------------------------------------------------

class Report:
    """Compares each recomputed value with the quoted one, or records the values when writing expected.json."""

    def __init__(self, quoted: dict, recording: bool) -> None:
        self.quoted, self.recording = quoted, recording
        self.recorded: dict = {}
        self.checked, self.failures = 0, []

    def check(self, label: str, got) -> None:
        got = json.loads(json.dumps(got))
        self.checked += 1
        if self.recording:
            self.recorded[label] = got
        elif label not in self.quoted:
            self.failures.append(f"{label}: no quoted value in {EXPECTED_FILE.name}")
        elif got != self.quoted[label]:
            self.failures.append(f"{label}: recomputed {got}, quoted {self.quoted[label]}")

    def require(self, label: str, got, wanted) -> None:
        self.checked += 1
        if got != wanted:
            self.failures.append(f"{label}: found {got}, must be {wanted}")

    def table(self, title: str, rows: dict[str, Comparison], their_name: str = "reference evidence") -> None:
        print(f"\n{title}")
        print(f"  {'':5s} {'questions':>9s} {'OpenCrawl':>10s} {their_name:>18s} {'lead':>7s}   {'over questions':<17s} "
              f"{'over conversations':<19s} t over conversations")
        for key, row in rows.items():
            ours, theirs, lead, low, high, low_c, high_c, low_t, high_t = row.points()
            print(f"  {key.upper():5s} {row.questions:9d} {ours:10.2f} {theirs:18.2f} {lead:+7.2f}   "
                  f"{f'{low:+.2f} to {high:+.2f}':<17s} {f'{low_c:+.2f} to {high_c:+.2f}':<19s} {low_t:+.2f} to {high_t:+.2f}")
            self.check(f"{title} | {key}", [row.questions, *row.points()])


def stored_scores(row: dict) -> list[tuple[dict | None, float]]:
    """Every score a record holds, with the verdict stored beside it (None where only the score was kept)."""
    if "variants" in row:  # a paired replay: three answers per variant that changed the context, scores only
        return [(None, score) for variant in row["variants"].values() if variant.get("changed") for score in variant["scores"]]
    if "verdicts" in row:  # a replay of the reference evidence made on 2026-11-12: one verdict per answer run
        return list(zip(row["verdicts"], row["scores"]))
    if "scores" in row:  # an earlier replay, or a re-grading: scores only
        return [(None, score) for score in row["scores"]]
    return [(row.get("judge"), row["score"])]  # a run: one answer, one verdict


def rederived(runs: list[Path]) -> tuple[int, int, int]:
    """(scores stored, scores re-derived from their verdict, re-derived scores that differ) over the given runs."""
    stored = derived_count = wrong = 0
    for run in runs:
        for row in read_rows(run):
            for verdict, score in stored_scores(row):
                stored += 1
                derived = score_from_verdict(verdict) if isinstance(verdict, dict) else None
                if derived is not None:
                    derived_count += 1
                    wrong += abs(derived - score) > 1e-9
    return stored, derived_count, wrong


def check_integrity(report: Report) -> None:
    all_runs = sorted(records.parent for records in RESULTS.rglob("results.jsonl.gz"))
    stored, derived, wrong = rederived(all_runs)
    report.require("scores that do not follow from their verdicts", wrong, 0)
    print(f"Integrity: {stored:,} scores are stored. {derived:,} have the judge's verdict beside them and were re-derived from it; "
          f"{wrong} differ.\n  The other {stored - derived:,} keep the score only (earlier replays of the reference evidence, re-graded "
          f"answer sets, paired replays, failed questions of excluded runs).")
    sides = (("OpenCrawl", [run for prompt in ("paper", "exabase") for split in SPLITS for run in reported(prompt)(split)]),
             ("reference evidence", [run for prompt in ("paper", "exabase") for split in SPLITS for run in reference(REFERENCE[prompt][split])]),
             ("published answers", [run for split in SPLITS for run in published_answers(split)]))
    counts = {name: rederived(runs)[:2] for name, runs in sides}
    print("  In the reported comparison: " + "; ".join(f"{name} {done:,} of {total:,} scores re-derived" for name, (total, done) in counts.items()) + ".")
    report.check("scores stored and re-derived", {"all": [stored, derived], **{name: list(pair) for name, pair in counts.items()}})

    runs = failed_rows = 0
    reported_folders = {REPORTED["folder"], EARLIER["folder"], "base-fact-cards", "base", "openrouter-route", "audit-run",
                        "published-harness-run", "evidence-replays"}
    for run in all_runs:
        summary_file = run / "summary.json"
        if not summary_file.exists():  # paired replays keep their numbers in the records only
            continue
        runs += 1
        rows = read_rows(run)
        summary = json.loads(summary_file.read_text())
        report.require(f"{run.name}: questions", len(rows), summary["questions"])
        report.require(f"{run.name}: mean score", round(mean(row["score"] for row in rows), 9), round(summary["microAverage"], 9))
        if run.parent.name in reported_folders:
            split = next(part for part in run.name.split("-") if part in QUESTIONS)
            report.require(f"{run.name}: covers its length", len({row["questionId"] for row in rows}), QUESTIONS[split])
            failed_rows += sum(1 for row in rows if row.get("error"))
    report.require("failed questions in the reported runs", failed_rows, 0)
    print(f"  {runs} run summaries recomputed from their records; {failed_rows} failed questions in the reported runs.")


def headline(report: Report) -> dict[str, dict[str, Comparison]]:
    tables = {}
    for prompt in ("paper", "exabase"):
        tables[prompt] = by_split(reported(prompt), lambda split: reference(REFERENCE[prompt][split]))
        report.table(f"{PROMPT_NAME[prompt]}: reported system against the reference evidence", tables[prompt])
    report.table("Annotation-aided prompt: reported system against the reference system's published answers, re-graded",
                 by_split(reported("exabase"), published_answers), "published answers")
    return tables


def check_readme(report: Report, tables: dict[str, dict[str, Comparison]]) -> None:
    """The result table in README.md must show the recomputed numbers."""
    text = (ROOT / "README.md").read_text(encoding="utf-8").replace("−", "-")
    row = re.compile(r"^\| (100K tokens|500K tokens|1M tokens|10M tokens|All) \| [\d,]+ \| \**([\d.]+)\** \| ([\d.]+) \| "
                     r"\**([+-][\d.]+)\** \| ([+-][\d.]+) to ([+-][\d.]+) \|", re.M)
    found = [[float(match.group(i)) for i in range(2, 7)] for match in row.finditer(text)]
    recomputed = [tables[prompt][split].points()[:3] + tables[prompt][split].points()[7:]  # scores, lead, t interval
                  for prompt in ("paper", "exabase") for split in (*SPLITS, "all")]
    report.require("README.md result table", found, recomputed)
    print(f"\nREADME.md: {len(found)} rows of the result table read from the file and compared with the recomputed values.")


def everything_else(report: Report) -> None:
    for prompt in ("paper", "exabase"):
        name = PROMPT_NAME[prompt]
        report.table(f"{name}: reported system against the reference evidence replayed on the same day only",
                     by_split(reported(prompt), lambda split: reference(REPLAYS_SAME_DAY[prompt][split])))
        suffix = "paper" if prompt == "paper" else "x3"
        for label, variant in (("put in time order", "time"), ("in OpenCrawl's item format and time order", "ourfmt-time")):
            report.table(f"{name}, reference evidence {label}",
                         by_split(reported(prompt), lambda split: reference([f"replay-{split}-{variant}_{suffix}"])))
        report.table(f"{name}: without the knowledge-update questions",
                     by_split(reported(prompt), lambda split: reference(REFERENCE[prompt][split]),
                              keep=lambda pair: "_knowledge_update_" not in pair.question))
    by_ability(report)

    # The same system as first measured, on notes written from prompts whose examples came from the benchmark.
    for prompt in ("paper", "exabase"):
        report.table(f"{PROMPT_NAME[prompt]}: the rebuilt system against the system before the rebuild",
                     by_split(reported(prompt), earlier(prompt)), their_name="before the rebuild")
    leaked_questions(report)
    published_harness_run(report)
    evidence_order(report)
    for prompt in ("paper", "exabase"):
        name, first = PROMPT_NAME[prompt], lambda split: reference(REPLAYS_FIRST[prompt][split])
        report.table(f"{name}: the system before the rebuild, against the reference evidence, as first measured",
                     by_split(earlier(prompt), first))
        report.table(f"{name}: the system before the rebuild, without the six questions whose answers were examples in its note-writing prompts",
                     by_split(earlier(prompt), first, keep=lambda pair: (pair.split, pair.question) not in LEAKED))
        # One more run per length was made, before the leak was found, from the harness as first prepared for
        # publication: version 1, with the loader, scorer and model client the earlier runs used (the audit run).
        audit = lambda split: [RESULTS / "opencrawl/audit-run" / f"{split}-search-{prompt}-audit"]
        report.table(f"{name}: the system before the rebuild, its three runs and the audit run",
                     by_split(lambda split: earlier(prompt)(split) + audit(split), first))
        scores = {split: round(100 * mean(row["score"] for row in read_rows(audit(split)[0])), 2) for split in SPLITS}
        print("  audit run alone: " + "  ".join(f"{split.upper()} {score:.2f}" for split, score in scores.items()))
        report.check(f"{name}: audit run scores", scores)

    router = lambda split: opencrawl("final4or", "exabase", split, "openrouter-route")
    report.table("Answer call through the API router, annotation-aided prompt, the system before the rebuild (1M and 10M)",
                 by_split(router, lambda split: reference(REFERENCE_ROUTER[split]), splits=("1m", "10m")))
    for tag, folder, name in (("final2", "base", "Base system"), ("final3", "base-fact-cards", "Base + fact cards")):
        report.table(f"BEAM's own prompt: {name} against the reference evidence, as first measured",
                     by_split(lambda split: opencrawl(tag, "paper", split, folder), lambda split: reference(REPLAYS_FIRST["paper"][split])))
    plain_scores(report)
    ablation(report)
    conflict_notes_and_fact_cards(report)
    reference_variants(report)
    coverage_diagnostic(report)
    stored_prompts(report)


def published_harness_run(report: Report) -> None:
    """One run per length and prompt made with the harness as published (version 2), whose dataset loader, scorer
    and model client replace the third-party modules the other runs used. Not part of the reported comparison:
    it is set against the three reported runs to show that the published code gives the reported system."""
    for prompt in ("paper", "exabase"):
        name = PROMPT_NAME[prompt]
        run_of = lambda split: [RESULTS / "opencrawl/published-harness-run" / f"{split}-search-{prompt}-harness2"]
        report.table(f"{name}: the run made with the published harness against the three reported runs",
                     by_split(run_of, reported(prompt)), their_name="reported runs")
        scores = {split: round(100 * mean(row["score"] for row in read_rows(run_of(split)[0])), 2) for split in SPLITS}
        scores["all"] = round(100 * mean(row["score"] for split in SPLITS for row in read_rows(run_of(split)[0])), 2)
        print("  that run alone: " + "  ".join(f"{key.upper()} {score:.2f}" for key, score in scores.items()))
        report.check(f"{name}: scores of the run made with the published harness", scores)
        each = [round(100 * mean(row["score"] for split in SPLITS for row in read_rows(reported(prompt)(split)[index])), 2)
                for index in range(3)]  # runs a, b and c
        print("  the three reported runs, each over all questions: " + ", ".join(f"{score:.2f}" for score in each))
        report.check(f"{name}: each of the three reported runs over all questions", each)
        # The published harness also replayed the reference evidence of 100K once (results/reference/evidence-replays/
        # replay-100k-raw_harness2*). That replay is not pooled into the reference side; these two tables show what it
        # would change, and the comparison at 100K with the published harness on both sides.
        replay = f"replay-100k-raw_harness2{'_paper' if prompt == 'paper' else ''}"
        report.table(f"{name}: 100K, reported system against the reference evidence with the published harness's replay pooled in",
                     by_split(reported(prompt), lambda split: reference(REFERENCE[prompt][split] + [replay]), splits=("100k",)))
        report.table(f"{name}: 100K, the published harness on both sides (its run against its replay of the reference evidence)",
                     by_split(run_of, lambda split: reference([replay]), splits=("100k",)))


def evidence_order(report: Report) -> None:
    """The paired replay for the order of evidence (README, Limits). run.py sorted evidence by the timestamp as
    written, which is not always the order of the moments. For every stored prompt of run a of the reported system
    whose evidence was out of that order, the prompt as stored and the same prompt with its evidence sorted by
    moment were both answered and judged again (harness/reorder_replay.py)."""
    print("\nEvidence sorted by moment against the order as run (paired replay on the stored prompts of the reported system)")
    for tag, prompt in (("paper", "BEAM's own prompt"), ("exabase", "annotation-aided prompt")):
        stored, effects, clusters, again = 0, [], {}, []
        for split in SPLITS:
            original = {row["questionId"]: row["score"] for row in read_rows(RESULTS / "opencrawl" / REPORTED["folder"] / f"{split}-search-{tag}-final5-a")}
            for row in read_rows(RESULTS / "opencrawl/paired-replays" / f"order-{split}-search-{tag}-final5-a"):
                stored += 1
                if row["variants"]["as-run"]["changed"]:
                    effect = mean(row["variants"]["by-moment"]["scores"]) - mean(row["variants"]["as-run"]["scores"])
                    effects.append(effect)
                    clusters.setdefault((split, row["questionId"].split("_")[0]), []).append(effect)
                    again.append(mean(row["variants"]["as-run"]["scores"]) - original[row["questionId"]])
        low, high = interval_over_questions(effects)
        by_conversation = list(clusters.values())
        low_t, high_t = interval_t(by_conversation)
        centre = mean(mean(cluster) for cluster in by_conversation)  # what the t interval is centred on
        got = [stored, len(effects), *(round(100 * value, 2) for value in (mean(effects), low, high, centre, low_t, high_t))]
        print(f"  {prompt}: {got[1]} of {got[0]} stored prompts out of order; on those questions {got[2]:+.2f} "
              f"({got[3]:+.2f} to {got[4]:+.2f}, bootstrap over questions); mean of the per-conversation means {got[5]:+.2f} "
              f"({got[6]:+.2f} to {got[7]:+.2f}, t over {len(by_conversation)} conversations); "
              f"over all {got[0]} questions that is {got[2] * got[1] / got[0]:+.2f}")
        report.check(f"Evidence sorted by moment against the order as run, {prompt}", got)
        # The same prompts as stored, answered again now, against the answers the reported run got for them: what
        # answering on another day does by itself.
        low, high = interval_over_questions(again)
        got = [len(again), *(round(100 * value, 2) for value in (mean(again), low, high))]
        print(f"    the same prompts as run, answered again, against the reported run's answers to them: {got[1]:+.2f} ({got[2]:+.2f} to {got[3]:+.2f})")
        report.check(f"Stored prompts answered again against the reported run's answers to them, {prompt}", got)


def by_ability(report: Report) -> None:
    title = "BEAM's own prompt, by ability, all lengths: reported system against the reference evidence"
    abilities: dict[str, list[Pair]] = {}
    for split in SPLITS:
        category = {row["questionId"]: row["category"] for row in read_rows(reported("paper")(split)[0])}
        for pair in question_pairs(split, reported("paper")(split), reference(REFERENCE["paper"][split])):
            abilities.setdefault(category[pair.question], []).append(pair)
    rows = {ability: compare(pairs) for ability, pairs in abilities.items()}
    print(f"\n{title}\n  {'':26s} {'n':>5s} {'OpenCrawl':>9s} {'reference':>9s} {'lead':>7s}   {'over questions':<17s} "
          f"{'over conversations':<19s} t over conversations")
    for ability, row in sorted(rows.items(), key=lambda item: -item[1].lead):
        ours, theirs, lead, low, high, low_c, high_c, low_t, high_t = row.points()
        print(f"  {ability:26s} {row.questions:5d} {ours:9.2f} {theirs:9.2f} {lead:+7.2f}   {f'{low:+.2f} to {high:+.2f}':<17s} "
              f"{f'{low_c:+.2f} to {high_c:+.2f}':<19s} {low_t:+.2f} to {high_t:+.2f}")
        report.check(f"{title} | {ability}", [row.questions, *row.points()])


def leaked_questions(report: Report) -> None:
    """The six questions whose answers stood in the first prompts: their mean score over three runs, before and after."""
    title = "The six questions of the prompt leak: mean score before and after the rebuild"
    print(f"\n{title}\n  {'':38s} {'own prompt':>17s} {'annotation-aided':>19s}")
    for split, question in sorted(LEAKED):
        cells = []
        for prompt in ("paper", "exabase"):
            before = mean(scores_by_question(earlier(prompt)(split))[question])
            after = mean(scores_by_question(reported(prompt)(split))[question])
            cells += [round(100 * before, 1), round(100 * after, 1)]
        print(f"  {split.upper():5s} {question:32s} {cells[0]:7.1f} -> {cells[1]:5.1f} {cells[2]:9.1f} -> {cells[3]:5.1f}")
        report.check(f"{title} | {split} {question}", cells)


def run_mean(folder: str, name: str) -> float:
    return round(100 * mean(row["score"] for row in read_rows(RESULTS / folder / name)), 1)


def plain_scores(report: Report) -> None:
    title = "Scores without a comparison (paper Table 2, first rows)"
    print(f"\n{title}")
    for label, pattern in (("no memory, own prompt", "{split}-none-paper"), ("no memory, annotation-aided prompt", "{split}-none-exabase"),
                           ("BM25 baseline, own prompt", "{split}-search-paper"), ("BM25 baseline, annotation-aided prompt", "{split}-search-exabase"),
                           ("tool-using agent over BM25, free-form answer", "{split}-agent-agent")):
        cells = {split: run_mean("opencrawl/baselines", pattern.format(split=split)) for split in SPLITS
                 if (RESULTS / "opencrawl/baselines" / pattern.format(split=split)).exists()}
        print(f"  {label:46s} " + "  ".join(f"{split.upper()} {value:5.1f}" for split, value in cells.items()))
        report.check(f"{title} | {label}", cells)


def ablation(report: Report) -> None:
    title = "Ablation of the base system, annotation-aided prompt, single runs (paper Table 6)"
    steps = (("BM25 baseline", "baselines", "{split}-search-exabase"),
             ("conversation-order evidence", "development", "{split}-search-exabase-t1"),
             ("three keyword rewrites, fused", "development", "{split}-search-exabase-{rewrites}"),
             ("follow-up queries", "development", "{split}-search-exabase-t4-follow"),
             ("point-in-time retrieval", "development", "{split}-search-exabase-t5-pit"),
             ("sparse semantic retrieval", "development", "{split}-search-exabase-t9-semantic"),
             ("memory notes", "development", "{split}-search-exabase-t10-mem"),
             ("precision instructions for the note-taker", "development", "{split}-search-exabase-t13-notes2"))
    print(f"\n{title}")
    for label, folder, pattern in steps:
        cells = {}
        for split in ("100k", "500k", "1m"):
            name = pattern.format(split=split, rewrites="t2" if split == "100k" else "t3-stem")  # 500K and 1M: with stemming
            if (RESULTS / "opencrawl" / folder / name).exists():
                cells[split] = run_mean(f"opencrawl/{folder}", name)
        print(f"  {label:44s} " + "  ".join(f"{split.upper()} {value:5.1f}" for split, value in cells.items()))
        report.check(f"{title} | {label}", cells)


def conflict_notes_and_fact_cards(report: Report) -> None:
    """Paper Table 7. Paired rows: one retrieval per question, answered with and without conflict notes."""
    for tag, prompt in (("pv7p", "BEAM's own prompt"), ("pv7x", "annotation-aided prompt")):
        title = f"Conflict notes, paired replay on identical retrieval, {prompt} (paper Table 7)"
        effects, pooled = {}, []
        for split in SPLITS:
            rows = read_rows(RESULTS / "opencrawl/paired-replays" / f"pv-{split}-{tag}")
            effects[split] = [mean(row["variants"]["all"]["scores"]) - mean(row["variants"]["base"]["scores"])
                              if row["variants"]["all"]["changed"] else 0.0 for row in rows]
            pooled += effects[split]
        effects["all"] = pooled
        print(f"\n{title}")
        for key, differences in effects.items():
            low, high = interval_over_questions(differences)
            got = [len(differences), round(100 * mean(differences), 2), round(100 * low, 2), round(100 * high, 2)]
            print(f"  {key.upper():5s} {got[0]:5d} questions   {got[1]:+.2f}   {got[2]:+.2f} to {got[3]:+.2f}")
            report.check(f"{title} | {key}", got)
    # Fact cards in the paired replay that preceded their adoption: cards sharing the note budget, 1M and 10M pooled.
    differences = [mean(row["variants"]["cards0"]["scores"]) - mean(row["variants"]["base"]["scores"])
                   if row["variants"]["cards0"]["changed"] else 0.0
                   for name in ("pv-1m-pv4", "pv-10m-pv2") for row in read_rows(RESULTS / "opencrawl/paired-replays" / name)]
    low, high = interval_over_questions(differences)
    got = [len(differences), round(100 * mean(differences), 2), round(100 * low, 2), round(100 * high, 2)]
    print(f"\nFact cards, paired replay on identical retrieval, annotation-aided prompt, 1M and 10M pooled (paper Table 7)\n"
          f"  {got[0]:5d} questions   {got[1]:+.2f}   {got[2]:+.2f} to {got[3]:+.2f}")
    report.check("Fact cards, paired replay on identical retrieval, annotation-aided prompt, 1M and 10M pooled (paper Table 7)", got)
    for older, newer, folders, name in (("final2", "final3", ("base", "base-fact-cards"), "fact cards"),
                                        ("final3", "final4", ("base-fact-cards", EARLIER["folder"]), "conflict notes")):
        for prompt in ("paper", "exabase"):
            rows = by_split(lambda split: opencrawl(newer, prompt, split, folders[1]), lambda split: opencrawl(older, prompt, split, folders[0]))
            report.table(f"Effect of {name} in fresh runs, {PROMPT_NAME[prompt]}: {newer} against {older} (paper Table 7)", rows, their_name=older)


def reference_variants(report: Report) -> None:
    title = "Reference evidence at 10M, re-presented or reduced, annotation-aided prompt (paper Appendix C)"
    variants = (("as published", ["replay-10m-raw", "replay-10m-raw_more"]), ("ordered by time", ["replay-10m-time"]),
                ("our item format, rank order", ["replay-10m-ourfmt"]), ("our item format, time order", ["replay-10m-ourfmt-time"]),
                ("source messages cut to 800 characters", ["replay-10m-trunc800"]), ("no excerpts on typed extractions", ["replay-10m-noexcerpts"]),
                ("whole source messages only", ["replay-10m-sources"]), ("typed extractions only", ["replay-10m-artifacts"]))
    print(f"\n{title}")
    for label, names in variants:
        score = round(100 * mean(mean(scores) for scores in scores_by_question(reference(names)).values()), 1)
        print(f"  {label:40s} {score:5.1f}")
        report.check(f"{title} | {label}", score)


def coverage_diagnostic(report: Report) -> None:
    title = "Coverage diagnostic: questions-equivalent lost by the base system, annotation-aided prompt (paper Table 9)"
    print(f"\n{title}\n  {'':5s} {'every cited turn in the evidence':>34s} {'a cited turn missing':>22s}")
    for split in SPLITS:
        coverage = json.loads((RESULTS / "diagnostics" / f"cited-turn-coverage-{split}.json").read_text())
        scores = scores_by_question(opencrawl("final2", "exabase", split, "base"))
        lost = {True: 0.0, False: 0.0}
        for question, entry in coverage.items():
            if "error" not in entry:
                covered = set(entry["text"]) | set(entry["note"]) >= set(entry["cited"])
                lost[covered] += 1 - mean(scores[question])
        got = [round(lost[True], 1), round(lost[False], 1)]
        print(f"  {split.upper():5s} {got[0]:34.1f} {got[1]:22.1f}")
        report.check(f"{title} | {split}", got)


OWN_PROMPT_HEAD = ("You are an assistant that MUST answer questions using ONLY the information provided in the context below.\n"
                   "STRICT INSTRUCTIONS:\n1. Answer ONLY based on the provided context\n2. Do NOT use your internal knowledge\nCONTEXT:\n")
OWN_PROMPT_TAIL = ("\nQUESTION:\n{question}\nANSWER REQUIREMENTS:\n- Be direct and concise\n"
                   "- Only output the answer to the question without any explanation\nRESPONSE:")
EVIDENCE_FIELDS = {"rank", "timestamp", "role", "turn", "text"}


def moment(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def stored_prompts(report: Report) -> None:
    """Runs made with --save-context keep the exact prompt the answer model received for every question.

    Checked for every stored prompt: the evidence is a list of items that carry only rank, timestamp, role, turn and
    text, and no item carries a date after the moment the question is asked. Under BEAM's own prompt the whole
    prompt must also be the benchmark's template around that evidence and the question, with nothing added. The
    dates are the ones the harness gave each turn and note at ingest, so this checks that the time bound was
    applied, not that the dataset's dates are right.
    """
    print("\nStored answer prompts")
    for records in sorted(RESULTS.rglob("results.jsonl.gz")):
        run = records.parent
        rows = [row for row in read_rows(run) if "answerPrompt" in row]
        if not rows:
            continue
        items = other_fields = late = off_template = 0
        for row in rows:
            prompt = row["answerPrompt"]
            evidence, end = json.JSONDecoder().raw_decode(prompt, prompt.index('{"results":'))
            for item in evidence["results"]:
                items += 1
                other_fields += set(item) != EVIDENCE_FIELDS
                late += bool(row["asOf"] and item["timestamp"]) and moment(item["timestamp"]) > moment(row["asOf"])
            if "-paper-" in run.name:
                template = OWN_PROMPT_HEAD + prompt[len(OWN_PROMPT_HEAD):end] + OWN_PROMPT_TAIL.format(question=row["question"])
                off_template += prompt != template or set(evidence) != {"results"}
        print(f"  {run.name:30s} {len(rows):5d} prompts, {items:6d} evidence items: {other_fields} with other fields, "
              f"{late} dated after the question" + (f", {off_template} prompts off the template" if "-paper-" in run.name else ""))
        split = next(part for part in run.name.split("-") if part in QUESTIONS)
        report.require(f"{run.name}: stored prompts", (len(rows), other_fields, late, off_template), (QUESTIONS[split], 0, 0, 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=COVERAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="check every covered table, not only the reported comparison")
    parser.add_argument("--write-expected", action="store_true",
                        help="write results/expected.json from the records instead of comparing with it (implies --all)")
    arguments = parser.parse_args()
    quoted = json.loads(EXPECTED_FILE.read_text(encoding="utf-8")) if EXPECTED_FILE.exists() else {}
    report = Report(quoted, arguments.write_expected)
    check_integrity(report)
    tables = headline(report)
    check_readme(report, tables)
    if arguments.all or arguments.write_expected:
        everything_else(report)
    print()
    if arguments.write_expected:
        EXPECTED_FILE.write_text(json.dumps(report.recorded, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {len(report.recorded)} values to results/{EXPECTED_FILE.name}.")
    if report.failures:
        print(f"{len(report.failures)} of {report.checked} checks FAILED:")
        for failure in report.failures:
            print("  " + failure)
        return 1
    print(f"All {report.checked} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
