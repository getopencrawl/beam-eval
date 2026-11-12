"""Write exabase_prompts.py from the published BEAM adapter, so that the prompt text in this harness comes from
that file and from nowhere else.

    python make_exabase_prompts.py /path/to/adapter.py        # writes exabase_prompts.py next to this script

The adapter is the Python file published at ADAPTER_URL below. `python check_harness.py --prompts` downloads it and
compares it with exabase_prompts.py; this script is how exabase_prompts.py was made from a saved copy of it.
The adapter is only read, never run.
"""

import ast
import hashlib
import sys
from pathlib import Path

ADAPTER_URL = "https://fabric.so/p/beam-3VjBcqEVRofZyA5CeazeX"
ADAPTER_SHA256 = "584b672d957f3e6f75e96f881ec31da22e1039da1df5fbedb53dc6a9145cfc43"

TEMPLATE = '''"""The annotation-aided answer prompt and the judge prompts of the BEAM adapter published at ADAPTER_URL.

We know the adapter as ExaBase's from published BEAM work that uses it. The page itself names no organisation
and states no licence. The prompts are reproduced here unchanged, with that attribution, so
that answers are produced and judged the way they are for published results that use the adapter. They are not
our work and are not covered by this repository's licence (see NOTICE.md).

What is taken from the adapter, character for character:

- its method `BEAMDataset.build_rag_prompt`, whole, unused parameters included. It is kept below in a class we
  named ExaBaseAdapter. For each ability it adds guidance to the answer prompt, and part of that guidance comes
  from the dataset's annotations for the question (the topics to order, the rubric items a summary should cover,
  time points, the preference or instruction under test, why a question may be unanswerable). This is the
  annotation-aided prompt.
- the text of its two judge prompts (`judge_prompt`, `same_item_prompt`) and the reply fields it asks the judge
  for (`JUDGE_REPLY`, `SAME_ITEM_REPLY`).

`python check_harness.py --prompts` downloads the adapter, checks its hash, and compares each of these with it.

This file is written by make_exabase_prompts.py; do not edit the prompt text.
"""

ADAPTER_URL = "@URL@"
ADAPTER_SHA256 = "@SHA@"


class ExaBaseAdapter:
    """Holds the adapter's answer-prompt method as published."""

@ANSWER_METHOD@


def answer_prompt(question: str, context: str, category: str, annotations: dict) -> str:
    """The annotation-aided answer prompt for one question, given the evidence the memory system returned."""
    return ExaBaseAdapter().build_rag_prompt(question, context, "open", "", category, annotations)


def judge_prompt(query: str, answer: str, rubric_item: str) -> str:
    """Asks the judge whether an answer satisfies one rubric item (0, 0.5 or 1)."""
    return @JUDGE_PROMPT@


JUDGE_REPLY = @JUDGE_REPLY@


def same_item_prompt(ref_item: str, sys_item: str) -> str:
    """Asks the judge whether two list items name the same thing, for event ordering."""
    return @SAME_PROMPT@


SAME_ITEM_REPLY = @SAME_REPLY@
'''


def main(adapter_path: Path, out_path: Path) -> None:
    raw = adapter_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != ADAPTER_SHA256:
        raise SystemExit(f"{adapter_path} has SHA-256 {digest}, not {ADAPTER_SHA256}")
    source = raw.decode("utf-8")
    lines = source.splitlines()
    adapter_class = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == "BEAMDataset")
    method = {node.name: node for node in adapter_class.body if isinstance(node, ast.FunctionDef)}

    def assigned(function: ast.FunctionDef, name: str) -> ast.expr:
        return next(n.value for n in function.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == name)

    def prompt_text(function: ast.FunctionDef) -> str:  # the f-string assigned to `prompt`, as source text
        return ast.get_source_segment(source, assigned(function, "prompt"))

    def reply_fields(function: ast.FunctionDef) -> dict:  # the keywords of the Schema(...) the adapter builds
        return {keyword.arg: ast.literal_eval(keyword.value) for keyword in assigned(function, "schema").keywords}

    answer = method["build_rag_prompt"]
    rubric, same = method["_rubric_item_score"], method["_llm_equivalence"]
    text = TEMPLATE
    for mark, value in (
        ("@URL@", ADAPTER_URL),
        ("@SHA@", ADAPTER_SHA256),
        ("@ANSWER_METHOD@", "\n".join(lines[answer.lineno - 1 : answer.end_lineno])),  # whole lines, indented as in the class
        ("@JUDGE_PROMPT@", prompt_text(rubric)),
        ("@JUDGE_REPLY@", repr(reply_fields(rubric))),
        ("@SAME_PROMPT@", prompt_text(same)),
        ("@SAME_REPLY@", repr(reply_fields(same))),
    ):
        text = text.replace(mark, value)
    compile(text, str(out_path), "exec")
    out_path.write_text(text, "utf-8")
    print(f"wrote {out_path} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), Path(__file__).resolve().parent / "exabase_prompts.py")
