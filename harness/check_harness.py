"""Check that this harness reproduces what the published runs recorded.

The runs in results/ were produced by an earlier version of the harness whose dataset loader, scorer and model
client were third-party modules. Those were replaced by the implementations in this directory (README.md). This
script is the public part of the check that nothing changed with them:

    python check_harness.py              scores: every stored verdict gives its stored score under scoring.py,
                                         and every run summary follows from its records (needs scipy and httpx;
                                         nothing is downloaded or called)
    python check_harness.py --dataset    also the loader: fingerprints of every conversation as the runs ingested
                                         it, and the questions, reference answers, moments and answer prompts the
                                         runs stored (downloads BEAM on first use: about 1.3 GB, most of it 10M)
    python check_harness.py --prompts    also the prompts: exabase_prompts.py against the published adapter it
                                         was made from (needs the network)
    python check_harness.py --split 100k limits --dataset to one length

It makes no model call. It exits non-zero on any difference.
"""

import argparse
import ast
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import exabase_prompts
import paths
import scoring

FINGERPRINTS = Path(__file__).resolve().parent / "fixtures" / "dataset-fingerprints.json"
problems: list[str] = []


def problem(text: str) -> None:
    problems.append(text)
    if len(problems) <= 25:
        print("  DIFFERENT:", text)


def close(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), abs_tol=1e-9)


def report(found_before: int, checked: str) -> None:
    """One line per part: what was compared, and whether all of it agreed."""
    found = len(problems) - found_before
    print(f"{'ok       ' if not found else 'DIFFERENT'} {checked}" + (f": {found} difference(s)" if found else ""))


# --- 1. Scores from stored verdicts ---------------------------------------------------------------


def score_of(verdict: dict) -> tuple[str, float] | None:
    """The kind of a stored verdict and the score scoring.py gives it; None when there is nothing to re-derive."""
    if verdict.get("method") == "rubric" and verdict.get("items"):
        for item in verdict["items"]:
            if "rawScore" in item and scoring.nearest_step(item["rawScore"]) != item["score"]:
                return "rubric", float("nan")
        return "rubric", scoring.rubric_mean(verdict["items"])
    if verdict.get("method") == "event_ordering" and "reference" in verdict:
        if not verdict["reference"] or not verdict["answer"]:
            return "ordering", 0.0
        return "ordering", scoring.order_agreement(verdict["reference"], verdict["answer"])
    return None  # a failed question, or a replay stored without its verdict


# The rule for a judge's number, as stated in scoring.py. Every number the judge gave in the stored verdicts is
# exactly 0, 0.5 or 1, so the records do not exercise the boundaries; they are checked here on fixed values.
STEP_RULE = {0: 0.0, 0.2: 0.0, 0.2499: 0.0, 0.25: 0.5, 0.5: 0.5, 0.7499: 0.5, 0.75: 1.0, 0.9: 1.0, 1: 1.0}


def check_scores() -> None:
    before = len(problems)
    for raw, step in STEP_RULE.items():
        if scoring.nearest_step(raw) != step:
            problem(f"a judge's {raw} becomes {scoring.nearest_step(raw)}, not {step}")
    runs = summaries = 0
    verdicts = {"rubric": 0, "ordering": 0}
    for directory in paths.run_dirs():
        rows = paths.read_rows(directory)
        used = False
        for row in rows:
            pairs = []
            if isinstance(row.get("judge"), dict):
                pairs.append((row["judge"], row["score"]))
            if isinstance(row.get("verdicts"), list):
                pairs.extend(zip(row["verdicts"], row.get("scores") or []))
            for verdict, stored in pairs:
                derived = score_of(verdict)
                if derived is None:
                    continue
                verdicts[derived[0]] += 1
                used = True
                if not close(derived[1], stored):
                    problem(f"{directory.name} {row['questionId']}: stored score {stored}, scoring.py gives {derived[1]}")
        runs += used
        summary_file = directory / "summary.json"
        if rows and "category" in rows[0] and summary_file.exists():
            summary, again = json.loads(summary_file.read_text()), scoring.summarize(rows)
            if "microAverage" not in summary:
                continue
            summaries += 1
            same = close(summary["microAverage"], again["microAverage"]) and summary["questions"] == again["questions"]
            for name, ability in (summary.get("categories") or {}).items():
                mine = again["categories"].get(name)
                same = same and mine is not None and mine["questions"] == ability["questions"] and close(mine["mean"], ability["mean"])
            if not same:
                problem(f"{directory.name}: its summary does not follow from its records under scoring.summarize")
    report(before, f"scores: {verdicts['rubric']:,} stored rubric verdicts averaged and {verdicts['ordering']:,} stored event-ordering "
                   f"verdicts recomputed with scoring.py, in {runs} runs; {summaries} run summaries recomputed from their records")


# --- 2. The loader ----------------------------------------------------------------------------------


def fingerprint(conversation) -> dict:
    """What the runs ingested and asked, as two digests per conversation."""
    turns, questions = hashlib.sha256(), hashlib.sha256()
    for m in conversation.messages:
        line = [m.message_id, m.session_id, m.ordinal, m.role, m.timestamp.isoformat(), m.turn_id,
                hashlib.sha256(m.content.encode()).hexdigest()]
        turns.update((json.dumps(line, ensure_ascii=False) + "\n").encode())
    for q in conversation.questions:
        line = [q.id, q.category, q.text, q.gold_answers, q.annotations, q.as_of]
        questions.update((json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode())
    return {"messages": len(conversation.messages), "turns": turns.hexdigest(),
            "questions": len(conversation.questions), "asked": questions.hexdigest()}


def prompt_frame(question, prompt: str) -> tuple[str, str]:
    """The answer prompt of a question as the text before and after its evidence."""
    import run

    mark = "\x00evidence\x00"
    if prompt == "exabase":
        text = exabase_prompts.answer_prompt(question.text, mark, question.category, question.annotations)
    else:
        text = run.paper_prompt(question.text, mark)
    head, tail = text.split(mark)
    return head, tail


def split_of(directory: Path, summary: dict) -> str | None:
    """The conversation length a run belongs to: from its summary, else from its directory name."""
    if summary.get("split"):
        return summary["split"]
    found = re.search(r"(?:^|[-_])(100k|500k|10m|1m)(?:[-_]|$)", directory.name)
    return found.group(1) if found else None


def check_dataset(splits: list[str]) -> None:
    import dataset
    import run

    expected = json.loads(FINGERPRINTS.read_text())
    questions, moments = {}, {}
    for split in splits:
        before = len(problems)
        rows, revision = dataset.load_rows(split)
        if revision != expected[split]["revision"]:
            problem(f"{split}: dataset revision {revision}, the runs used {expected[split]['revision']}")
        conversations = [dataset.build_conversation(row) for row in rows]
        for conversation in conversations:
            if fingerprint(conversation) != expected[split]["conversations"].get(conversation.id):
                problem(f"{split} conversation {conversation.id}: turns or questions differ from what the runs used")
        questions[split] = {q.id: q for c in conversations for q in c.questions}
        moments[split] = {qid: when for c in conversations for qid, when in run.as_of_times(c).items()}
        report(before, f"dataset {split}: {len(conversations)} conversations, {sum(len(c.messages) for c in conversations):,} "
                       f"turns and {len(questions[split])} questions against the fingerprints of what the runs used")

    before = len(problems)
    runs = records = prompts = 0
    for directory in paths.run_dirs():
        summary_file = directory / "summary.json"
        summary = json.loads(summary_file.read_text()) if summary_file.exists() else {}
        split = split_of(directory, summary)
        if split not in questions:
            continue
        runs += 1
        for row in paths.read_rows(directory):
            question = questions[split].get(row.get("questionId"))
            if question is None:
                problem(f"{directory.name}: {row.get('questionId')} is not a question of {split}")
                continue
            records += 1
            if row.get("category", question.category) != question.category:
                problem(f"{directory.name} {question.id}: ability differs")
            if "question" in row and (row["question"], row.get("goldAnswers")) != (question.text, question.gold_answers):
                problem(f"{directory.name} {question.id}: question or reference answer differs")
            if row.get("asOf") and row["asOf"] != moments[split].get(question.id):
                problem(f"{directory.name} {question.id}: asked as of {row['asOf']}, the loader says {moments[split].get(question.id)}")
            if row.get("answerPrompt") and summary.get("prompt") in ("exabase", "paper"):
                prompts += 1
                head, tail = prompt_frame(question, summary["prompt"])
                stored = row["answerPrompt"]
                evidence = stored[len(head) : len(stored) - len(tail)]
                if not (stored.startswith(head) and stored.endswith(tail) and evidence.startswith('{"results":[')):
                    problem(f"{directory.name} {question.id}: the stored answer prompt is not the one this harness writes")
    report(before, f"records: {records:,} stored records in {runs} runs against the loader (question ids and, where stored, "
                   f"question, reference answer, ability and moment), and {prompts:,} stored answer prompts rebuilt around "
                   f"their evidence")


# --- 3. The prompts ---------------------------------------------------------------------------------


def published_adapter() -> str:
    import httpx

    page = httpx.get(exabase_prompts.ADAPTER_URL, follow_redirects=True, timeout=30).text.replace("\\u0026", "&")
    link = re.search(r'https://cdn\.fabric\.so/[^"\s]+?\.py\?token=[^"\s\\]+', page)
    if link is None:
        raise SystemExit(f"No download link for the adapter found on {exabase_prompts.ADAPTER_URL}")
    content = httpx.get(link.group(0), follow_redirects=True, timeout=30).content
    digest = hashlib.sha256(content).hexdigest()
    if digest != exabase_prompts.ADAPTER_SHA256:
        problem(f"the published adapter now has SHA-256 {digest}, not {exabase_prompts.ADAPTER_SHA256}")
    return content.decode("utf-8")


def functions(source: str) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}


def prompt_text(source: str, function: ast.FunctionDef) -> str:
    """The source text of the prompt a function builds: the f-string it assigns to `prompt`, or returns."""
    for node in function.body:
        value = getattr(node, "value", None)
        named_prompt = isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "prompt"
        if isinstance(value, ast.JoinedStr) and (named_prompt or isinstance(node, ast.Return)):
            return ast.get_source_segment(source, value)
    raise SystemExit(f"{function.name}: no prompt found")


def reply_fields(function: ast.FunctionDef) -> dict:
    """The fields the adapter asks the judge for: the keywords of its Schema(...) call."""
    for node in function.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "schema":
            return {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.value.keywords}
    raise SystemExit(f"{function.name}: no reply schema found")


def check_prompts() -> None:
    before = len(problems)
    theirs_source = published_adapter()
    ours_source = Path(exabase_prompts.__file__).read_text("utf-8")
    theirs, ours = functions(theirs_source), functions(ours_source)
    answer_theirs = ast.get_source_segment(theirs_source, theirs["build_rag_prompt"])
    answer_ours = ast.get_source_segment(ours_source, ours["build_rag_prompt"])
    if answer_theirs != answer_ours:
        problem("the answer-prompt method differs from the published adapter")
    for mine, published, fields in (("judge_prompt", "_rubric_item_score", exabase_prompts.JUDGE_REPLY),
                                    ("same_item_prompt", "_llm_equivalence", exabase_prompts.SAME_ITEM_REPLY)):
        if prompt_text(ours_source, ours[mine]) != prompt_text(theirs_source, theirs[published]):
            problem(f"{mine} differs from the published adapter")
        if reply_fields(theirs[published]) != fields:
            problem(f"the reply fields of {mine} differ from the published adapter")
    report(before, "prompts: the answer-prompt method, both judge prompts and their reply fields against the published adapter")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset", action="store_true", help="also check the loader (downloads BEAM on first use)")
    parser.add_argument("--prompts", action="store_true", help="also compare the prompts with ExaBase's adapter (network)")
    parser.add_argument("--split", choices=("100k", "500k", "1m", "10m"), help="with --dataset: one length only")
    arguments = parser.parse_args()
    check_scores()
    if arguments.dataset:
        check_dataset([arguments.split] if arguments.split else ["100k", "500k", "1m", "10m"])
    if arguments.prompts:
        check_prompts()
    if problems:
        print(f"FAILED: {len(problems)} difference(s)")
        sys.exit(1)
    print("everything checked agrees")


if __name__ == "__main__":
    main()
