"""Export the agent memory files written for the benchmark from the search index, so the notes that took the
note-taker hundreds of millions of tokens to write are kept with the results.

Three kinds, each as gzip JSON lines per split under memory/ at the top of the repository:
  notes          per-turn narrative notes (installations turnnotes-<session>-<k>)
  fact-cards     what each user message states (facts-<session>-<k>)
  conflict-notes a later denial of something the user reported earlier (conflicts-<session>)

Only the current generation of each installation is exported (what search returns). One line per indexed passage:
{"session", "path", "modifiedAt", "chunk", "text"}.

    python export_memory.py
"""

import collections, gzip, json, os
import httpx

OS = "http://127.0.0.1:19200"
KINDS = {"notes": "turnnotes-", "fact-cards": "facts-", "conflict-notes": "conflicts-"}
OUT = os.environ.get("BEAM_MEMORY_EXPORT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory")


def main():
    http = httpx.Client(timeout=300)
    index = http.get(f"{OS}/_cat/indices/opencrawl-*?h=index").text.split()[0]
    os.makedirs(OUT, exist_ok=True)
    for kind, prefix in KINDS.items():
        query = {
            "bool": {
                "filter": [
                    {"term": {"corpus": "memory"}},
                    {"term": {"memory.kind": "passage"}},
                    {"prefix": {"memory.installationId": prefix}},
                ]
            }
        }
        rows, latest = [], collections.defaultdict(int)
        page = http.post(
            f"{OS}/{index}/_search?scroll=5m",
            json={
                "size": 5000,
                "query": query,
                "_source": [
                    "text",
                    "timestamp",
                    "memory.path",
                    "memory.installationId",
                    "memory.generation",
                    "memory.sourceSessionId",
                    "memory.chunk",
                ],
            },
        ).json()
        while page["hits"]["hits"]:
            for hit in page["hits"]["hits"]:
                source = hit["_source"]
                memory = source["memory"]
                latest[memory["installationId"]] = max(latest[memory["installationId"]], memory.get("generation") or 0)
                rows.append(
                    (
                        memory["installationId"],
                        memory.get("generation") or 0,
                        memory.get("sourceSessionId") or "",
                        memory.get("path") or "",
                        source.get("timestamp"),
                        memory.get("chunk") or 0,
                        source.get("text") or "",
                    )
                )
            page = http.post(f"{OS}/_search/scroll", json={"scroll": "5m", "scroll_id": page["_scroll_id"]}).json()
        by_split = collections.defaultdict(list)
        for installation, generation, session, path, when, chunk, text in rows:
            if generation == latest[installation]:
                split = session.split("-")[1] if session.count("-") >= 2 else "unknown"
                by_split[split].append(
                    {"session": session, "path": path, "modifiedAt": when, "chunk": chunk, "text": text}
                )
        for split, items in sorted(by_split.items()):
            items.sort(key=lambda r: (r["session"], r["path"], r["chunk"]))
            name = f"{OUT}/{kind}-{split}.jsonl.gz"
            with gzip.open(name, "wt") as out:
                for item in items:
                    out.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"{kind:15s} {split:5s} {len(items):7d} passages  {os.path.getsize(name) / 1e6:6.1f} MB  {name}")


if __name__ == "__main__":
    main()
