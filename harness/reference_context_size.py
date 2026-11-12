"""Size of the context the reference system's answer model read, per conversation length.

For each question, the tokens (o200k_base) of its published evidence object as compact JSON, which is the string
its harness puts into the answer prompt. The means are the context caps OpenCrawl's runs were given
(run_config.sh), so that both answer models read contexts of the same size on average.

    export BEAM_REFERENCE_RESULTS=/path/to/those/records     # not included here: docs/reference-system.md
    python reference_context_size.py          # prints what results/reference/context-tokens.json holds
"""

import json
import statistics

import tiktoken

import paths

if __name__ == "__main__":
    encoding = tiktoken.get_encoding("o200k_base")
    sizes_by_length = {}
    for split in ("100k", "500k", "1m", "10m"):
        sizes = sorted(
            len(encoding.encode(json.dumps(record["recall"], ensure_ascii=False, separators=(",", ":")), disallowed_special=()))
            for record in paths.read_jsonl(paths.reference_results(split))
            if record.get("recall")
        )
        sizes_by_length[split] = {"mean": round(statistics.mean(sizes)), "median": round(statistics.median(sizes)),
                                  "p90": sizes[int(0.9 * len(sizes))], "max": sizes[-1], "n": len(sizes)}
    print(json.dumps(sizes_by_length, indent=1))
