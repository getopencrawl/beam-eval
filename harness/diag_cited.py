"""Per-question diagnostic: are BEAM's cited evidence turns in the evidence the answer model reads?

Replays retrieval for every question of a split with the given run.py flags and records, per question, the cited
turns, which of them are in the final evidence (as a transcript passage or as a note about that turn), and their
fused rank among all candidates. Joined with scores it separates retrieval misses from reader misses.

    python diag_cited.py --split 10m --out logs/diag-10m.json -- --expand 3 --follow-up 3 ... (run.py flags)
"""

import asyncio, json, re, sys
import run as R, llm
from dataset import build_conversation, load_rows, probing_questions
from retrieval_recall import evidence_ids
from opencrawl_api import session_id

NOTE_TURN = re.compile(r"\(turns? (\d+)(?:\s*[-–,]\s*(\d+))?\)")


async def main():
    split = sys.argv[sys.argv.index("--split") + 1]
    out = sys.argv[sys.argv.index("--out") + 1]
    cats = set(sys.argv[sys.argv.index("--cats") + 1].split(",")) if "--cats" in sys.argv else None
    flags = sys.argv[sys.argv.index("--") + 1 :]
    sys.argv = ["run.py", "--split", split] + flags
    args = R.parse_arguments()
    run = R.Run(args)
    rows, _ = load_rows(split)
    slots = asyncio.Semaphore(6)
    results = {}

    async def one(row, conv, q):
        cat, idx = q.id[len(str(conv.id)) + 1 :].rsplit("_", 1)
        if cats and cat not in cats:
            return
        ids = evidence_ids(probes[conv.id][cat][int(idx)])
        cited = {m.ordinal for m in conv.messages if m.turn_id in ids}
        if not cited:
            return
        async with slots:
            R.CURRENT_AS_OF.set(run.as_of_all[conv.id].get(q.id) if run.point_in_time else None)
            try:
                session = session_id(split, conv.id)
                found = await R.expand_top(run, await R.retrieve(run, session, q.text))
                if run.deep:
                    found = await R.deepen(run, found)
                items, used = R.evidence(found, run.order)
            except Exception as e:
                results[q.id] = {"error": str(e)[:200]}
                return
        in_text, in_note = set(), set()
        for it in items:
            if it["turn"] is not None:
                in_text.add(it["turn"])
            else:
                for m in NOTE_TURN.finditer(it["text"]):
                    a = int(m.group(1))
                    b = int(m.group(2) or a)
                    in_note.update(range(a, b + 1) if b - a < 50 else [a, b])
        roles = {m.ordinal: m.role for m in conv.messages if m.ordinal in cited}
        results[q.id] = {
            "category": cat,
            "cited": sorted(cited),
            "text": sorted(cited & in_text),
            "note": sorted(cited & in_note),
            "items": len(items),
            "user_cited": sum(1 for o in cited if roles.get(o) == "user"),
        }
        if len(results) % 20 == 0:
            print(len(results), "done", flush=True)

    run.as_of_all = {}
    tasks, probes = [], {}
    for row in rows:
        conv = build_conversation(row)
        run.as_of_all[conv.id] = R.as_of_times(conv)
        probes[conv.id] = probing_questions(row)
        tasks += [one(row, conv, q) for q in conv.questions]
    await asyncio.gather(*tasks)
    json.dump(results, open(out, "w"))
    await run.opencrawl.close()
    await llm.close()
    print("DIAG_DONE", len(results))


asyncio.run(main())
