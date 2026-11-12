"""Retrieval-only diagnostic: does OpenCrawl's search, given the question verbatim, return the
turns BEAM cites as the evidence (`source_chat_ids`)? No LLM involved.

    python retrieval_recall.py --split 100k

Per question: evidence turns = all ids in source_chat_ids (abstention has none and is skipped).
Reports, at k=10 and k=40 (the MCP search page sizes: default and maximum):
  hit@k    at least one evidence turn retrieved
  recall@k fraction of evidence turns retrieved
"""

import argparse
import paths
import ast
import asyncio
import json
import re
from collections import defaultdict

from dataset import build_conversation, load_rows, probing_questions, CATEGORIES
from opencrawl_api import OpenCrawl, session_id

KS = (10, 40)


def evidence_ids(item: dict) -> set[str]:
    value = item.get("source_chat_ids")
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except Exception:
            return set(re.findall(r"\d+", value))
    found = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif v is not None:
            found.add(str(v))

    walk(value)
    return found


async def main(split: str) -> None:
    rows, _ = load_rows(split)
    opencrawl = OpenCrawl()
    stats = defaultdict(lambda: {"n": 0, **{f"hit@{k}": 0 for k in KS}, **{f"recall@{k}": 0.0 for k in KS}})
    per_question = []
    slots = asyncio.Semaphore(16)

    async def one(conversation, by_turn, category, item):
        wanted = evidence_ids(item)
        if not wanted or not item.get("question"):
            return
        async with slots:
            result = await opencrawl.search(session_id(split, conversation.id), item["question"], limit=40)
        ranked = [by_turn.get(hit["provenance"]["eventId"]) for hit in result.get("results", [])]
        record = {"conversation": conversation.id, "category": category, "evidence": sorted(wanted)}
        for k in KS:
            got = {t for t in ranked[:k] if t} & wanted
            record[f"recall@{k}"] = len(got) / len(wanted)
            record[f"hit@{k}"] = int(bool(got))
        per_question.append(record)

    tasks = []
    for row in rows:
        conversation = build_conversation(row)
        by_turn = {m.message_id: m.turn_id for m in conversation.messages}
        for category, items in probing_questions(row).items():
            for item in items:
                tasks.append(one(conversation, by_turn, category, item))
    await asyncio.gather(*tasks)
    await opencrawl.close()

    for record in per_question:
        for name in (record["category"], "ALL"):
            s = stats[name]
            s["n"] += 1
            for k in KS:
                s[f"hit@{k}"] += record[f"hit@{k}"]
                s[f"recall@{k}"] += record[f"recall@{k}"]
    table = {}
    for name in [c for c in CATEGORIES if c in stats] + ["ALL"]:
        s = stats[name]
        table[name] = {"questions": s["n"], **{key: round(s[key] / s["n"], 3) for key in s if key != "n"}}
        print(
            f"{name:<26} n={s['n']:<4} "
            + "  ".join(f"{key}={table[name][key]:.3f}" for key in table[name] if key != "questions")
        )
    out = paths.LOCAL / f"retrieval-recall-{split}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": table, "questions": per_question}, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="100k")
    asyncio.run(main(parser.parse_args().split))
