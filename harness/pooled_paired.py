"""Pool one variant of a paired replay (replay_variants.py) over several splits.

    python pooled_paired.py pv7p all            # the paired replay pv-<split>-pv7p, variant "all"
"""

import random, statistics as st, sys

import paths

tag, name = sys.argv[1], sys.argv[2]


def ci(diffs, n=10000):
    rng = random.Random(7)  # every interval restarts the stream, as verify.py does
    k = len(diffs)
    boots = sorted(sum(diffs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return 100 * st.mean(diffs), 100 * boots[int(0.025 * n)], 100 * boots[int(0.975 * n)], sum(b > 0 for b in boots) / n


everything, cats = [], {}
print("| Split | Questions | Evidence changes | Base | Δ (95% CI) | P(Δ>0) |\n|---|---:|---:|---:|---|---:|")
for split in ("100k", "500k", "1m", "10m"):
    if not paths.find_run(f"pv-{split}-{tag}"):
        continue
    rows = paths.read_rows(f"pv-{split}-{tag}")
    diffs = []
    for r in rows:
        base = st.mean(r["variants"]["base"]["scores"])
        v = r["variants"][name]
        d = (st.mean(v["scores"]) - base) if v["changed"] else 0.0
        diffs.append(d)
        cats.setdefault(r["category"], []).append(d)
    m, lo, hi, p = ci(diffs)
    everything += diffs
    print(
        f"| {split} | {len(rows)} | {sum(r['variants'][name]['changed'] for r in rows)} | {100 * st.mean(st.mean(r['variants']['base']['scores']) for r in rows):.2f} | {m:+.2f} ({lo:+.2f} to {hi:+.2f}) | {p:.3f} |"
    )
m, lo, hi, p = ci(everything)
print(f"| **All** | {len(everything)} | | | **{m:+.2f} ({lo:+.2f} to {hi:+.2f})** | {p:.3f} |\n")
print("| Ability | Δ, all splits |\n|---|---:|")
for c in sorted(cats):
    print(f"| {c} | {100 * st.mean(cats[c]):+.1f} |")
