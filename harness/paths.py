"""Where the harness reads and writes run records.

Published runs live under <repository>/results/, grouped by purpose (results/README.md). A run is identified by
its directory name, which is unique across groups, and its per-question records are in results.jsonl.gz
(results.jsonl for a run made locally). New runs are written to results/local/, which git ignores. If a local run
has the name of a published one, the scripts that look runs up by name find the published one: give local runs a
--tag of their own.

Environment:
    BEAM_RESULTS             another results root
    BEAM_REFERENCE_RESULTS   a directory holding the reference system's published per-question records, one
                             <split>/results.jsonl per split; needed only to replay its evidence or to judge
                             its answers again (docs/reference-system.md describes the records)
"""

import fnmatch
import gzip
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(os.environ.get("BEAM_RESULTS") or ROOT / "results")
LOCAL = RESULTS / "local"
LOGS = Path(__file__).resolve().parent / "logs"  # checkpoints of the note-writing passes
LOGS.mkdir(exist_ok=True)


def _records(directory: Path) -> Path | None:
    for name in ("results.jsonl.gz", "results.jsonl"):
        if (directory / name).exists():
            return directory / name
    return None


def run_dirs(pattern: str = "*") -> list[Path]:
    """Every run directory whose name matches the glob pattern, in name order."""
    found = {}
    for records in list(RESULTS.rglob("results.jsonl.gz")) + list(RESULTS.rglob("results.jsonl")):
        if fnmatch.fnmatchcase(records.parent.name, pattern):
            found.setdefault(records.parent.name, records.parent)
    return [found[name] for name in sorted(found)]


def find_run(name: str) -> Path | None:
    matches = run_dirs(name)
    return matches[0] if matches else None


def run_dir(name: str) -> Path:
    found = find_run(name)
    if found is None:
        raise SystemExit(f"No run named {name} under {RESULTS}")
    return found


def read_rows(run: str | Path) -> list[dict]:
    """The per-question records of a run, given its name or its directory."""
    directory = run if isinstance(run, Path) else run_dir(run)
    records = _records(directory)
    if records is None:
        raise SystemExit(f"No results.jsonl(.gz) in {directory}")
    return read_jsonl(records)


def read_jsonl(path: str | Path) -> list[dict]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def new_run_dir(name: str) -> Path:
    return LOCAL / name


def reference_results(split: str) -> Path:
    """The reference system's published per-question records for a split."""
    root = os.environ.get("BEAM_REFERENCE_RESULTS", "").strip()
    path = Path(root).expanduser() / split / "results.jsonl"
    if not root or not path.exists():
        raise SystemExit(
            "Set BEAM_REFERENCE_RESULTS to a directory holding the reference system's published records as "
            "<split>/results.jsonl (docs/reference-system.md). This repository does not include them."
        )
    return path
