"""Entity-state ledger: normalized, dated fact records per conversation, stored as OpenCrawl memories.

Question-independent consolidation built at ingest from the per-turn memory notes (turn_notes.py). Each record is
one line "ENTITY — ATTRIBUTE: value [status] (date, turn N)", where status says whether it actually happened, is
planned, was only proposed, or is hypothetical. Records are stored as per-turn memory files (ledger/turn-N.md)
dated at their turn, so point-in-time search sees only records known by then. At question time run.py --ledger
expands each retrieved record's KEY into its value history (all records for that key up to the as-of time).

    python ledger.py --split 1m
"""

import argparse, asyncio, json, re
from collections import defaultdict
import httpx
import llm
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

OS = "http://127.0.0.1:19200"
BATCH = 150
PER_SNAPSHOT = 4000
TURN = re.compile(r"^- \d{4}-\d{2}-\d{2} \(turns? (\d+)(?:\s*[-–,]\s*(\d+))?\):\s*(.*)")

# The example record names in this prompt come from benchmark conversations. The ledger was tested and not adopted, and
# the prompt is left as it was run.
PROMPT = """Below are dated memory notes (each with its turn number) from a long conversation between a user and \
their AI assistant. Convert every concrete, checkable fact in them into ledger records. A record has:
- key: "<entity> — <attribute>", a short canonical noun phrase naming exactly what is measured or decided, using the \
most specific stable names (e.g. "Saturday budget review — time", "Instagram automation sprint — deadline", \
"Kadikoy apartment — monthly rent", "user — weekly writing target"); reuse the same key for the same thing;
- value: the exact value with units (number, amount, date, time, version, name, count, choice);
- turn: the note's turn number;
- status: "actual" (true or done), "planned", "proposed" (suggested, not decided), "hypothetical" (example or what-if), \
or "negated" (the user said it is not so or never happened).
Only facts with specific values; skip general advice and vague statements. Return JSON {{"records": [...]}}.

Notes:
{notes}"""


async def bullets(http, index, session):
    """All per-turn note bullets of a session: (turn, text)."""
    out, after = [], None
    while True:
        body = {
            "size": 5000,
            "_source": ["text"],
            "sort": [{"memory.path": "asc"}, {"id": "asc"}],
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"corpus": "memory"}},
                        {"term": {"memory.sourceSessionId": session}},
                        {"prefix": {"memory.installationId": "turnnotes-"}},
                    ]
                }
            },
        }
        if after:
            body["search_after"] = after
        hits = (await http.post(f"{OS}/{index}/_search", json=body)).json()["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            for line in h["_source"]["text"].splitlines():
                m = TURN.match(line)
                if m:
                    out.append((int(m.group(2) or m.group(1)), line))
        after = hits[-1]["sort"]
    return sorted(set(out))


async def build(conv, split, http, index, oc, owner, slots):
    session = session_id(split, conv.id)
    items = await bullets(http, index, session)
    batches = [items[i : i + BATCH] for i in range(0, len(items), BATCH)]

    async def extract(batch):
        async with slots:
            reply = await llm.complete_json(
                PROMPT.format(notes="\n".join(line for _, line in batch)),
                {
                    "properties": {
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "turn": {"type": "integer"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["actual", "planned", "proposed", "hypothetical", "negated"],
                                    },
                                },
                                "required": ["key", "value", "turn", "status"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["records"],
                },
                purpose="ledger",
            )
        return reply.get("records") or []

    records = [r for rs in await asyncio.gather(*(extract(b) for b in batches)) for r in rs]
    by_turn = defaultdict(list)
    for r in records:
        t = r.get("turn")
        if isinstance(t, int) and 0 <= t < len(conv.messages) and r.get("key") and r.get("value"):
            when = event_time(conv.messages[t]).date()
            by_turn[t].append(f"{r['key'].strip()}: {r['value'].strip()} [{r['status']}] ({when}, turn {t})")
    files = [
        {
            "path": f"ledger/turn-{t:06d}.md",
            "project": conv.title[:200],
            "modifiedAt": utc_iso(event_time(conv.messages[t])),
            "text": f"---\noriginSessionId: {session}\n---\n" + "\n".join(sorted(set(lines))) + "\n",
        }
        for t, lines in sorted(by_turn.items())
    ]
    for k in range(0, len(files), PER_SNAPSHOT):
        await oc._capture_call(
            "POST",
            "/api/sessions/memories",
            {
                "schemaVersion": 1,
                "installationId": f"ledger-{session}-{k // PER_SNAPSHOT}",
                "harness": "claude-code",
                "generation": 1,
                "host": "beam-notes",
                "owner": owner,
                "files": files[k : k + PER_SNAPSHOT],
            },
        )
    log(f"ledger: {len(records)} records from {len(items)} bullets in {len(files)} turn files", conv.id)


async def main(split):
    rows, _ = load_rows(split)
    oc = OpenCrawl()
    p = await oc.identity()
    owner = {"tenantId": p["tenantId"], "userId": p["userId"]}
    slots = asyncio.Semaphore(48)
    async with httpx.AsyncClient(timeout=300) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        await asyncio.gather(*(build(build_conversation(r), split, http, index, oc, owner, slots) for r in rows))
    await oc.trigger_indexing()
    await oc.close()
    await llm.close()
    log(f"ledger done: {json.dumps(llm.USAGE)}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--split", required=True)
    asyncio.run(main(a.parse_args().split))
