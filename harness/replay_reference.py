"""Answer BEAM questions from the reference system's *published* evidence with this harness's answer call and
judge: the reference side of the controlled comparison. The variants re-present or ablate that evidence to learn
which of its properties carry the score. Nothing here feeds OpenCrawl's own answers.

The published records are not part of this repository (docs/reference-system.md). With a copy of them, one
results.jsonl per split, each record holding the question id and, under `recall`, the evidence as that system's
API returned it:
    export BEAM_REFERENCE_RESULTS=/path/to/those/records
    python replay_reference.py --split 1m --variant raw --repeat 3 --tag _x3
    python replay_reference.py --split 1m --variant raw --repeat 2 --prompt paper --tag _paper
Variants:
  raw            the published evidence object exactly as its harness passed it
  time           same results, sorted by time instead of rank
  sources        only whole source messages (drop typed extractions)
  artifacts      only typed extractions
  trunc800       source messages cut to their first 800 characters
  ourfmt         same content in OpenCrawl's evidence item shape (rank, timestamp, role, turn, text), rank order
  ourfmt-time    ourfmt, time order
  noexcerpts     drop the per-source excerpts of typed extractions (keep their one-line content)

"Sorted by time" is by the timestamp as written. The published timestamps drop trailing zeros of the fraction of
a second, so turns of one session do not all sort in the order they were said (README, Limits); run.py orders
OpenCrawl's own evidence the same way.

Nothing is written until every question is done, and a call that fails stops the script.
"""

import argparse, asyncio, json
import exabase_prompts, llm, paths, scoring
from datetime import datetime, timezone

from dataset import build_conversation, load_rows, utc_iso

# The BEAM paper's own answer prompt (Listing 44), as in run.py's paper_prompt: no dataset annotations.
PAPER_PROMPT = """You are an assistant that MUST answer questions using ONLY the information provided in the context below.
STRICT INSTRUCTIONS:
1. Answer ONLY based on the provided context
2. Do NOT use your internal knowledge
CONTEXT:
{context}
QUESTION:
{question}
ANSWER REQUIREMENTS:
- Be direct and concise
- Only output the answer to the question without any explanation
RESPONSE:"""


def transform(recall: dict, variant: str) -> str:
    results = list(recall.get("results") or [])
    kind = lambda x: (x.get("artifact") or {}).get("kind")
    if variant == "time":
        results.sort(key=lambda x: x.get("occurredAt") or "")
    elif variant == "sources":
        results = [x for x in results if kind(x) == "source"]
    elif variant == "artifacts":
        results = [x for x in results if kind(x) != "source"]
    elif variant == "trunc800":
        results = [{**x, "content": x["content"][:800]} if kind(x) == "source" else x for x in results]
    elif variant == "noexcerpts":
        results = [
            {**x, "sources": [{k: v for k, v in s.items() if k != "excerpts"} for s in x.get("sources") or []]}
            for x in results
        ]
    if variant.startswith("ourfmt"):
        items = []
        for x in results:
            src = (x.get("sources") or [{}])[0]
            role = (src.get("metadata") or {}).get("role") if kind(x) == "source" else "memory note"
            items.append(
                {
                    "rank": x.get("rank"),
                    "timestamp": x.get("occurredAt"),
                    "role": role,
                    "turn": src.get("sourceId") if kind(x) == "source" else None,
                    "text": x.get("content") or "",
                }
            )
        if variant == "ourfmt-time":
            items.sort(key=lambda i: i["timestamp"] or "")
        return json.dumps({"results": items}, ensure_ascii=False, separators=(",", ":"))
    return json.dumps({**recall, "results": results}, ensure_ascii=False, separators=(",", ":"))


async def main(
    split: str, variant: str, repeat: int, reasoning: str | None = None, tag: str = "", prompt: str = "exabase"
) -> None:
    rows, revision = load_rows(split)
    questions = {q.id: q for row in rows for q in build_conversation(row).questions}
    published = paths.read_jsonl(paths.reference_results(split))
    out = paths.new_run_dir(f"replay-{split}-{variant}{tag}")
    out.mkdir(parents=True, exist_ok=True)

    async def one(r):
        q = questions[r["questionId"]]
        context = transform(r["recall"], variant)
        scores, answers, verdicts = [], [], []
        for _ in range(repeat):
            text = (
                exabase_prompts.answer_prompt(q.text, context, q.category, q.annotations)
                if prompt == "exabase"
                else PAPER_PROMPT.format(context=context, question=q.text)
            )
            answer = (await llm.complete_text(text, reasoning=reasoning)).strip()
            score, verdict = await scoring.score_question(q, answer)
            scores.append(score)
            answers.append(answer)
            verdicts.append(verdict)
        return {
            "questionId": q.id,
            "category": q.category,
            "score": sum(scores) / len(scores),
            "scores": scores,
            "answer": answers[-1],
            "answers": answers,
            "verdicts": verdicts,  # one per answer run, in the order of "scores"
        }

    done = await asyncio.gather(*(one(r) for r in published if r.get("recall")))
    with (out / "results.jsonl").open("w") as f:
        for r in done:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = scoring.summarize(done)
    summary.update(
        {
            "split": split,
            "variant": variant,
            "repeat": repeat,
            "answerReasoning": reasoning or llm.REASONING_EFFORT,
            "prompt": prompt,
            "answerModel": llm.MODEL,
            "judgeModel": llm.MODEL,
            "datasetRevision": revision,
            "finishedAt": utc_iso(datetime.now(timezone.utc)),
            "usage": llm.USAGE,
        }
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"{split} {variant + tag:<18} {100 * summary['microAverage']:.2f}  "
        + " ".join(f"{c[:6]}={100 * v['mean']:.0f}" for c, v in summary["categories"].items()),
        flush=True,
    )
    await llm.close()


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--split", required=True)
    a.add_argument("--variant", default="raw")
    a.add_argument("--repeat", type=int, default=1)
    a.add_argument("--reasoning")
    a.add_argument("--tag", default="")
    a.add_argument("--prompt", choices=("exabase", "paper"), default="exabase")
    args = a.parse_args()
    asyncio.run(main(args.split, args.variant, args.repeat, args.reasoning, args.tag, args.prompt))
