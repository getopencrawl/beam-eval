"""Evidence coverage of role-restricted retrieval, straight against the realm (same query shape as core's
semantic textQuery): unrestricted top-40 vs user-only top-40 vs a fused 40 (RRF)."""

import asyncio, sys, collections
import httpx
from dataset import build_conversation, load_rows, probing_questions
from opencrawl_api import session_id
from retrieval_recall import evidence_ids
from run import as_of_times

OS = "http://127.0.0.1:19200"


def text_query(q):
    return {
        "bool": {
            "should": [
                {"match": {"text": {"query": q, "operator": "or"}}},
                {"match": {"text.english": {"query": q, "operator": "or"}}},
                {"neural_sparse": {"textSparse": {"query_text": q, "analyzer": "bert-uncased", "boost": 10}}},
            ],
            "minimum_should_match": 1,
        }
    }


async def search(http, index, session, q, before, role=None, k=40):
    filt = [
        {"term": {"corpus": "session"}},
        {"term": {"session.sessionId": session}},
        {"range": {"timestamp": {"lte": before}}},
    ]
    if role:
        filt.append({"term": {"session.role": role}})
    r = await http.post(
        f"{OS}/{index}/_search",
        json={"size": k, "_source": ["session.eventId"], "query": {"bool": {"filter": filt, "must": [text_query(q)]}}},
    )
    r.raise_for_status()
    return [h["_source"]["session"]["eventId"] for h in r.json()["hits"]["hits"]]


def rrf(lists, k=60):
    s = {}
    for l in lists:
        for i, e in enumerate(l):
            s[e] = s.get(e, 0) + 1 / (k + i + 1)
    return sorted(s, key=lambda e: -s[e])


async def main(split):
    rows, _ = load_rows(split)
    async with httpx.AsyncClient(timeout=120) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        sem = asyncio.Semaphore(12)
        stats = collections.defaultdict(lambda: collections.defaultdict(float))

        async def one(conv, by_event, asof, cat, item):
            wanted = evidence_ids(item)
            if not wanted or not item.get("question"):
                return
            sess = session_id(split, conv.id)
            async with sem:
                a, u = await asyncio.gather(
                    search(http, index, sess, item["question"], asof),
                    search(http, index, sess, item["question"], asof, "user"),
                )
            for name, l in (("all", a), ("user", u), ("fused", rrf([a, u])[:40])):
                got = {by_event.get(e) for e in dict.fromkeys(l)} & wanted
                for key in (cat, "ALL"):
                    stats[key][name + "_rec"] += len(got) / len(wanted)
                    stats[key][name + "_full"] += len(got) == len(wanted)
            for key in (cat, "ALL"):
                stats[key]["n"] += 1

        tasks = []
        for row in rows:
            conv = build_conversation(row)
            by_event = {m.message_id: m.turn_id for m in conv.messages}
            asof = as_of_times(conv)
            for cat, items in probing_questions(row).items():
                for i, item in enumerate(items):
                    tasks.append(one(conv, by_event, asof.get(f"{conv.id}_{cat}_{i}"), cat, item))
        await asyncio.gather(*tasks)
        print(split, "(question as query, top 40 passages; recall of cited turns / all cited turns found)")
        for key in sorted(stats, key=lambda k: (k == "ALL", k)):
            s = stats[key]
            n = s["n"]
            print(
                f"  {key:<26} n={int(n):<4} all {s['all_rec'] / n:.2f}/{s['all_full'] / n:.2f}  user-only {s['user_rec'] / n:.2f}/{s['user_full'] / n:.2f}  fused {s['fused_rec'] / n:.2f}/{s['fused_full'] / n:.2f}"
            )


asyncio.run(main(sys.argv[1]))
