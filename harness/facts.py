"""Fact cards: what each of the user's messages states or takes for granted, as short dated lines.

The per-turn memory notes (notes.py, turn_notes.py) narrate the conversation: "the user asked how to re-thread the
sewing machine they bought for $40". A reader asked "what did the sewing machine cost?" then has to dig the fact out
of a narrated request, and hedges or picks an older value. A fact card states it: "Sewing machine: cost $40".
(An invented illustration, like the examples in the prompt below.)

One pass over the user's own messages only (they carry the facts; assistant replies carry the volume), in windows
of consecutive messages. Each message's facts become one memory file dated at that turn, stored through the
ordinary memories API beside the notes (installations facts-<session>-<k>), so point-in-time search applies.

    python facts.py --split 1m                      # build and upload
    python facts.py --split 10m --only 7 --turns 7400-7410 --dry   # print the cards for a few turns
"""

import argparse, asyncio, json, os, re
import paths
import llm
from dataset import build_conversation, load_rows, utc_iso
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

WINDOW_CHARS = 5000  # user text per call
WINDOW_MESSAGES = 12
MESSAGE_CHARS = 1600
PER_SNAPSHOT = 4000
CODE = re.compile(r"```.*?(```|$)", re.S)

# The examples in this prompt are invented and match no BEAM question or reference answer. The examples of the first
# version were taken from benchmark conversations and restated what five test questions ask for; the cards behind the
# runs tagged final3 and final4 were written with that version (docs/experiment-log.md, 2026-11-12).
PROMPT = """You maintain an AI assistant's long-term memory of one user. Below are consecutive messages the USER \
wrote to the assistant (the assistant's replies are omitted), each labelled with its turn number and date.

For each message, write down the facts it states or takes for granted about the user's world: the user, their work, \
projects, systems, plans, schedule, people, places, possessions, purchases, measurements, settings, versions, amounts, \
counts, dates and times, habits, preferences and decisions. One short standalone line per fact:

<what it is about>: <the fact, with its exact value>

Examples: "Choir rehearsal: now Thursday at 7 PM (moved; may clash with the beekeeping class)" - "Bicycle bell from Harwick's: paid $9" - \
"Odalys's glider exam: September 12, 2025" - "Spreadsheet add-in under evaluation: Quillon 4.2, for about 300 monthly invoices" - \
"Oolong: preferred over Earl Grey".

Rules:
- Keep names, numbers, units, versions, dates and times exactly as written.
- Facts are often mentioned in passing inside a question or request; record them ("How do I re-thread my $40 sewing \
machine?" -> "Sewing machine: cost $40").
- When a message changes something stated before (moved, now, instead of, upgraded, switched, no longer), give the new \
value and, if the message gives it, the old one.
- Say what the user did, has, uses, decided, prefers, plans or is considering, and mark plans and options under \
consideration as such.
- Name the thing a fact is about specifically enough to tell it apart from similar things (which project, which \
purchase, which person, which test).
- Do not record the request itself, general knowledge, or anything the message does not say. A message with no facts \
gets no lines.

Messages:
{messages}"""

SCHEMA = {
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"turn": {"type": "integer"}, "fact": {"type": "string"}},
                "required": ["turn", "fact"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["facts"],
}


def clean(text: str) -> str:
    text = CODE.sub("[code omitted]", text)
    text = re.sub(r"\s*->->\s*[\w,()/ .]*$", "", text.strip())  # BEAM's trailing generation marker
    return text[:MESSAGE_CHARS]


def windows(messages):
    current, size = [], 0
    for message in messages:
        text = clean(message.content)
        if current and (size + len(text) > WINDOW_CHARS or len(current) >= WINDOW_MESSAGES):
            yield current
            current, size = [], 0
        current.append((message, text))
        size += len(text)
    if current:
        yield current


async def extract(part, slots, reasoning):
    block = "\n\n".join(f"[turn {m.ordinal} | {event_time(m).date()}] {text}" for m, text in part)
    turns = {m.ordinal for m, _ in part}
    async with slots:
        for attempt in range(3):
            try:
                reply = await llm.complete_json(
                    PROMPT.format(messages=block), SCHEMA, purpose="facts", reasoning=reasoning
                )
                break
            except Exception as error:  # a malformed reply: try again, then give this window no cards
                if attempt == 2:
                    log(f"facts window failed: {str(error)[:120]}")
                    return {}
    out: dict[int, list[str]] = {}
    for item in reply.get("facts", []):
        turn, fact = item.get("turn"), " ".join(str(item.get("fact") or "").split())
        if turn in turns and fact:
            out.setdefault(turn, []).append(fact)
    return out


async def build(conversation, split, opencrawl, owner, slots, args):
    session = session_id(split, conversation.id)
    checkpoint = f"{paths.LOGS}/facts-{session}.json"
    users = [m for m in conversation.messages if m.role == "user"]
    if args.turns:
        lo, hi = (int(x) for x in args.turns.split("-"))
        users = [m for m in users if lo <= m.ordinal <= hi]
    if os.path.exists(checkpoint) and not args.turns:
        cards = {int(k): v for k, v in json.load(open(checkpoint)).items()}
    else:
        cards = {}
        for found in await asyncio.gather(*(extract(part, slots, args.reasoning) for part in windows(users))):
            cards.update(found)
        if not args.turns:
            json.dump(cards, open(checkpoint, "w"))
    if args.dry:
        for turn in sorted(cards):
            print(f"[{conversation.id} turn {turn}] {clean(conversation.messages[turn].content)[:260]!r}")
            for fact in cards[turn]:
                print(f"      - {fact}")
        return len(cards)
    files = []
    for turn in sorted(cards):
        day = event_time(conversation.messages[turn]).date()
        files.append(
            {
                "path": f"facts/turn-{turn:06d}.md",
                "project": conversation.title[:200],
                "modifiedAt": utc_iso(event_time(conversation.messages[turn])),
                "text": f"---\noriginSessionId: {session}\n---\n"
                + "\n".join(f"- {day} (turn {turn}): {fact}" for fact in cards[turn])
                + "\n",
            }
        )
    for k in range(0, len(files), PER_SNAPSHOT):
        await opencrawl._capture_call(
            "POST",
            "/api/sessions/memories",
            {
                "schemaVersion": 1,
                "installationId": f"facts-{session}-{k // PER_SNAPSHOT}",
                "harness": "claude-code",
                "generation": args.generation,
                "host": "beam-notes",
                "owner": owner,
                "files": files[k : k + PER_SNAPSHOT],
            },
        )
    log(
        f"facts: {len(files)} cards from {len(users)} user messages, {sum(len(v) for v in cards.values())} facts",
        conversation.id,
    )
    return len(files)


async def main(args):
    rows, _ = load_rows(args.split)
    if args.only:
        rows = [r for r in rows if str(r["conversation_id"]) in set(args.only)]
    opencrawl = OpenCrawl()
    principal = await opencrawl.identity()
    owner = {"tenantId": principal["tenantId"], "userId": principal["userId"]}
    slots = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(
        *(build(build_conversation(r), args.split, opencrawl, owner, slots, args) for r in rows), return_exceptions=True
    )
    for row, result in zip(rows, results):
        if isinstance(result, Exception):
            log(f"facts FAILED: {str(result)[:200]}", str(row["conversation_id"]))
    if not args.dry:
        await opencrawl.trigger_indexing()
    await opencrawl.close()
    await llm.close()
    log(f"facts done: {json.dumps(llm.USAGE)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--turns", help="a-b: only these turns (with --dry)")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--reasoning", default="low", choices=("none", "low", "medium"))
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=64)
    asyncio.run(main(parser.parse_args()))
