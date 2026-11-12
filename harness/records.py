"""The records a run writes: one JSON object per question in results.jsonl.

Every record starts with the same six fields; a scored question adds `retrieval` (what was shown to the answer
model, as counts and turn numbers), `answer`, `judge` (the verdicts, see scoring.py) and `score`, and with
--save-context `answerPrompt`, the exact text the answer model received. A question whose retrieval or answer call
failed adds `error` instead and scores 0.
"""

import asyncio
import json
from pathlib import Path


def question_fields(conversation, question, as_of: str | None) -> dict:
    """What identifies a question in a record. `as_of` is the moment retrieval was limited to, if it was."""
    return {
        "asOf": as_of,
        "questionId": question.id,
        "conversationId": conversation.id,
        "category": question.category,
        "question": question.text,
        "goldAnswers": question.gold_answers,
    }


class ResultsFile:
    """A run's results.jsonl. Records are appended a whole conversation at a time, under a lock, so concurrent
    conversations never interleave and an interrupted run holds only complete conversations."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._appending = asyncio.Lock()

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]

    async def append(self, records: list[dict]) -> None:
        text = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
        async with self._appending:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(text)
