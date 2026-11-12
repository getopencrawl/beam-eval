"""Neural-sparse (doc-only) vs BM25 vs RRF hybrid evidence recall on the side index beam-sparse."""

import asyncio, sys
import httpx
from dataset import build_conversation, load_rows, probing_questions
from opencrawl_api import session_id
from retrieval_recall import evidence_ids

OS = "http://127.0.0.1:19200"


def q_bm25(q):
    return {"bool": {"should": [{"match": {"text": q}}]}}


def q_sparse(q):
    return {"neural_sparse": {"text_sparse": {"query_text": q, "analyzer": "bert-uncased"}}}


async def ids(http, session, query, k=80):
    body = {
        "size": k,
        "_source": ["eventId"],
        "query": {"bool": {"filter": [{"term": {"sessionId": session}}], "must": [query]}},
    }
    r = await http.post(f"{OS}/beam-sparse/_search", json=body)
    r.raise_for_status()
    return [h["_source"]["eventId"] for h in r.json()["hits"]["hits"]]


def rrf(lists, k=60):
    s = {}
    for l in lists:
        for i, e in enumerate(l):
            s[e] = s.get(e, 0) + 1 / (k + i + 1)
    return sorted(s, key=lambda e: -s[e])


async def main(split):
    rows, _ = load_rows(split)
    async with httpx.AsyncClient(timeout=60) as http:
        V = ("bm25", "sparse", "sum1", "sum3", "sum10")
        tot = {v: [0, 0.0, 0] for v in V}
        for row in rows:
            c = build_conversation(row)
            by_event = {m.message_id: m.turn_id for m in c.messages}
            for items in probing_questions(row).values():
                for item in items:
                    wanted = evidence_ids(item)
                    if not wanted or not item.get("question"):
                        continue
                    s = session_id(split, c.id)
                    q = item["question"]

                    def summed(w):
                        return {
                            "bool": {
                                "should": [
                                    {"match": {"text": q}},
                                    {
                                        "neural_sparse": {
                                            "text_sparse": {"query_text": q, "analyzer": "bert-uncased", "boost": w}
                                        }
                                    },
                                ]
                            }
                        }

                    lists = await asyncio.gather(
                        ids(http, s, q_bm25(q)),
                        ids(http, s, q_sparse(q)),
                        ids(http, s, summed(1)),
                        ids(http, s, summed(3)),
                        ids(http, s, summed(10)),
                    )
                    for v, l in zip(V, lists):
                        got = {by_event.get(e) for e in l[:40]} & wanted
                        tot[v][0] += bool(got)
                        tot[v][1] += len(got) / len(wanted)
                        tot[v][2] += 1
        for v, (h, r, n) in tot.items():
            print(f"{split} {v:<7} hit@40={h / n:.3f} recall@40={r / n:.3f}")


asyncio.run(main(sys.argv[1]))
