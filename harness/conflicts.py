"""Conflict notes: places where the user later denies something they reported earlier.

"I've never owned a dog" (turn 70) after "we adopted a greyhound in March" (turn 12), an invented illustration: both
cannot be true, and a memory that returns only one of them will state it as fact. This pass finds such pairs at
write time and stores a dated note naming both statements, so that any later recall about the topic sees the
conflict.

1. Candidates: fact cards (facts.py) in which the user says they have never / not yet / not done, used or had
   something.
2. For each, the product's own search (role=user, before the candidate's time) returns the user's earlier messages
   about the same thing.
3. One LLM call per candidate decides whether an earlier message reports what the later one denies. Plans, questions,
   other objects and changes of value over time are not conflicts.
4. Each confirmed conflict becomes one memory file dated at the later turn (installation conflicts-<session>), so
   point-in-time search applies.

    python conflicts.py --split 100k [--dry]
"""

import argparse, asyncio, json, os, re
import paths
import llm
from dataset import build_conversation, load_rows, utc_iso
from facts import clean
from log import log
from opencrawl_api import OpenCrawl, session_id
from run import event_time

NEGATED = re.compile(
    r"\b(never|not yet|has not|have not|hasn['’]t|haven['’]t|had not|hadn['’]t|did not|didn['’]t|does not|doesn['’]t|"
    r"do not|don['’]t|no experience|no prior|not used|not tried|not done|none|first time|new to|unfamiliar)\b",
    re.I,
)
EARLIER = 8
QUOTE = 260

VERIFY = """You check an AI assistant's memory of one user for contradictions in what the user has said about themselves.

LATER MESSAGE (turn {turn}, {date}): "{later}"
It says, among other things: {fact}

EARLIER MESSAGES from the same user:
{earlier}

Does any earlier message state or clearly presuppose something that cannot be true if that claim in the later message \
is true? The typical case: the later message says the user has never done, used, had, set up or experienced something, \
and an earlier message reports that they already did.

Do not count: plans, intentions, or questions about how to do it; a different project, tool, person or occasion; \
general knowledge; a value, schedule or decision that simply changed over time; an earlier message that is merely on \
the same topic.

Return JSON {{"conflicts": [{{"earlier_turn": <turn number of the earlier message>, "earlier_claim": "<what it \
reports, in a few words>", "later_claim": "<what the later message denies, in a few words>"}}]}}, with an empty list if \
there is none."""

# The example below is invented. The first version used the conflict of one BEAM question as its example; the conflict
# notes behind the runs tagged final4 were written with that version (docs/experiment-log.md, 2026-11-12).
RESTATE = """Two messages from the same user contradict each other. Say in a few words what each one claims about the \
point of conflict. Do not include numbers, amounts, dates, times or version numbers; name the thing, not its value.

EARLIER MESSAGE: "{earlier}"
LATER MESSAGE: "{later}"

Return JSON {{"earlier_claim": "...", "later_claim": "..."}}, each starting with a verb (for example "reported \
having adopted a greyhound" / "says they have never owned a dog")."""

RESTATE_SCHEMA = {
    "properties": {"earlier_claim": {"type": "string"}, "later_claim": {"type": "string"}},
    "required": ["earlier_claim", "later_claim"],
}

SCHEMA = {
    "properties": {
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "earlier_turn": {"type": "integer"},
                    "earlier_claim": {"type": "string"},
                    "later_claim": {"type": "string"},
                },
                "required": ["earlier_turn", "earlier_claim", "later_claim"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["conflicts"],
}


async def check(conversation, session, turn, fact, opencrawl, slots):
    message = conversation.messages[turn]
    async with slots:
        found = await opencrawl.search(
            session, fact, limit=30, match="any", before=utc_iso(event_time(message)), source="sessions", role="user"
        )
        seen, earlier = set(), []
        for hit in found.get("results") or []:
            sequence = (hit.get("provenance") or {}).get("sequence")
            if isinstance(sequence, int) and sequence < turn and sequence not in seen:
                seen.add(sequence)
                earlier.append(conversation.messages[sequence])
            if len(earlier) == EARLIER:
                break
        if not earlier:
            return []
        listing = "\n".join(f'(turn {m.ordinal}, {event_time(m).date()}): "{clean(m.content)[:600]}"' for m in earlier)
        try:
            reply = await llm.complete_json(
                VERIFY.format(
                    turn=turn,
                    date=event_time(message).date(),
                    later=clean(message.content)[:800],
                    fact=fact,
                    earlier=listing,
                ),
                SCHEMA,
                purpose="conflicts",
                reasoning="low",
            )
        except Exception as error:
            log(f"conflict check failed: {str(error)[:120]}")
            return []
    out, listed = [], {m.ordinal for m in earlier}
    for item in reply.get("conflicts", []):
        if item.get("earlier_turn") in listed:  # the model must name one of the turns it was shown
            out.append(
                {
                    "later": turn,
                    "earlier": item["earlier_turn"],
                    "earlier_claim": " ".join(str(item.get("earlier_claim") or "").split()),
                    "later_claim": " ".join(str(item.get("later_claim") or "").split()),
                }
            )
    return out


async def mine(conversation, split, opencrawl, owner, slots, args):
    session = session_id(split, conversation.id)
    checkpoint = f"{paths.LOGS}/conflicts-{session}.json"
    if os.path.exists(checkpoint):
        conflicts = json.load(open(checkpoint))
    else:
        cards = json.load(open(f"{paths.LOGS}/facts-{session}.json"))
        candidates = [(int(turn), fact) for turn, facts in cards.items() for fact in facts if NEGATED.search(fact)]
        found = await asyncio.gather(
            *(check(conversation, session, turn, fact, opencrawl, slots) for turn, fact in candidates)
        )
        conflicts, seen = [], set()
        for group in found:
            for conflict in group:
                if (conflict["later"], conflict["earlier"]) not in seen:
                    seen.add((conflict["later"], conflict["earlier"]))
                    conflicts.append(conflict)
        json.dump(conflicts, open(checkpoint, "w"))
        log(f"conflicts: {len(conflicts)} from {len(candidates)} candidate statements", conversation.id)
    by_turn: dict[int, list[dict]] = {}
    for conflict in conflicts:
        by_turn.setdefault(conflict["later"], []).append(conflict)
    if args.compact:
        return await compact_notes(conversation, session, by_turn, opencrawl, owner, slots, args)
    files = []
    for turn in sorted(by_turn):
        later = conversation.messages[turn]
        day = event_time(later).date()
        lines = []
        for conflict in by_turn[turn][:2]:
            earlier = conversation.messages[conflict["earlier"]]
            lines.append(
                f"- {day} (turn {turn}): Conflict in the user's own statements. Earlier, on {event_time(earlier).date()} "
                f'(turn {earlier.ordinal}), the user said: "{clean(earlier.content)[:QUOTE]}" ({conflict["earlier_claim"]}). '
                f'On {day} (turn {turn}) the user said: "{clean(later.content)[:QUOTE]}" ({conflict["later_claim"]}). '
                f"These cannot both be true, and the user has not said which is correct."
            )
        files.append(
            {
                "path": f"conflicts/turn-{turn:06d}.md",
                "project": conversation.title[:200],
                "modifiedAt": utc_iso(event_time(later)),
                "text": f"---\noriginSessionId: {session}\n---\n" + "\n".join(lines) + "\n",
            }
        )
    if args.dry:
        for file in files[: args.show]:
            print(file["text"].split("---\n", 2)[2].strip()[:900], "\n")
        return conflicts
    if files:
        await opencrawl._capture_call(
            "POST",
            "/api/sessions/memories",
            {
                "schemaVersion": 1,
                "installationId": f"conflicts-{session}",
                "harness": "claude-code",
                "generation": args.generation,
                "host": "beam-notes",
                "owner": owner,
                "files": files[:4000],
            },
        )
    return conflicts


async def compact_notes(conversation, session, by_turn, opencrawl, owner, slots, args):
    """Second form of the note: one short bullet per denial that names the two claims without their values and
    points at the turns. The first form quoted both messages at length; it displaced other notes and, when the
    earlier message carried a value that had since changed, put the stale value back in front of the reader."""
    checkpoint = f"{paths.LOGS}/conflicts2-{session}.json"
    restated = json.load(open(checkpoint)) if os.path.exists(checkpoint) else {}

    async def restate(turn):
        first = by_turn[turn][0]
        async with slots:
            try:
                reply = await llm.complete_json(
                    RESTATE.format(
                        earlier=clean(conversation.messages[first["earlier"]].content)[:700],
                        later=clean(conversation.messages[turn].content)[:700],
                    ),
                    RESTATE_SCHEMA,
                    purpose="conflicts",
                    reasoning="none",
                )
            except Exception as error:
                log(f"restate failed: {str(error)[:120]}")
                return
        tidy = lambda text: (lambda t: t[:1].lower() + t[1:] if t else t)(" ".join(str(text or "").split()).rstrip("."))
        restated[str(turn)] = {k: tidy(reply.get(k)) for k in ("earlier_claim", "later_claim")}

    await asyncio.gather(*(restate(turn) for turn in by_turn if str(turn) not in restated))
    json.dump(restated, open(checkpoint, "w"))
    files = []
    for turn in sorted(by_turn):
        claims = restated.get(str(turn))
        if not claims or not claims["earlier_claim"] or not claims["later_claim"]:
            continue
        later = conversation.messages[turn]
        day = event_time(later).date()
        earlier = sorted({c["earlier"] for c in by_turn[turn]})[:3]
        where = ", ".join(f"turn {t} on {event_time(conversation.messages[t]).date()}" for t in earlier)
        text = (
            f"- {day} (turn {turn}): Conflict in the user's own statements. Earlier ({where}) the user {claims['earlier_claim']}; "
            f"here (turn {turn}) the user {claims['later_claim']}. Both cannot be true, and the user has not said which is correct."
        )
        files.append(
            {
                "path": f"conflicts/turn-{turn:06d}.md",
                "project": conversation.title[:200],
                "modifiedAt": utc_iso(event_time(later)),
                "text": f"---\noriginSessionId: {session}\n---\n{text}\n",
            }
        )
    if args.dry:
        for file in files[: args.show]:
            print(file["text"].split("---\n", 2)[2].strip()[:600])
        return [c for group in by_turn.values() for c in group]
    if files:
        await opencrawl._capture_call(
            "POST",
            "/api/sessions/memories",
            {
                "schemaVersion": 1,
                "installationId": f"conflicts-{session}",
                "harness": "claude-code",
                "generation": args.generation,
                "host": "beam-notes",
                "owner": owner,
                "files": files[:4000],
            },
        )
    return [c for group in by_turn.values() for c in group]


async def main(args):
    rows, _ = load_rows(args.split)
    if args.only:
        rows = [r for r in rows if str(r["conversation_id"]) in set(args.only)]
    opencrawl = OpenCrawl()
    principal = await opencrawl.identity()
    owner = {"tenantId": principal["tenantId"], "userId": principal["userId"]}
    slots = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(
        *(mine(build_conversation(r), args.split, opencrawl, owner, slots, args) for r in rows), return_exceptions=True
    )
    total = 0
    for row, result in zip(rows, results):
        if isinstance(result, Exception):
            log(f"conflicts FAILED: {str(result)[:200]}", str(row["conversation_id"]))
        else:
            total += len(result)
    if not args.dry:
        await opencrawl.trigger_indexing()
    await opencrawl.close()
    await llm.close()
    log(f"conflicts done: {total} conflicts in {len(rows)} conversations; {json.dumps(llm.USAGE)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="short notes naming the two claims without their values (use --generation 2)",
    )
    parser.add_argument("--show", type=int, default=3)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=24)
    asyncio.run(main(parser.parse_args()))
