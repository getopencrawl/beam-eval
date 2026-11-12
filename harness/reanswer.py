"""Answer and judge again from the prompts a run stored: OpenCrawl's side of the comparison, checkable with an API
key and without OpenCrawl.

A run made with --save-context stores, for every question, the complete prompt the answer model received (run `a`
of the reported system at each length and prompt does, and so do the runs under results/opencrawl/audit-run/). This
sends each stored prompt to the answer model again, judges the answer with the same judge prompts and rules, and
writes a new run to results/local/. Nothing is written until every question is done, and a call that fails stops
the script. replay_reference.py does the same for the reference system's published evidence, but needs that
system's records, which are not in this repository.

    python reanswer.py --run 10m-search-paper-final5-a --repeat 2
    python reanswer.py --run 10m-search-paper-final5-a --limit 20     # a quick check on the first 20 questions
"""

import argparse
import asyncio
import json

import llm
import paths
import scoring
from dataset import build_conversation, load_rows


async def main(run_name: str, repeat: int, limit: int | None, tag: str) -> None:
    records = [record for record in paths.read_rows(run_name) if record.get("answerPrompt")]
    if not records:
        raise SystemExit(f"{run_name} stores no prompts; use a run made with run.py --save-context")
    records = records[:limit] if limit else records
    split = run_name.split("-")[0]
    rows, _ = load_rows(split)
    questions = {q.id: q for row in rows for q in build_conversation(row).questions}
    out = paths.new_run_dir(f"reanswer-{run_name}" + (f"-{tag}" if tag else ""))
    out.mkdir(parents=True, exist_ok=True)

    async def one(record: dict) -> dict:
        question = questions[record["questionId"]]
        scores, answer = [], ""
        for _ in range(repeat):
            answer = (await llm.complete_text(record["answerPrompt"])).strip()
            score, _ = await scoring.score_question(question, answer)
            scores.append(score)
        return {"questionId": question.id, "category": question.category, "score": sum(scores) / len(scores),
                "scores": scores, "answer": answer, "storedScore": record["score"]}

    done = await asyncio.gather(*(one(record) for record in records))
    with (out / "results.jsonl").open("w") as file:
        for row in done:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = scoring.summarize(done)
    summary.update({"split": split, "source": run_name, "repeat": repeat, "answerModel": llm.MODEL, "judgeModel": llm.MODEL,
                    "usage": llm.USAGE})
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    stored = sum(record["score"] for record in records) / len(records)
    print(f"{run_name}: {len(done)} questions, answered again {100 * summary['microAverage']:.2f}, stored run {100 * stored:.2f}; "
          f"written to {out}")
    await llm.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", required=True, help="name of a run that stores prompts, e.g. 10m-search-paper-audit")
    parser.add_argument("--repeat", type=int, default=1, help="answer runs per question")
    parser.add_argument("--limit", type=int, help="only the first N questions")
    parser.add_argument("--tag", default="", help="suffix for the new run's name")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.run, arguments.repeat, arguments.limit, arguments.tag))
