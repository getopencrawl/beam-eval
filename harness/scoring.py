"""How an answer becomes a score between 0 and 1.

The rules are the BEAM paper's, in the form ExaBase's published adapter gives them (see exabase_prompts.py for the
adapter; the judge prompts are its prompts):

- Event ordering. The answer is read as a list. Each of its items is renamed to the first topic of the reference
  order that the judge says is the same thing and that no earlier item has taken. The two orders are then compared
  with Kendall's tau-b over every item of either list, an item absent from a list ranking after all of its items;
  tau-b runs from -1 to 1 and is mapped to 0..1.
- Every other ability. The judge scores the answer against each rubric item, and the question's score is the mean.
  The judge is asked for 0, 0.5 or 1; any other number is moved to the nearest of the three (0.75 and above is 1,
  0.25 and above is 0.5). A question without a rubric is judged against its reference answer as one item.

A rubric verdict the judge fails to give counts 0 and is recorded with its error, so the failure is visible in the
result and counted in the summary. In event ordering, a comparison of two items that fails counts as "different"
and is only logged: nothing in the record marks it. Errors that mean the account is refused stop the run instead
(llm.stops_the_run).

`summarize` gives a run's mean over questions (the number reported everywhere), each ability's mean, and the mean of
those means.
"""

import asyncio
import math
import re

from scipy.stats import kendalltau

import exabase_prompts
import llm
from log import log

# What the adapter removes from the front of a list line: "3." or "3)" or a dash or an asterisk.
LIST_MARK = re.compile(r"^\s*(?:\d+[.)]\s*|[-*]\s*)")


def nearest_step(raw: float) -> float:
    """The judge's number as one of 0, 0.5, 1."""
    if raw >= 0.75:
        return 1.0
    return 0.5 if raw >= 0.25 else 0.0


def list_items(text: str) -> list[str]:
    """The non-empty lines of a list, without their numbers or bullets."""
    stripped = (LIST_MARK.sub("", line).strip() for line in text.strip().splitlines())
    return [item for item in stripped if item]


def order_agreement(reference: list[str], answer: list[str]) -> float:
    """Kendall's tau-b between two orders of (mostly) the same items, as a number from 0 (reversed) to 1 (same).

    Ranks are positions counted from 1. An item that a list repeats takes its last position there, and an item a
    list does not have ranks one past the number of distinct items, which is how the adapter computes it. Where tau
    is undefined (a single item, or a list that ranks everything equally) the score is 0, also as in the adapter, so
    two identical one-item lists score 0.
    """
    items = list(dict.fromkeys([*reference, *answer]))
    absent = len(items) + 1

    def ranks(order: list[str]) -> list[int]:
        last_position = {}
        for position, item in enumerate(order, start=1):
            last_position[item] = position
        return [last_position.get(item, absent) for item in items]

    tau, _ = kendalltau(ranks(reference), ranks(answer), variant="b")
    if tau is None or math.isnan(tau):  # undefined when one of the two orders is all ties
        return 0.0
    return float((tau + 1) / 2)


def rubric_mean(items: list[dict]) -> float:
    """A question's score from its rubric verdicts: the mean of their scores."""
    return sum(item["score"] for item in items) / len(items)


async def score_question(question, answer: str) -> tuple[float, dict]:
    """The score of one answer and the verdicts it rests on, in the form the result files store them."""
    golds = question.gold_answers
    if question.category == "event_ordering":
        reference = question.annotations.get("ordering_tested") or (list_items(golds[0]) if golds else [])
        if not reference:
            return 0.0, {"method": "event_ordering", "note": "no reference order for this question"}
        return await _score_order(reference, list_items(answer))

    rubric = question.annotations.get("rubric") or ([f"LLM response should contain: {golds[0]}"] if golds else [])
    if not rubric:
        return 0.0, {"method": "rubric", "note": "no rubric for this question"}
    items = await asyncio.gather(*(_judge_item(question.text, answer, item) for item in rubric))
    return rubric_mean(items), {"method": "rubric", "items": list(items)}


async def _judge_item(question: str, answer: str, rubric_item: str) -> dict:
    try:
        reply = await llm.complete_json(
            exabase_prompts.judge_prompt(question, answer, rubric_item), exabase_prompts.JUDGE_REPLY
        )
        raw = float(reply.get("score", 0))
    except Exception as error:
        if llm.stops_the_run(error):
            raise
        return {"rubricItem": rubric_item, "score": 0.0, "error": str(error)[:500]}
    return {"rubricItem": rubric_item, "rawScore": raw, "score": nearest_step(raw), "reason": reply.get("reason", "")}


async def _same_item(topic: str, item: str) -> bool:
    try:
        reply = await llm.complete_json(
            exabase_prompts.same_item_prompt(topic, item), exabase_prompts.SAME_ITEM_REPLY
        )
    except Exception as error:
        if llm.stops_the_run(error):
            raise
        log(f"could not compare two list items ({str(error)[:120]}); they count as different")
        return False
    return str(reply.get("answer", "")).strip().upper().startswith("YES")


async def _score_order(reference: list[str], answer_items: list[str]) -> tuple[float, dict]:
    verdict = {"method": "event_ordering", "reference": reference, "answer": answer_items}
    if not answer_items:
        return 0.0, verdict
    # One item at a time, in the answer's order: each takes the first free topic the judge accepts, so the
    # comparisons made for an item depend on what the items before it took.
    taken: set[int] = set()
    renamed = []
    for item in answer_items:
        chosen = None
        for index, topic in enumerate(reference):
            if index not in taken and await _same_item(topic, item):
                chosen = index
                break
        if chosen is None:
            renamed.append(item)
        else:
            taken.add(chosen)
            renamed.append(reference[chosen])
    verdict["answer"] = renamed
    return order_agreement(reference, renamed), verdict


def summarize(rows: list[dict]) -> dict:
    """A run's scores from its records: over questions, per ability, and over abilities."""
    by_ability: dict[str, list[float]] = {}
    for row in rows:
        by_ability.setdefault(row["category"], []).append(float(row["score"]))
    abilities = {
        name: {"questions": len(scores), "mean": sum(scores) / len(scores)} for name, scores in sorted(by_ability.items())
    }
    scores = [float(row["score"]) for row in rows]
    failed_verdicts = 0
    for row in rows:
        judge = row.get("judge")
        if isinstance(judge, dict):
            failed_verdicts += sum(1 for item in judge.get("items") or [] if item.get("error"))
    return {
        "questions": len(scores),
        "failedQuestions": sum(1 for row in rows if row.get("error")),  # retrieval or the answer call failed
        "failedVerdicts": failed_verdicts,  # rubric items the judge did not rule on
        "microAverage": sum(scores) / len(scores) if scores else None,
        "macroAverage": sum(a["mean"] for a in abilities.values()) / len(abilities) if abilities else None,
        "categories": abilities,
    }
