"""Agent memory notes for BEAM conversations, stored through OpenCrawl's memories API.

In the product, Claude Code / Codex write memory files as they work and OpenCrawl captures and indexes
them beside the session transcripts. This plays that agent: it reads each conversation in windows of
~6k tokens (in order, with dates and turn numbers) and writes concise dated notes, one memory file per
window, with `originSessionId:` frontmatter linking them to the session. The prompt is generic memory
hygiene (facts, changes, preferences, standing instructions, plans, advice given); it knows nothing about
the benchmark's questions or categories. Each file's modifiedAt is its window's last turn, so
point-in-time search sees only notes written by then.

    python notes.py --split 100k
"""

import argparse
import asyncio
import json
import time

import tiktoken

import llm
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

WINDOW_TOKENS = 6000
REASONING: str | None = None  # note-taker reasoning effort (None = harness default, "none")
GENERATION = 1  # a newer generation replaces a conversation's previous notes
NOTES_MODEL: str | None = None  # the note-taker's model (default: the harness model)
_enc = tiktoken.get_encoding("o200k_base")

NOTES_PROMPT = """You are an AI assistant keeping long-term memory notes about your conversations with a user, \
so that weeks or months later you can recall exactly what was said. Below is the next part of the conversation, \
each turn labelled with its date, turn number and speaker.

Write memory notes for this part as a markdown bullet list. Each bullet is one self-contained, specific fact, \
starting with the date and turn: "- 2024-03-15 (turn 128): ...". Record, with exact names, numbers, versions, \
amounts, dates and times:
- facts about the user and their life, work, projects, people, places, possessions, experiences and history, \
including things they say they have never done or do not have;
- plans, schedules, deadlines, appointments, goals and targets;
- any change to something stated earlier ("changed X from A to B", "moved the deadline to ...");
- decisions made and the reasons;
- the user's preferences, likes, dislikes and habits;
- standing instructions the user gives about how you should respond ("always ...", "never ...", formats to use);
- the specific advice, recommendations, steps, code or explanations you gave, summarized with their key details;
- the topic the conversation focuses on in this part.
Be precise: keep exact figures and units; record totals, counts and dates exactly as stated; say clearly whether \
something actually happened, is planned, was only proposed or considered, or is hypothetical or an example; and \
attribute statements correctly to the user or to you. Do not invent anything not in the text. Write as many bullets as needed (typically 15-40).

Conversation part:
{window}"""


def windows(conversation):
    current, size = [], 0
    for message in conversation.messages:
        line = f"[{event_time(message).date()} | turn {message.ordinal} | {message.role}] {message.content}"
        cost = len(_enc.encode(line, disallowed_special=()))
        if current and size + cost > WINDOW_TOKENS:
            yield current
            current, size = [], 0
        current.append((message, line))
        size += cost
    if current:
        yield current


async def note_conversation(opencrawl: OpenCrawl, split: str, conversation, slots: asyncio.Semaphore) -> int:
    session = session_id(split, conversation.id)
    parts = list(windows(conversation))

    async def one(index, part):
        async with slots:
            text = await llm.complete_text(
                NOTES_PROMPT.format(window="\n\n".join(line for _, line in part)),
                purpose="notes",
                reasoning=REASONING,
                model=NOTES_MODEL,
            )
        last = part[-1][0]
        return {
            "path": f"notes/{event_time(last).date()}-part{index:04d}.md",
            "project": conversation.title[:200],
            "modifiedAt": utc_iso(event_time(last)),
            "text": f"---\noriginSessionId: {session}\ndescription: Memory notes, turns {part[0][0].ordinal}-{last.ordinal}\n---\n\n{text.strip()}\n",
        }

    files = await asyncio.gather(*(one(i, part) for i, part in enumerate(parts)))
    if opencrawl.principal is None:
        await opencrawl.identity()
    snapshot = {
        "schemaVersion": 1,
        "installationId": f"notes-{session}",
        "harness": "claude-code",
        "generation": GENERATION,
        "host": "beam-notes",
        "owner": {"tenantId": opencrawl.principal["tenantId"], "userId": opencrawl.principal["userId"]},
        "files": files,
    }
    await opencrawl._capture_call("POST", "/api/sessions/memories", snapshot)
    return len(files)


async def main(split: str, limit: int | None) -> None:
    rows, _ = load_rows(split)
    if limit:
        rows = rows[:limit]
    opencrawl = OpenCrawl()
    slots = asyncio.Semaphore(48)
    started = time.monotonic()

    async def run(row):
        conversation = build_conversation(row)
        count = await note_conversation(opencrawl, split, conversation, slots)
        log(f"{count} memory files uploaded ({time.monotonic() - started:.0f}s)", conversation.id)

    await asyncio.gather(*(run(row) for row in rows))
    await opencrawl.trigger_indexing()
    await opencrawl.close()
    await llm.close()
    log(f"notes done: {json.dumps(llm.USAGE)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="100k")
    parser.add_argument("--conversations", type=int)
    parser.add_argument("--reasoning", choices=("none", "low", "medium"))
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--model", help="note-taker model, e.g. gpt-5.6-sol")
    args = parser.parse_args()
    parser_model = args.model
    REASONING, GENERATION, NOTES_MODEL = args.reasoning, args.generation, parser_model
    asyncio.run(main(args.split, args.conversations))
