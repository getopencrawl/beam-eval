"""Date memory notes by the turn they describe, not by their window's end.

notes.py writes one memory file per ~6k-token window, dated at the window's last turn. With point-in-time
search, a question asked mid-window cannot see that window's notes (the file is dated later), while earlier
windows' notes -- often restating an older value -- remain visible. Each bullet already starts with
"- DATE (turn N):". This regroups a session's latest notes into per-turn memory files, each dated at its turn,
uploaded through the memories API (split across installations to respect the 4,096-file snapshot limit), and
retires the window-dated installation with an empty generation.

    python turn_notes.py --split 1m
"""

import argparse, asyncio, re
from collections import defaultdict
import httpx
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

OS = "http://127.0.0.1:19200"
BULLET = re.compile(r"^- \d{4}-\d{2}-\d{2} \(turns? (\d+)(?:\s*[-–,]\s*(\d+))?")
PER_SNAPSHOT = 4000


async def main(split):
    rows, _ = load_rows(split)
    oc = OpenCrawl()
    principal = await oc.identity()
    owner = {"tenantId": principal["tenantId"], "userId": principal["userId"]}
    async with httpx.AsyncClient(timeout=300) as http:
        index = (await http.get(f"{OS}/_cat/indices/opencrawl-*?h=index")).text.split()[0]
        for row in rows:
            conv = build_conversation(row)
            session = session_id(split, conv.id)
            body = {
                "size": 10000,
                "_source": ["text", "memory.path", "memory.generation", "memory.chunk", "memory.project"],
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"corpus": "memory"}},
                            {"term": {"memory.installationId": f"notes-{session}"}},
                            {"term": {"memory.kind": "passage"}},
                        ]
                    }
                },
            }
            hits = (await http.post(f"{OS}/{index}/_search", json=body)).json()["hits"]["hits"]
            latest = max(h["_source"]["memory"]["generation"] for h in hits)
            files = defaultdict(list)
            project = ""
            for h in hits:
                m = h["_source"]["memory"]
                if m["generation"] == latest:
                    files[m["path"]].append((m["chunk"], h["_source"]["text"]))
                    project = m["project"]
            by_turn: dict[int, list[str]] = defaultdict(list)
            for path, chunks in files.items():
                text = "".join(t for _, t in sorted(chunks))
                window_end = None
                for line in text.splitlines():
                    match = BULLET.match(line)
                    if match:
                        turn = int(match.group(2) or match.group(1))
                        if 0 <= turn < len(conv.messages):
                            by_turn[turn].append(line)
                            window_end = turn
                            continue
                    if line.startswith("- ") and window_end is not None:  # undated bullet: keep with the previous turn
                        by_turn[window_end].append(line)
            turns = sorted(by_turn)
            notes = [
                {
                    "path": f"notes/turn-{t:06d}.md",
                    "project": project,
                    "modifiedAt": utc_iso(event_time(conv.messages[t])),
                    "text": f"---\noriginSessionId: {session}\n---\n" + "\n".join(by_turn[t]) + "\n",
                }
                for t in turns
            ]
            parts = [notes[i : i + PER_SNAPSHOT] for i in range(0, len(notes), PER_SNAPSHOT)]
            for k, part in enumerate(parts):
                await oc._capture_call(
                    "POST",
                    "/api/sessions/memories",
                    {
                        "schemaVersion": 1,
                        "installationId": f"turnnotes-{session}-{k}",
                        "harness": "claude-code",
                        "generation": 1,
                        "host": "beam-notes",
                        "owner": owner,
                        "files": part,
                    },
                )
            await oc._capture_call(
                "POST",
                "/api/sessions/memories",
                {
                    "schemaVersion": 1,
                    "installationId": f"notes-{session}",
                    "harness": "claude-code",
                    "generation": latest + 1,
                    "host": "beam-notes",
                    "owner": owner,
                    "files": [],
                },
            )
            log(f"{len(notes)} per-turn note files in {len(parts)} snapshot(s) from {len(files)} window files", conv.id)
    await oc.trigger_indexing()
    await oc.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", required=True)
    asyncio.run(main(p.parse_args().split))
