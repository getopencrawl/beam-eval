"""Does it matter that some evidence was shown out of order? A paired replay for a flaw in run.py.

run.py sorts evidence by the timestamp as written, not as a moment. A timestamp on a whole second is written
without a fraction and sorts after the others of its second, so the first turn of a conversation (and turns 1000,
2000, ...) can follow turns that came after it. This script takes the prompts a run stored (--save-context), finds
those whose evidence is not in the order of the moments themselves, and answers both versions of each: the prompt
as stored, and the same prompt with the same evidence sorted by moment, ties broken by turn number as run.py
breaks them. Nothing else in the prompt changes. Both versions are answered and judged --repeat times now, with
the same answer call and judge, so that the two arms differ only in the order.

    python reorder_replay.py --run 10m-search-paper-final5-a --repeat 2

Writes results/local/order-<run>/results.jsonl in the form of the other paired replays: per question, the
variants "as-run" and "by-moment" with their scores and answers. The judge's verdicts are not kept, so a verdict
the judge failed to give would count 0 without a trace in the record; the log shows the retries that precede one.
A question whose stored evidence is already in order is recorded as unchanged and not answered again. Records are
appended as questions finish; run the command again and it continues.
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone

import llm
import paths
import scoring
from dataset import build_conversation, load_rows

ARMS = ("as-run", "by-moment")
EARLIEST = datetime.min.replace(tzinfo=timezone.utc)


def moment(timestamp: str | None) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else EARLIEST


def by_moment(items: list[dict]) -> list[dict]:
    """The items as run.py orders them under --order time, but comparing moments instead of strings: a pinned
    profile first, the user's most recent messages last, everything else by moment and then turn."""
    pinned = [item for item in items if item["role"] == "profile memory"]
    recent = [item for item in items if item["role"] == "user (most recent messages)"]
    rest = [item for item in items if item not in pinned and item not in recent]
    rest.sort(key=lambda item: (moment(item["timestamp"]), item["turn"] if item["turn"] is not None else -1))
    return pinned + rest + recent


def reordered(prompt: str) -> str:
    """The stored prompt with its evidence in the order of the moments. Returns the prompt itself when that is the
    order it already has."""
    start = prompt.index('{"results":[')
    evidence, end = json.JSONDecoder().raw_decode(prompt, start)
    as_written = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    if as_written != prompt[start:end]:
        raise SystemExit("A stored prompt does not hold its evidence in the form run.py writes it")
    fixed = json.dumps({**evidence, "results": by_moment(evidence["results"])}, ensure_ascii=False, separators=(",", ":"))
    return prompt[:start] + fixed + prompt[end:]


async def main(run_name: str, repeat: int, limit: int | None) -> None:
    records = [record for record in paths.read_rows(run_name) if record.get("answerPrompt")]
    if not records:
        raise SystemExit(f"{run_name} stores no prompts; use a run made with run.py --save-context")
    records = records[:limit] if limit else records
    split = run_name.split("-")[0]
    rows, _ = load_rows(split)
    questions = {q.id: q for row in rows for q in build_conversation(row).questions}
    out = paths.new_run_dir(f"order-{run_name}")
    out.mkdir(parents=True, exist_ok=True)
    results = out / "results.jsonl"
    done = {row["questionId"] for row in paths.read_jsonl(results)} if results.exists() else set()
    writing = asyncio.Lock()

    async def one(record: dict) -> None:
        question = questions[record["questionId"]]
        prompts = {"as-run": record["answerPrompt"], "by-moment": reordered(record["answerPrompt"])}
        changed = prompts["as-run"] != prompts["by-moment"]
        variants = {arm: {"changed": changed, "scores": [], "answers": []} for arm in ARMS}
        if changed:
            for _ in range(repeat):
                for arm in ARMS:
                    answer = (await llm.complete_text(prompts[arm])).strip()
                    score, _ = await scoring.score_question(question, answer)
                    variants[arm]["scores"].append(score)
                    variants[arm]["answers"].append(answer)
        line = json.dumps({"questionId": question.id, "category": question.category, "variants": variants}, ensure_ascii=False)
        async with writing:
            with results.open("a", encoding="utf-8") as file:
                file.write(line + "\n")

    try:
        await asyncio.gather(*(one(record) for record in records if record["questionId"] not in done))
    finally:
        await llm.close()

    stored = paths.read_jsonl(results)
    effects = [
        sum(row["variants"]["by-moment"]["scores"]) / len(row["variants"]["by-moment"]["scores"])
        - sum(row["variants"]["as-run"]["scores"]) / len(row["variants"]["as-run"]["scores"])
        for row in stored
        if row["variants"]["as-run"]["changed"]
    ]
    effect = 100 * sum(effects) / len(effects) if effects else 0.0
    print(f"{run_name}: {len(effects)} of {len(stored)} stored prompts were out of order; by moment minus as run, "
          f"on those questions: {effect:+.2f} points; written to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", required=True, help="name of a run that stores prompts, e.g. 10m-search-paper-final5-a")
    parser.add_argument("--repeat", type=int, default=2, help="answer runs per version of a prompt")
    parser.add_argument("--limit", type=int, help="only the first N stored prompts")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.run, arguments.repeat, arguments.limit))
