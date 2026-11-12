"""Paired presentation experiments: retrieve each question's evidence once, then answer it under several
presentations of that same evidence and judge each answer.

Run-to-run noise in retrieval (LLM query rewrites) is ~1 point at 700 questions, which hides presentation effects
of a few tenths. Holding the evidence fixed and changing only how it is shown removes that noise; a question whose
context is identical under a variant reuses the base answers, so it contributes exactly zero difference.

    python replay_variants.py --split 10m --variants lint,qualify,rankfirst --repeat 3 --tag pv1 -- <run.py flags>

Variants (none uses the question's category, gold or rubric). Presentation variants act on the items the reader
sees; design variants rebuild the evidence from the same search results under another budget rule. Several can be
combined with "+", e.g. cards8+lint.
  base       the configuration's evidence as is (or, with --base nocards, the same search results without fact cards)
  nocards    design: fact cards left out, their budget goes back to notes and passages
  noconf     design: conflict notes left out (use as --base noconf with variant "all" to measure conflict notes)
  all        design: everything the search returned, under the configuration's own budget rule
  cardsN     design: fact cards as their own layer, up to N% of the budget (cards8 = 8%); narrative notes keep
             --memory-share
  lint       memory notes without clauses that assert absence ("... was not provided", "did not specify ...")
  qualify    the same clauses kept, marked as scoped to the message they describe
  rankfirst  the five best-ranked items first, then everything in conversation order
  rolefocus  design: one small LLM call reads the question alone and says whose words hold the answer (the user's,
             the assistant's, or both). For a question about what the user said, did or was told, the evidence is
             built from the user's messages and the memory notes only; otherwise unchanged.
  timeline   design: one small LLM call names the question's subject (a person, project or thing); the product's
             search returns the fact cards about it oldest-first (order=oldest, all terms); an evenly spaced subset
             becomes a layer of at most 10% of the evidence, so the reader sees how the subject developed in order
  legend     the context starts with a one-paragraph description of the fields (who wrote each kind of entry)
  roles      each entry's role spelled out: "user (their own message)", "assistant (its reply: advice, examples,
             proposals)", "memory note (summary of a turn)"
  notesfirst memory notes first (conversation order), then the transcript passages (conversation order)
"""

import asyncio, json, os, random, re, statistics as st, sys
import exabase_prompts, llm, paths, scoring
import run as R
from dataset import build_conversation, load_rows
from log import log
from opencrawl_api import session_id

ABSENCE = re.compile(
    r"\b(?:(?:was|were|is|are|been|being)\s+not\s+(?:provided|specified|stated|given|included|mentioned|confirmed|identified|disclosed|shared|supplied|available|known)"
    r"|(?:did|does|do)\s+not\s+(?:specify|provide|state|mention|say|give|include|identify|indicate|name|share|clarify)"
    r"|(?:could|can)\s*not\s+be\s+(?:determined|calculated|computed|confirmed|verified)"
    r"|(?:is|are|was|were|remains?|remained)\s+(?:unknown|unclear|unspecified)"
    r"|no\s+(?:specific\s+|exact\s+|actual\s+)?[\w\s,'’/-]{0,60}?(?:was|were|is|are)\s+(?:provided|given|stated|specified|mentioned|included|available))\b",
    re.I,
)
SEGMENT = re.compile(r"(?<=[;.])\s+(?=\S)")
BULLET = re.compile(r"^(- \d{4}-\d{2}-\d{2} \(turns? [^)]*\):\s*)(.*)$")
SCOPE = " [true of that message only]"
LEGEND = (
    "Entries from the user's chat history with an AI assistant, in conversation order. role \"user\": the user's own "
    'message. role "assistant": the assistant\'s reply to the user (its advice, examples and proposals; not a record '
    'of what the user did or decided). role "memory note": a dated note summarising one turn.'
)


def _absent(segment: str) -> bool:
    """A clause in which the note-taker says something was missing; a report of what the assistant said is kept."""
    match = ABSENCE.search(segment)
    return bool(match) and not re.search(r"\bassistant\b", segment[: match.start()], re.I)


def lint_note(text: str, qualify: bool) -> str:
    out = []
    for line in text.splitlines():
        match = BULLET.match(line)
        if not match:
            out.append(line)
            continue
        prefix, body = match.groups()
        kept = []
        for segment in SEGMENT.split(body):
            if _absent(segment):
                if qualify:
                    core = segment.rstrip()
                    end = core[-1] if core and core[-1] in ";." else ""
                    kept.append((core[:-1] if end else core) + SCOPE + end)
            else:
                kept.append(segment)
        body = " ".join(kept).strip()
        if body:
            if body.endswith(";"):
                body = body[:-1] + "."
            out.append(prefix + body)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


ABOUT_PROMPT = """A user is asking their AI assistant a question about their own past conversations with it. \
Whose words would hold the answer?
- "user": something the user stated: facts about their life, work and projects, events, numbers, dates, plans, \
decisions, preferences, or what other people told them.
- "assistant": something the assistant said: its advice, recommendations, explanations, examples, or plans it proposed.
- "both": the answer needs both, or it is unclear.
Return JSON {{"about": "user" | "assistant" | "both"}}.

Question: {question}"""


# The three example subjects below come from benchmark conversations. This variant was tested and not adopted, and the
# prompt is left as it was run.
SUBJECT_PROMPT = """A user asks their AI assistant a question about their past conversations. Name the main person, \
project or thing the question is about, in one to three words as they would appear in the user's own messages \
(for example "Elizabeth", "wedding budget", "Flask app"). Return JSON {{"subject": "..."}}; an empty string if the \
question has no single subject.

Question: {question}"""
TIMELINE_SHARE = 0.10


async def timeline_hits(run, session: str, question: str) -> list[dict]:
    reply = await llm.complete_json(
        SUBJECT_PROMPT.format(question=question),
        {"properties": {"subject": {"type": "string"}}, "required": ["subject"]},
        purpose="subject",
    )
    subject = " ".join(str(reply.get("subject") or "").split())
    if not subject:
        return []
    hits, cursor = [], None
    for _ in range(3):  # up to 120 memory passages about the subject, oldest first
        page = await run.opencrawl.search(
            session,
            subject,
            limit=40,
            match="all",
            before=R.CURRENT_AS_OF.get(),
            source="memories",
            order="oldest",
            cursor=cursor,
        )
        if "error" in page:
            break
        hits += [h for h in page.get("results") or [] if R.is_fact_card(h)]
        cursor = page.get("next")
        if not cursor:
            break
    # Keep only the lines of each card that mention the subject, then the largest evenly spaced subset that fits.
    words = [w.lower() for w in re.findall(r"\w+", subject) if len(w) >= 4] or [subject.lower()]
    trimmed = []
    for hit in hits:
        lines = [
            line
            for line in (hit.get("text") or "").splitlines()
            if line.startswith("- ") and any(w in line.lower() for w in words)
        ]
        if lines:
            trimmed.append({**hit, "text": "\n".join(lines) + "\n", "timeline": True})
    budget = int(R.CONTEXT_TOKENS.get() * TIMELINE_SHARE) if R.CONTEXT_TOKENS.get() else 800
    cost = lambda h: R.tokens(h["text"]) + 30
    keep = len(trimmed)
    while keep > 0:
        subset = (
            [trimmed[round(i * (len(trimmed) - 1) / max(keep - 1, 1))] for i in range(keep)]
            if keep > 1
            else trimmed[:1]
        )
        if sum(cost(h) for h in subset) <= budget:
            return subset
        keep -= 1
    return []


async def question_about(question: str) -> str:
    reply = await llm.complete_json(
        ABOUT_PROMPT.format(question=question),
        {"properties": {"about": {"type": "string", "enum": ["user", "assistant", "both"]}}, "required": ["about"]},
        purpose="about",
    )
    return reply.get("about") if reply.get("about") in ("user", "assistant", "both") else "both"


def build_items(run, found: dict, design: str, about: str = "both", timeline: list | None = None) -> list[dict]:
    """Evidence items from one question's search results under a design variant."""
    if design == "timeline":
        ids = {h["id"] for h in timeline or []}
        found = {
            **found,
            "results": list(timeline or []) + [h for h in found.get("results") or [] if h["id"] not in ids],
        }
        token = R.TIMELINE_SHARE.set(TIMELINE_SHARE)
        try:
            items, _ = R.evidence(found, run.order)
        finally:
            R.TIMELINE_SHARE.reset(token)
        return items
    if design == "rolefocus" and about == "user":
        found = {
            **found,
            "results": [
                h
                for h in found.get("results") or []
                if h.get("source") == "memories" or (h.get("provenance") or {}).get("role") != "assistant"
            ],
        }
    if design == "nocards":
        found = {**found, "results": [h for h in found.get("results") or [] if not R.is_fact_card(h)]}
    if design == "noconf":
        found = {**found, "results": [h for h in found.get("results") or [] if not R.is_conflict_note(h)]}
    token = R.FACTS_SHARE.set(
        int(design[5:]) / 100 if design.startswith("cards") and design[5:].isdigit() else R.FACTS_SHARE.get()
    )
    try:
        items, _ = R.evidence(found, run.order)
    finally:
        R.FACTS_SHARE.reset(token)
    return items


def is_design(name: str) -> bool:
    return name in ("nocards", "noconf", "all", "rolefocus", "timeline") or (
        name.startswith("cards") and name[5:].isdigit()
    )


def variant_items(name: str, items: list[dict]) -> list[dict]:
    if name == "base":
        return items
    if name in ("lint", "qualify"):
        out = []
        for item in items:
            if item["role"] == "memory note":
                text = lint_note(item["text"], name == "qualify")
                if text.strip():
                    out.append({**item, "text": text})
            else:
                out.append(item)
        return out
    if name == "rankfirst":
        top = sorted((i for i in items if i.get("rank")), key=lambda i: i["rank"])[:5]
        ids = {id(i) for i in top}
        return top + [i for i in items if id(i) not in ids]
    if name == "legend":
        return items  # the legend is added to the context, not to the items
    if name == "roles":
        labels = {
            "user": "user (their own message)",
            "assistant": "assistant (its reply: advice, examples, proposals)",
            "memory note": "memory note (summary of a turn)",
        }
        return [{**i, "role": labels.get(i["role"], i["role"])} for i in items]
    if name == "notesfirst":
        return [i for i in items if i["role"] == "memory note"] + [i for i in items if i["role"] != "memory note"]
    raise SystemExit(f"unknown variant {name}")


async def main():
    argv = sys.argv
    split = argv[argv.index("--split") + 1]
    tag = argv[argv.index("--tag") + 1]
    variants = ["base"] + [v for v in argv[argv.index("--variants") + 1].split(",") if v != "base"]
    repeat = int(argv[argv.index("--repeat") + 1]) if "--repeat" in argv else 2
    base_design = argv[argv.index("--base") + 1] if "--base" in argv else "asis"
    flags = argv[argv.index("--") + 1 :]
    sys.argv = ["run.py", "--split", split] + flags
    args = R.parse_arguments()
    run = R.Run(args)
    rows, _ = load_rows(split)
    conversations = [build_conversation(r) for r in rows]
    run.as_of = {qid: when for c in conversations for qid, when in R.as_of_times(c).items()}
    out_dir = paths.new_run_dir(f"pv-{split}-{tag}")
    os.makedirs(out_dir, exist_ok=True)
    path = f"{out_dir}/results.jsonl"
    done = {json.loads(l)["questionId"] for l in open(path)} if os.path.exists(path) else set()
    slots = asyncio.Semaphore(int(os.environ.get("PV_QUESTIONS_AT_ONCE", "6")))
    lock = asyncio.Lock()

    async def answer(question, items, legend=False):
        context = json.dumps(
            {"legend": LEGEND, "results": items} if legend else {"results": items},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        prompt = (
            exabase_prompts.answer_prompt(question.text, context, question.category, question.annotations)
            if run.prompt == "exabase"
            else R.paper_prompt(question.text, context)
        )
        text = (await llm.complete_text(prompt)).strip()
        score, _ = await scoring.score_question(question, text)
        return score, text

    async def one(conversation, question):
        if question.id in done:
            return
        async with slots:
            try:
                R.CURRENT_AS_OF.set(run.as_of.get(question.id) if run.point_in_time else None)
                session = session_id(split, conversation.id)
                found = await R.expand_top(run, await R.retrieve(run, session, question.text))
                if run.deep and found:
                    found = await R.deepen(run, found)
                items = build_items(run, found, base_design)
                about = await question_about(question.text) if any("rolefocus" in v for v in variants) else "both"
                timeline = (
                    await timeline_hits(run, session, question.text) if any("timeline" in v for v in variants) else []
                )
                row = {"questionId": question.id, "category": question.category, "about": about, "variants": {}}
                base_context = json.dumps(items, ensure_ascii=False)
                for name in variants:
                    parts = name.split("+")
                    design = next((p for p in parts if is_design(p)), None)
                    shown = build_items(run, found, design, about, timeline) if design else items
                    for part in parts:
                        if not is_design(part):
                            shown = variant_items(part, shown)
                    legend = "legend" in parts
                    changed = name == "base" or legend or json.dumps(shown, ensure_ascii=False) != base_context
                    if not changed:
                        row["variants"][name] = {"changed": False}
                        continue
                    results = await asyncio.gather(
                        *(answer(question, shown, name != "base" and legend) for _ in range(repeat))
                    )
                    row["variants"][name] = {
                        "changed": True,
                        "scores": [s for s, _ in results],
                        "answers": [a for _, a in results],
                    }
            except Exception as error:
                if llm.stops_the_run(error):
                    raise
                log(f"{question.id}: failed ({str(error)[:160]})", conversation.id)
                return
        async with lock:
            with open(path, "a") as file:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    await asyncio.gather(*(one(c, q) for c in conversations for q in c.questions))
    await run.opencrawl.close()
    await llm.close()
    report(path, variants)


def report(path, variants=None):
    rows = [json.loads(l) for l in open(path)]
    variants = variants or list(rows[0]["variants"])
    rng = random.Random(7)
    base = {r["questionId"]: st.mean(r["variants"]["base"]["scores"]) for r in rows}
    print(f"{len(rows)} questions; base {100 * st.mean(base.values()):.2f}")
    print(
        "| Variant | Questions whose context changes | Score | Δ vs base, all questions (95% CI) | Δ on changed questions |\n|---|---:|---:|---|---:|"
    )
    for name in variants:
        if name == "base":
            continue
        diffs, changed = [], []
        for r in rows:
            v = r["variants"][name]
            d = (st.mean(v["scores"]) - base[r["questionId"]]) if v["changed"] else 0.0
            diffs.append(d)
            if v["changed"]:
                changed.append(d)
        n = len(diffs)
        boots = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(5000))
        print(
            f"| {name} | {len(changed)} | {100 * (st.mean(base.values()) + st.mean(diffs)):.2f} | {100 * st.mean(diffs):+.2f} ({100 * boots[125]:+.2f} to {100 * boots[4875]:+.2f}) | "
            f"{100 * st.mean(changed) if changed else 0:+.2f} |"
        )
    cats = sorted({r["category"] for r in rows})
    print(
        "\n| Ability | base | "
        + " | ".join(v for v in variants if v != "base")
        + " |\n|---|---:|"
        + "---:|" * (len(variants) - 1)
    )
    for c in cats:
        sub = [r for r in rows if r["category"] == c]
        cells = []
        for name in variants:
            if name == "base":
                continue
            cells.append(
                f"{100 * st.mean((st.mean(r['variants'][name]['scores']) - base[r['questionId']]) if r['variants'][name]['changed'] else 0.0 for r in sub):+.1f}"
            )
        print(f"| {c} | {100 * st.mean(base[r['questionId']] for r in sub):.1f} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report(sys.argv[sys.argv.index("--report") + 1])
    else:
        asyncio.run(main())
