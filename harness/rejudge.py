"""Re-judge published answers with this harness's judge, so two systems are compared under one judge setup.

The reference system's published records carry its answer to each question. Its judge and ours are the same
model with the same prompts and scoring rules, but they ran at different times through different API routes, and
judging by a language model is not deterministic: near-identical answers can get 0.5 and 0 on the same rubric
item. Judging both systems' answers again with one judge removes that difference.

    python rejudge.py --split 500k --repeat 3 --answers $BEAM_REFERENCE_RESULTS/500k/results.jsonl \\
        --output ../results/local/published-answers-500k
    python rejudge.py --split 500k --answers ../results/opencrawl/development/500k-search-exabase-t10-mem/results.jsonl.gz \\
        --output ../results/local/rejudge-t10-mem-500k
"""

import argparse
import asyncio
import json
from pathlib import Path

import llm
import paths
import scoring
from dataset import build_conversation, load_rows


async def main(split: str, answers_path: str, output: str, repeat: int) -> None:
    rows, _ = load_rows(split)
    questions = {q.id: q for row in rows for q in build_conversation(row).questions}
    answers = {r["questionId"]: r.get("answer") for r in paths.read_jsonl(answers_path) if r.get("answer")}
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    async def one(qid, answer):
        scores = []
        for _ in range(repeat):
            score, verdicts = await scoring.score_question(questions[qid], answer)
            scores.append(score)
        return {
            "questionId": qid,
            "category": questions[qid].category,
            "scores": scores,
            "score": sum(scores) / len(scores),
        }

    rows_out = await asyncio.gather(*(one(q, a) for q, a in answers.items() if q in questions))
    with (out / "results.jsonl").open("w") as f:
        for r in rows_out:
            f.write(json.dumps(r) + "\n")
    summary = scoring.summarize(rows_out)
    summary.update(
        {"split": split, "answers": answers_path, "repeat": repeat, "judgeModel": llm.MODEL, "usage": llm.USAGE}
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"{split} {answers_path.split('/')[-2]}: {summary['microAverage']:.4f} over {summary['questions']} "
        + " ".join(f"{c[:6]}={v['mean']:.3f}" for c, v in summary["categories"].items())
    )
    await llm.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--repeat", type=int, default=1)
    a = p.parse_args()
    asyncio.run(main(a.split, a.answers, a.output, a.repeat))
