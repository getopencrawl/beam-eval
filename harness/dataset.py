"""BEAM as this harness reads it.

A row of the dataset is one long conversation and the twenty questions asked about it. `build_conversation` turns a
row into two lists:

- `messages`: every non-empty turn, in order, with a stable id, the session it belongs to, and a timestamp
  (text is kept as written, without leading or trailing white space);
- `questions`: every probing question, with its reference answers, its annotations, and the moment it is asked.

Three decisions here shape the published records, so they are spelled out.

Ids. A turn's id is `<conversation>_<place>`, where the place says where the turn sits in the row: `s003_t0012` is
turn 12 of session 3 in the 100K, 500K and 1M splits; `p002_b0004_g0007_t0001` is turn 1 of group 7 of batch 4 of
plan 2 in the 10M split, whose conversations are nested one level deeper. Counting starts at zero except for plans,
which carry the number in their name. A question's id is `<conversation>_<ability>_<index>`.

Time. BEAM dates a session (10M: a batch) with a day such as "March-15-2024", written on its first turn. Every turn
is placed at noon UTC of its day, plus one microsecond per turn since the start of the conversation, so timestamps
are unique. They follow conversation order wherever BEAM's days do, which is not everywhere: in four 10M
conversations (1, 3, 4, 5) a batch carries an earlier day than the batch before it. (run.py spaces turns by a
millisecond instead when it ingests them, because the index keeps milliseconds.)

The moment a question is asked. Every question is asked at the end of the conversation, except knowledge-update
questions: BEAM cites the turns that carry the updated value, and the question is asked at the latest turn with a
cited id. For 10 of the 200 knowledge-update questions no cited turn is found, and they are asked at the end like
the rest. BEAM's turn ids repeat inside four 1M conversations (5, 26, 33, 34); the latest turn that has a cited id
is the one taken.

The annotations (rubric, and for some abilities the topics to order, the time points, the preference or instruction
under test, the reason a question cannot be answered) are the ones ExaBase's published BEAM adapter passes to its
prompts. Retrieval never receives them: they are read by the annotation-aided answer prompt and by the judge.
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

# split -> (Hugging Face dataset, its split name, the revision every run in results/ used)
SOURCES = {
    "100k": ("Mohammadta/BEAM", "100K", "3205395e897e7318c7b094ef4e6047b9b82dbb03"),
    "500k": ("Mohammadta/BEAM", "500K", "3205395e897e7318c7b094ef4e6047b9b82dbb03"),
    "1m": ("Mohammadta/BEAM", "1M", "3205395e897e7318c7b094ef4e6047b9b82dbb03"),
    "10m": ("Mohammadta/BEAM-10M", "10M", "9b2096193fe74e2837e4713e483351e19817773c"),
}
SPLITS = list(SOURCES)

# The ten abilities, in the order questions are numbered and reported.
CATEGORIES = [
    "abstention",
    "contradiction_resolution",
    "event_ordering",
    "information_extraction",
    "instruction_following",
    "knowledge_update",
    "multi_session_reasoning",
    "preference_following",
    "summarization",
    "temporal_reasoning",
]

# Where a question keeps its reference answer: the first of ANSWER_KEYS that is present (ExaBase's adapter reads the
# same keys in the same order). Abilities graded on behaviour rather than content leave it blank and describe the
# expected behaviour under one of BEHAVIOUR_KEYS instead.
ANSWER_KEYS = ("ideal_response", "answer", "expected_answer", "expected", "gold_answer", "reference")
BEHAVIOUR_KEYS = ("ideal_answer", "ideal_summary", "expected_compliance")

# Annotations beyond the rubric, by ability, each with the value used when the dataset leaves it out.
ANNOTATION_KEYS = {
    "abstention": {"why_unanswerable": ""},
    "event_ordering": {"ordering_tested": []},
    "instruction_following": {"instruction_being_tested": "", "compliance_indicators": []},
    "preference_following": {"preference_being_tested": "", "compliance_indicators": []},
    "temporal_reasoning": {"time_points": [], "calculation_required": ""},
}

DAY_PATTERNS = ("%B-%d-%Y", "%B %d, %Y", "%B %d %Y", "%Y-%m-%d")
CACHE = Path(os.environ.get("BEAM_CACHE") or Path.home() / ".cache" / "beam-eval")


@dataclass(frozen=True)
class Message:
    message_id: str
    session_id: str
    ordinal: int  # position among the conversation's non-empty turns, from 0
    role: str
    content: str
    timestamp: datetime
    turn_id: str | None  # BEAM's own id for the turn, which its citations use


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    text: str
    gold_answers: list[str]
    annotations: dict
    as_of: str  # UTC time the question is asked, as utc_iso() writes it


@dataclass(frozen=True)
class Conversation:
    id: str
    title: str
    messages: list[Message]
    questions: list[Question]


# --- Loading ------------------------------------------------------------------------------------


def load_rows(split: str) -> tuple[list[dict], str]:
    """The split's rows and the dataset revision they come from. Downloaded once, then read from CACHE."""
    name, hf_split, revision = SOURCES[split]
    rows_file, revision_file = CACHE / f"{split}.json", CACHE / f"{split}.revision"
    if rows_file.exists() and revision_file.exists():
        return json.loads(rows_file.read_text("utf-8")), revision_file.read_text("utf-8").strip()

    from datasets import load_dataset  # imported here so that reading a cached copy does not need the package

    print(f"Downloading BEAM {split}: {name}, split {hf_split}, revision {revision}", flush=True)
    rows = [dict(row) for row in load_dataset(name, split=hf_split, revision=revision)]
    CACHE.mkdir(parents=True, exist_ok=True)
    rows_file.write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
    revision_file.write_text(revision + "\n", "utf-8")
    return rows, revision


def utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# --- A conversation ------------------------------------------------------------------------------


def build_conversation(row: dict) -> Conversation:
    conversation = str(row["conversation_id"])
    seed = row.get("conversation_seed")
    title = seed.get("title") if isinstance(seed, dict) else None
    messages = _messages(conversation, row.get("chat") or [])
    return Conversation(
        id=conversation,
        title=str(title or f"Conversation {conversation}"),
        messages=messages,
        questions=_questions(conversation, row, messages),
    )


def _is_turn(value) -> bool:
    return isinstance(value, dict) and "role" in value


def _places(chat: list) -> Iterator[tuple[str, str, dict]]:
    """Every turn of a row with its place and its session: (place, session, turn)."""
    for outer, item in enumerate(chat):
        if isinstance(item, list):  # a session of turns
            for inner, turn in enumerate(item):
                if _is_turn(turn):
                    yield f"s{outer:03d}_t{inner:04d}", f"s{outer:03d}", turn
        elif _is_turn(item):  # a turn outside any session
            yield f"f{outer:06d}", "flat", item
        elif isinstance(item, dict):  # 10M: {"plan-N": [batch, ...]}, a batch being {"turns": [group, ...]}
            for name, batches in item.items():
                if not isinstance(batches, list):
                    continue
                digits = re.search(r"(\d+)\s*$", str(name))
                plan = f"p{int(digits.group(1)):03d}" if digits else f"p{outer:03d}"
                for b, batch in enumerate(batches):
                    groups = batch.get("turns") if isinstance(batch, dict) else None
                    for g, group in enumerate(groups or []):
                        turns = group if isinstance(group, list) else [group]
                        for t, turn in enumerate(turns):
                            if _is_turn(turn):
                                yield f"{plan}_b{b:04d}_g{g:04d}_t{t:04d}", f"{plan}-b{b:04d}", turn


def _day(text) -> datetime | None:
    """A BEAM date ("March-15-2024", "March 15th, 2024", "2024-03-15") as noon UTC of that day."""
    if not isinstance(text, str) or not text.strip():
        return None
    cleaned = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", text.strip())
    for pattern in DAY_PATTERNS:
        try:
            return datetime.strptime(cleaned, pattern).replace(hour=12, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _session_days(placed: list[tuple[str, str, dict]], conversation: str) -> dict[str, datetime]:
    """The day of each session: the first date written on one of its turns. A session without a date follows the
    one before it: an hour later when sessions are BEAM's own (so that two sessions never share a moment), on the
    same day in the 10M split. If the conversation opens with undated sessions they are placed the day before the
    first dated one."""
    order: list[str] = []
    found: dict[str, datetime | None] = {}
    for _, session, turn in placed:
        if session not in found:
            order.append(session)
            found[session] = None
        if found[session] is None:
            found[session] = _day(turn.get("time_anchor"))
    if not any(found.values()):
        raise ValueError(f"Conversation {conversation} has no dated turn")

    days: dict[str, datetime] = {}
    previous = None
    for session in order:
        if found[session] is not None:
            previous = found[session]
        elif previous is not None:
            previous = previous + (timedelta(hours=1) if session.startswith("s") else timedelta(0))
        days[session] = previous  # None only before the first dated session
    first_dated = next(day for day in (found[s] for s in order) if day is not None)
    for session in order:
        if days[session] is None:
            days[session] = first_dated - timedelta(days=1)
    return days


def _messages(conversation: str, chat: list) -> list[Message]:
    placed = list(_places(chat))
    if not placed:
        return []
    days = _session_days(placed, conversation)
    messages: list[Message] = []
    for place, session, turn in placed:
        content = turn.get("content")
        content = content.strip() if isinstance(content, str) else ""
        if not content:
            continue
        ordinal = len(messages)
        messages.append(
            Message(
                message_id=f"{conversation}_{place}",
                session_id=session,
                ordinal=ordinal,
                role=str(turn.get("role") or "user").lower(),
                content=content,
                timestamp=days[session] + timedelta(microseconds=ordinal),
                turn_id=None if turn.get("id") is None else str(turn["id"]),
            )
        )
    return messages


# --- Its questions -------------------------------------------------------------------------------


def probing_questions(row: dict) -> dict[str, list[dict]]:
    """The row's questions by ability. The dataset stores them as a string (JSON, or a Python literal)."""
    value = row.get("probing_questions") or {}
    if isinstance(value, str):
        for parse in (json.loads, ast.literal_eval):
            try:
                value = parse(value)
                break
            except (ValueError, SyntaxError):
                continue
    return value if isinstance(value, dict) else {}


def _reference_answers(item: dict) -> list[str]:
    answer = next((item[key] for key in ANSWER_KEYS if key in item), None)
    text = "" if answer is None else str(answer)
    if not text.strip():
        behaviour = next((item[key] for key in BEHAVIOUR_KEYS if item.get(key)), None)
        text = "" if behaviour is None else str(behaviour)
    return [text] if text.strip() else []


def _annotations(category: str, item: dict) -> dict:
    found: dict = {}
    rubric = item.get("rubric")
    if rubric:
        found["rubric"] = list(rubric) if isinstance(rubric, list) else [str(rubric)]
    for key, missing in ANNOTATION_KEYS.get(category, {}).items():
        found[key] = item.get(key, missing)
    return found


def _cited_updates(item: dict) -> set[str]:
    """BEAM's ids of the turns that carry a knowledge update's new value, however deeply they are listed."""
    cited: set[str] = set()
    pending = [(item.get("source_chat_ids") or {}).get("updated_info")]
    while pending:
        value = pending.pop()
        if isinstance(value, (list, tuple)):
            pending.extend(value)
        elif value is not None and not isinstance(value, dict):
            cited.add(str(value))
    return cited


def _questions(conversation: str, row: dict, messages: list[Message]) -> list[Question]:
    if not messages:
        return []
    end = messages[-1].timestamp
    by_ability = probing_questions(row)
    questions = []
    for category in CATEGORIES:
        for index, item in enumerate(by_ability.get(category) or []):
            text = str(item.get("question") or "") if isinstance(item, dict) else ""
            if not text.strip():
                continue  # the question text itself is kept exactly as the dataset writes it
            asked = end
            if category == "knowledge_update":
                cited = _cited_updates(item)
                moments = [m.timestamp for m in messages if m.turn_id in cited]
                if moments:
                    asked = max(moments)
            questions.append(
                Question(
                    id=f"{conversation}_{category}_{index}",
                    category=category,
                    text=text,
                    gold_answers=_reference_answers(item),
                    annotations=_annotations(category, item),
                    as_of=utc_iso(asked),
                )
            )
    return questions
