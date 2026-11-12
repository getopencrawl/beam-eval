"""Dated state snapshots: a running, resolved state sheet per conversation, stored as OpenCrawl memories.

The BEAM paper's LIGHT scratchpad, made point-in-time. A state-keeper reads the conversation's per-turn memory
notes in order, in windows, and after each window rewrites a compact state sheet: the CURRENT value of each
important fact (with the date it was set and what it replaced), active plans and deadlines, decisions, standing
instructions and preferences. Each sheet is stored as a memory file dated at its window's last turn, so a question
asked at time t loads the latest sheet at or before t (run.py --state).

Sequential within a conversation; conversations run in parallel.

    python state.py --split 1m
"""

import argparse, asyncio, json, re
import paths
import httpx
import llm
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

OS = "http://127.0.0.1:19200"
WINDOW_CHARS = 24_000  # notes per update (~6k tokens)
PER_SNAPSHOT = 4000
TURN = re.compile(r"^- \d{4}-\d{2}-\d{2} \(turns? (\d+)(?:\s*[-–,]\s*(\d+))?\)")

UPDATE = """You maintain a STATE SHEET for an AI assistant about its long-running relationship with one user: a compact, \
always-current summary the assistant reads before every reply. Below are the current sheet and the next dated memory \
notes (in order). Rewrite the sheet so it reflects everything known after these notes.

Sections (markdown):
## Current facts: one line per important specific fact about the user, their projects, people, plans, numbers, \
versions, amounts, schedules and deadlines: "- <thing>: <current value> (since YYYY-MM-DD; was <previous value> \
until YYYY-MM-DD)". When a note changes a value, update the line and keep what it replaced. Mark items that were only \
proposed or planned as such.
## Standing instructions: how the user wants the assistant to respond (always/never/format), with dates.
## Preferences: the user's stated preferences and priorities, with dates.
## Contradictions: places where the user stated incompatible things, both sides with dates.

Keep it at most ~1,000 words: drop stale, minor or one-off details first; never drop standing instructions. \
Only include what the notes state.

CURRENT SHEET:
{sheet}

NEW NOTES:
{notes}

Return only the rewritten sheet."""


async def turn_notes(http, index, session):
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
    done = (
        await http.post(
            f"{OS}/{index}/_count",
            json={
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"corpus": "memory"}},
                            {"prefix": {"memory.installationId": f"state-{session}-"}},
                            {"term": {"memory.kind": "passage"}},
                        ]
                    }
                }
            },
        )
    ).json()["count"]
    if done:
        log(f"state: already uploaded ({done} passages)", conv.id)
        return
    lines = await turn_notes(http, index, session)
    windows, cur, size = [], [], 0
    for turn, line in lines:
        if cur and size + len(line) > WINDOW_CHARS:
            windows.append(cur)
            cur, size = [], 0
        cur.append((turn, line))
        size += len(line)
    if cur:
        windows.append(cur)
    sheet, files = "(empty)", []
    for i, window in enumerate(windows):
        async with slots:
            sheet = (
                await llm.complete_text(
                    UPDATE.format(sheet=sheet, notes="\n".join(l for _, l in window)), purpose="state", reasoning="low"
                )
            ).strip()
        last = max(t for t, _ in window)
        files.append(
            {
                "path": f"state/{i:05d}-turn-{last:06d}.md",
                "project": conv.title[:200],
                "modifiedAt": utc_iso(event_time(conv.messages[last])),
                "text": f"---\noriginSessionId: {session}\ndescription: State sheet as of turn {last}\n---\n\n# State sheet (as of turn {last})\n\n{sheet}\n",
            }
        )
        if i % 50 == 49:
            log(f"state: {i + 1}/{len(windows)} windows", conv.id)
    with open(f"{paths.LOGS}/state-{session}.json", "w") as f:  # checkpoint before upload
        json.dump(files, f)
    for k in range(0, len(files), PER_SNAPSHOT):
        await oc._capture_call(
            "POST",
            "/api/sessions/memories",
            {
                "schemaVersion": 1,
                "installationId": f"state-{session}-{k // PER_SNAPSHOT}",
                "harness": "claude-code",
                "generation": 1,
                "host": "beam-notes",
                "owner": owner,
                "files": files[k : k + PER_SNAPSHOT],
            },
        )
    log(f"state: {len(files)} dated sheets uploaded", conv.id)


async def main(split, only):
    rows, _ = load_rows(split)
    if only:
        rows = [r for r in rows if str(r["conversation_id"]) in only]
    oc = OpenCrawl()
    p = await oc.identity()
    owner = {"tenantId": p["tenantId"], "userId": p["userId"]}
    slots = asyncio.Semaphore(64)
    async with httpx.AsyncClient(timeout=300) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        results = await asyncio.gather(
            *(build(build_conversation(r), split, http, index, oc, owner, slots) for r in rows), return_exceptions=True
        )
        for r, res in zip(rows, results):
            if isinstance(res, Exception):
                log(f"state FAILED: {str(res)[:200]}", str(r["conversation_id"]))
    await oc.trigger_indexing()
    await oc.close()
    await llm.close()
    log(f"state done: {json.dumps(llm.USAGE)}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--split", required=True)
    a.add_argument("--only", nargs="*")
    args = a.parse_args()
    asyncio.run(main(args.split, set(args.only or [])))
