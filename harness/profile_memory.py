"""Always-loaded profile memory (the agent's MEMORY.md), stored through OpenCrawl's memories API.

Agents keep a short memory index loaded into every session (Claude Code's MEMORY.md; the BEAM paper's
LIGHT scratchpad). Standing instructions ("always ...") and preferences rarely share words with the later
requests they govern, so search alone cannot surface them. This consolidates a conversation's memory notes
(notes.py, read back from the realm) into one concise profile.md by map-reduce, and uploads it as its own
memory file dated at the conversation's end, linked to the session. run.py --profile loads it first.

    python profile_memory.py --split 1m
"""

import argparse
import asyncio

import httpx

import llm
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

OS = "http://127.0.0.1:19200"
CHUNK_CHARS = 90_000
GENERATION = 2  # v2: instructions and preferences only, ~350 words (v1 ~900 words crowded the evidence budget)

EXTRACT = """Below are dated memory notes from a long conversation between a user and you, their AI assistant. \
Extract, as concise markdown bullets with dates:
## Standing instructions
Every instruction the user gave about how you should respond in general or for a kind of request (formats, \
things to always or never include, styles), quoted closely.
## Preferences
The user's stated preferences, likes, dislikes, priorities and working style.
Only include what the notes state. If a later note changes an earlier one, keep the latest and say what it replaced.

Notes:
{notes}"""

MERGE = """Merge these partial profiles of one user (in chronological order) into one profile with the same two \
sections (## Standing instructions, ## Preferences). Keep every distinct standing instruction and preference, \
one short line each with its date; when a later item updates an earlier one keep only the latest. \
At most ~350 words.

{parts}"""


async def notes_text(http: httpx.AsyncClient, index: str, session: str) -> str:
    """The session's per-turn memory notes (turn_notes.py), in turn order, paged without a size cap."""
    texts, after = [], None
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
        texts += [h["_source"]["text"].split("---\n", 2)[-1] for h in hits]
        after = hits[-1]["sort"]
    return "\n".join(texts)


async def build(conversation, split, http, index, opencrawl, slots):
    session = session_id(split, conversation.id)
    text = await notes_text(http, index, session)
    chunks = [text[i : i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)] or [""]

    async def call(prompt):
        async with slots:
            return await llm.complete_text(prompt, purpose="profile", reasoning="low")

    parts = await asyncio.gather(*(call(EXTRACT.format(notes=c)) for c in chunks))
    first = True
    while len(parts) > 1 or first:  # grouped merges keep each call small; always one pass to enforce the cap
        first = False
        groups = [parts[i : i + 6] for i in range(0, len(parts), 6)]
        parts = await asyncio.gather(*(call(MERGE.format(parts="\n\n---\n\n".join(g))) for g in groups))
    end = max(event_time(m) for m in conversation.messages)
    profile = {
        "path": "profile.md",
        "project": conversation.title[:200],
        "modifiedAt": utc_iso(end),
        "text": f"---\noriginSessionId: {session}\ndescription: User profile memory - standing instructions, "
        f"preferences and key facts\n---\n\n# User profile memory\n\n{parts[0].strip()}\n",
    }
    snapshot = {
        "schemaVersion": 1,
        "installationId": f"profile-{session}",
        "harness": "claude-code",
        "generation": GENERATION,
        "host": "beam-notes",
        "owner": {"tenantId": opencrawl.principal["tenantId"], "userId": opencrawl.principal["userId"]},
        "files": [profile],
    }
    await opencrawl._capture_call("POST", "/api/sessions/memories", snapshot)
    log(f"profile uploaded ({len(chunks)} note chunks, {len(parts[0])} chars)", conversation.id)


async def main(split):
    rows, _ = load_rows(split)
    opencrawl = OpenCrawl()
    await opencrawl.identity()
    slots = asyncio.Semaphore(24)
    async with httpx.AsyncClient(timeout=120) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        await asyncio.gather(*(build(build_conversation(r), split, http, index, opencrawl, slots) for r in rows))
    await opencrawl.trigger_indexing()
    await opencrawl.close()
    await llm.close()
    log(f"profiles done: {llm.USAGE}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", default="100k")
    asyncio.run(main(p.parse_args().split))
