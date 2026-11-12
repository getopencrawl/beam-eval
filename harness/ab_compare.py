"""Paired comparison of two OpenCrawl configurations on the same questions.

    python ab_compare.py final2 final3 [--prompt paper]

Per split: mean over each configuration's answer runs, difference with a paired bootstrap over questions
(10,000 resamples) on per-question means, and the difference by ability.
"""

import random, statistics as st, sys

import paths

A, B = sys.argv[1], sys.argv[2]
PROMPT = sys.argv[sys.argv.index("--prompt") + 1] if "--prompt" in sys.argv else "exabase"
SPLITS = ["100k", "500k", "1m", "10m"]


def load(split, tag):
    out, failed, runs = {}, 0, []
    for d in paths.run_dirs(f"{split}-search-{PROMPT}-{tag}-*"):
        if not (d / "summary.json").exists():
            continue
        scores = []
        for r in paths.read_rows(d):
            out.setdefault(r["questionId"], {"category": r["category"], "scores": []})["scores"].append(r["score"])
            failed += bool(r.get("error"))
            scores.append(r["score"])
        runs.append(st.mean(scores))
    return out, failed, runs


def bootstrap(pairs, n=10000, seed=7):
    rng = random.Random(seed)
    k = len(pairs)
    diffs = []
    for _ in range(n):
        diffs.append(sum(pairs[rng.randrange(k)] for _ in range(k)) / k)
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)], sum(d > 0 for d in diffs) / n


print(
    f"| Split | {A} | {B} | Δ (95% CI) | P(Δ>0) | {A} runs | {B} runs | failed |\n|---|---:|---:|---|---:|---|---|---:|"
)
allpairs, weights, cats = [], [], {}
for split in SPLITS:
    a, fa, ra = load(split, A)
    b, fb, rb = load(split, B)
    common = sorted(set(a) & set(b))
    if not common or not ra or not rb:
        print(f"| {split} | (no runs) | | | | | | |")
        continue
    pairs = [st.mean(b[q]["scores"]) - st.mean(a[q]["scores"]) for q in common]
    lo, hi, p = bootstrap(pairs)
    ma, mb = st.mean(st.mean(a[q]["scores"]) for q in common), st.mean(st.mean(b[q]["scores"]) for q in common)
    print(
        f"| {split} ({len(common)}) | {100 * ma:.2f} | {100 * mb:.2f} | {100 * (mb - ma):+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} | "
        f"{', '.join(f'{100 * x:.1f}' for x in ra)} | {', '.join(f'{100 * x:.1f}' for x in rb)} | {fa}/{fb} |"
    )
    allpairs += pairs
    for q in common:
        c = cats.setdefault((split, a[q]["category"]), [[], []])
        c[0].append(st.mean(a[q]["scores"]))
        c[1].append(st.mean(b[q]["scores"]))
if allpairs:
    lo, hi, p = bootstrap(allpairs)
    print(
        f"| All ({len(allpairs)}) | | | {100 * st.mean(allpairs):+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} | | | |"
    )
    print(f"\nBy ability ({B} minus {A}, points):\n")
    names = sorted({c for _, c in cats})
    print("| Ability | " + " | ".join(SPLITS) + " |\n|---|" + "---:|" * len(SPLITS))
    for c in names:
        cells = []
        for s in SPLITS:
            v = cats.get((s, c))
            cells.append(f"{100 * (st.mean(v[1]) - st.mean(v[0])):+.1f}" if v else "")
        print(f"| {c} | " + " | ".join(cells) + " |")
