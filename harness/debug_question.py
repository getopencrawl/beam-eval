"""Replay one question through the retrieval pipeline and print the evidence the answer model would read.

    python debug_question.py --split 10m --qid 7_knowledge_update_0 -- --expand 3 --follow-up 3 --order time \
        --point-in-time --memories --context-tokens 10467 --deep 12 --deep-whole --memory-share 0.2
"""

import asyncio, json, sys
import run as R
import llm
from dataset import build_conversation, load_rows, probing_questions
from retrieval_recall import evidence_ids
from opencrawl_api import session_id


async def main():
    split = sys.argv[sys.argv.index("--split") + 1]
    qid = sys.argv[sys.argv.index("--qid") + 1]
    answer = "--answer" in sys.argv
    flags = sys.argv[sys.argv.index("--") + 1 :]
    sys.argv = ["run.py", "--split", split] + flags
    args = R.parse_arguments()
    run = R.Run(args)
    rows, _ = load_rows(split)
    conv_id = qid.split("_")[0]
    row = next(r for r in rows if str(r["conversation_id"]) == conv_id)
    conv = build_conversation(row)
    run.as_of = R.as_of_times(conv)
    q = next(x for x in conv.questions if x.id == qid)
    cat, idx = qid[len(conv_id) + 1 :].rsplit("_", 1)
    item = probing_questions(row)[cat][int(idx)]
    ids = evidence_ids(item)
    cited = {m.ordinal for m in conv.messages if m.turn_id in ids}
    session = session_id(split, conv.id)
    R.CURRENT_AS_OF.set(run.as_of.get(q.id) if run.point_in_time else None)
    found = await R.expand_top(run, await R.retrieve(run, session, q.text))
    if run.deep:
        found = await R.deepen(run, found)
    if run.recent:
        found = await R.with_recent(run, session, found)
    if run.state:
        found = await R.with_state(run, session, found)
    if run.curate:
        found = await R.curate_evidence(run, q.text, found)
    items, used = R.evidence(found, run.order)
    print(
        f"Q: {q.text}\nGOLD: {q.gold_answers}\nasOf: {R.CURRENT_AS_OF.get()} | cited turns: {sorted(cited)} | queries: {found.get('queries')}\n{len(items)} items, {used} budget tokens\n"
    )
    for it in items:
        mark = "**CITED**" if it["turn"] in cited else ""
        print(
            f"[{str(it['timestamp'])[:10]} turn {it['turn']} {it['role']}] ({len(it['text'])} chars) {mark} {it['text'][: int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 260]!r}"
        )
    if answer:
        import exabase_prompts

        context = json.dumps({"results": items}, ensure_ascii=False, separators=(",", ":"))
        print(
            "\nANSWER:",
            (
                await llm.complete_text(exabase_prompts.answer_prompt(q.text, context, q.category, q.annotations))
            ).strip(),
        )
    await run.opencrawl.close()
    await llm.close()


asyncio.run(main())
