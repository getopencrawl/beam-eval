"""Do the numbers in an answer appear in the prompt its model read?

Used for one check on the reference system's published answers: if they contained many more numbers that are absent
from the published evidence than our replays of that evidence do, the published evidence would not be all that its
answer model read. For each answer this extracts the numbers (ignoring list numbering and turn references) and
counts those that occur nowhere in the prompt built from the published evidence.

    export BEAM_REFERENCE_RESULTS=/path/to/those/records     # not included here: docs/reference-system.md
    python check_grounding.py 10m
"""

import collections
import json
import re
import sys

import exabase_prompts
import paths
from dataset import build_conversation, load_rows

NUMBER = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?")
REPLAYS = {"100k": "replay-100k-raw_x3", "500k": "replay-500k-raw_x3", "1m": "replay-1m-raw", "10m": "replay-10m-raw"}


def numbers(text: str) -> set[str]:
    found = set()
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*]\s*)?\d+[.)]\s", "", line)  # list numbering
        line = re.sub(r"\(?[Tt]urns? [\d, and–-]+\)?", "", line)  # turn references
        for match in NUMBER.findall(line):
            value = match.strip("$%").replace(",", "").rstrip(".")
            if len(value) >= 2:
                found.add(value)
    return found


def main(split: str) -> None:
    rows, _ = load_rows(split)
    questions = {q.id: q for row in rows for q in build_conversation(row).questions}
    replayed = {record["questionId"]: record.get("answer") or "" for record in paths.read_rows(REPLAYS[split])}
    counts = collections.defaultdict(lambda: {"published": [0, 0], "replay": [0, 0]})  # [numbers, absent from the prompt]
    for record in paths.read_jsonl(paths.reference_results(split)):
        question = questions[record["questionId"]]
        context = json.dumps(record["recall"], ensure_ascii=False, separators=(",", ":"))
        prompt = exabase_prompts.answer_prompt(question.text, context, question.category, question.annotations)
        prompt = re.sub(r"(?<=\d),(?=\d)", "", prompt)
        for which, answer in (("published", record.get("answer") or ""), ("replay", replayed.get(record["questionId"], ""))):
            found = numbers(answer)
            for scope in (record["category"], "all"):
                counts[scope][which][0] += len(found)
                counts[scope][which][1] += sum(1 for number in found if number not in prompt)
    print(f"{split}: numbers in answers that do not occur in the prompt (question, annotations, published evidence)")
    print(f"{'ability':28s} {'published answers':>24s}   {'our replay of the evidence':>28s}")
    for scope in sorted(counts, key=lambda name: (name == "all", name)):
        published, replay = counts[scope]["published"], counts[scope]["replay"]
        print(f"{scope:28s} {published[1]:6d} of {published[0]:6d}  {published[1] / max(published[0], 1):6.3f}   "
              f"{replay[1]:8d} of {replay[0]:6d}  {replay[1] / max(replay[0], 1):6.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
