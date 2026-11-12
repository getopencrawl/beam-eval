"""Retrieval prototypes run directly against the self-host OpenSearch realm (loopback :19200), scored by
whether BEAM's cited evidence turns come back. LLM-free; used to choose what to port into core search.

    python proto_search.py --splits 100k 500k 1m 10m --variants base stem stem_phrase
"""

import argparse
import asyncio

import httpx

from dataset import build_conversation, load_rows, probing_questions
from opencrawl_api import session_id
from retrieval_recall import evidence_ids

OS = "http://127.0.0.1:19200"
KS = (10, 20, 40)


def text_query(variant: str, q: str) -> dict:
    if variant == "base":
        return {"match": {"text": {"query": q, "operator": "or"}}}
    if variant == "stem":
        return {"multi_match": {"query": q, "fields": ["text", "text.english"], "type": "most_fields"}}
    if variant == "english":
        return {"match": {"text.english": {"query": q}}}
    if variant == "stem_phrase":
        return {
            "bool": {
                "must": [{"multi_match": {"query": q, "fields": ["text", "text.english"], "type": "most_fields"}}],
                "should": [{"match_phrase": {"text.english": {"query": q, "slop": 6, "boost": 2}}}],
            }
        }
    if variant == "stem_mm":
        return {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["text", "text.english"],
                            "type": "most_fields",
                            "minimum_should_match": "2<30%",
                        }
                    }
                ],
                "should": [{"match_phrase": {"text.english": {"query": q, "slop": 6, "boost": 2}}}],
            }
        }
    raise ValueError(variant)


async def search(http: httpx.AsyncClient, index: str, session: str, variant: str, q: str, k: int = 40) -> list[str]:
    body = {
        "size": k,
        "_source": ["session.eventId"],
        "query": {
            "bool": {
                "filter": [{"term": {"corpus": "session"}}, {"term": {"session.sessionId": session}}],
                "must": [text_query(variant, q)],
            }
        },
    }
    r = await http.post(f"{OS}/{index}/_search", json=body)
    r.raise_for_status()
    return [h["_source"]["session"]["eventId"] for h in r.json()["hits"]["hits"]]


async def main(splits: list[str], variants: list[str]) -> None:
    async with httpx.AsyncClient(timeout=60) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        slots = asyncio.Semaphore(16)
        for split in splits:
            rows, _ = load_rows(split)
            work = []
            for row in rows:
                c = build_conversation(row)
                by_event = {m.message_id: m.turn_id for m in c.messages}
                for category, items in probing_questions(row).items():
                    for item in items:
                        wanted = evidence_ids(item)
                        if wanted and item.get("question"):
                            work.append((session_id(split, c.id), by_event, category, item["question"], wanted))
            for variant in variants:

                async def one(w):
                    session, by_event, category, q, wanted = w
                    async with slots:
                        ids = await search(http, index, session, variant, q)
                    turns = [by_event.get(e) for e in ids]
                    return category, {
                        k: (bool(set(turns[:k]) & wanted), len(set(turns[:k]) & wanted) / len(wanted)) for k in KS
                    }

                results = await asyncio.gather(*(one(w) for w in work))
                total = {k: [0, 0.0] for k in KS}
                for _, r in results:
                    for k in KS:
                        total[k][0] += r[k][0]
                        total[k][1] += r[k][1]
                n = len(results)
                print(
                    f"{split:<5} {variant:<12} "
                    + "  ".join(f"hit@{k}={total[k][0] / n:.3f} rec@{k}={total[k][1] / n:.3f}" for k in KS),
                    flush=True,
                )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--splits", nargs="+", default=["100k"])
    p.add_argument("--variants", nargs="+", default=["base"])
    a = p.parse_args()
    asyncio.run(main(a.splits, a.variants))
