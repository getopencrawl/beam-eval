"""Optional: write OpenCrawl's semantic (learned-sparse) vectors for already indexed passages from the host.

OpenCrawl encodes passages inside the search cluster by itself (pipeline `opencrawl-semantic-*`, sparse_encoding
with opensearch-neural-sparse-encoding-doc-v3-distill); nothing here is needed for correctness. That background
encoder handles about ten long passages a second, which is slow for a first load of a million passages. This script
produces the same vectors in batches with PyTorch -- verified to 2e-6 on shared tokens: max-pool over tokens,
log(1 + log(1 + relu(x))), special tokens zeroed, weights below 0.1 x the passage maximum pruned.

    python encode_backfill.py MODEL_ID beam3-100k- beam3-500k- beam3-1m- beam3-10m-

MODEL_ID is the id of the sparse-encoding model deployed in the cluster; the arguments after it are session-id
prefixes. For the reported runs the same encoder ran on a GPU at about 200 passages a second.
"""

import sys, time, json
import httpx, torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

OS = "http://127.0.0.1:19200"
NAME = "opensearch-project/opensearch-neural-sparse-encoding-doc-v3-distill"
torch.set_num_threads(8)
tok = AutoTokenizer.from_pretrained(NAME)
model = AutoModelForMaskedLM.from_pretrained(NAME).eval()
special = [tok.vocab[t] for t in tok.special_tokens_map.values() if isinstance(t, str)]
id2tok = {v: k for k, v in tok.vocab.items()}


def encode(texts):
    # Sort by length so padding stays small.
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    out = [None] * len(texts)
    for start in range(0, len(order), 16):
        idx = order[start : start + 16]
        f = tok([texts[i] for i in idx], padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            logits = model(**f)[0]
        v, _ = torch.max(logits * f["attention_mask"].unsqueeze(-1), dim=1)
        v = torch.log1p(torch.log1p(torch.relu(v)))
        v[:, special] = 0
        for row, i in zip(v, idx):
            nz = torch.nonzero(row).flatten()
            weights = row[nz]
            keep = weights >= 0.1 * weights.max() if len(weights) else weights.bool()
            out[i] = {id2tok[int(t)]: float(w) for t, w in zip(nz[keep], weights[keep])}
    return out


def main(model_id, prefixes):
    http = httpx.Client(timeout=120)
    index = http.get(f"{OS}/_cat/indices/opencrawl-*?h=index").text.split()[0]
    for prefix in prefixes:
        done, started = 0, time.time()
        # "notes:<prefix>" selects agent memory passages linked to sessions with that prefix.
        field = "memory.sourceSessionId" if prefix.startswith("notes:") else "session.sessionId"
        query = {
            "bool": {
                "filter": [{"prefix": {field: prefix.removeprefix("notes:")}}],
                "must_not": [{"term": {"semantic": model_id}}],
            }
        }
        while True:
            hits = http.post(f"{OS}/{index}/_search", json={"size": 256, "_source": ["text"], "query": query}).json()[
                "hits"
            ]["hits"]
            if not hits:
                break
            vectors = encode([h["_source"].get("text") or "" for h in hits])
            body = "".join(
                json.dumps({"update": {"_id": h["_id"]}})
                + "\n"
                + json.dumps({"doc": {"textSparse": v, "semantic": model_id}})
                + "\n"
                for h, v in zip(hits, vectors)
            )
            r = http.post(
                f"{OS}/{index}/_bulk?refresh=wait_for", content=body, headers={"content-type": "application/x-ndjson"}
            ).json()
            if r.get("errors"):
                bad = [i for i in r["items"] if i["update"].get("error")][:2]
                raise SystemExit(f"bulk errors: {bad}")
            done += len(hits)
            print(f"{prefix} {done} docs, {done / (time.time() - started):.1f}/s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
