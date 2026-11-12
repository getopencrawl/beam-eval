"""The controlled comparison: OpenCrawl's answer runs against the reference system's evidence answered by the same
call, and against its published answers, by length and by ability.

  OpenCrawl           every answer run of one configuration (--config TAG; default final5, the reported system)
  Reference evidence  the reference system's published evidence, answered by this harness (replay_reference.py)
  Published answers   the reference system's published answers, graded by this judge (rejudge.py, three passes)

A question's score is its mean over runs; the difference between the systems is bootstrapped over questions
(10,000 resamples). verify.py at the top of the repository is an independent implementation of the same computation
and checks the numbers this prints.

    python final_compare.py --paper                            # the reported system, BEAM's own prompt
    python final_compare.py                                    # the reported system, annotation-aided prompt
    python final_compare.py --same-day                         # against the replays made on the day of its runs only
    python final_compare.py --ref time                         # reference evidence re-presented: time, ourfmt-time
    python final_compare.py --config final4 --first-replays    # an earlier configuration, as first measured
    python final_compare.py --config final4or --route or       # answer call through OpenRouter
    python final_compare.py --config final2 --with-selection   # also the runs that led to choosing that configuration
"""

import paths
import random, statistics as st, sys

SPLITS = ["100k", "500k", "1m", "10m"]
PROMPT = "paper" if "--paper" in sys.argv else "exabase"
# Headline: only runs launched after the configuration was frozen (tag final2). --with-selection also counts the
# earlier runs of the same configuration that led to choosing it (1M t35-a/b, 10M t34-user1-time-a/b).
CONFIG = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else "final5"
OURS = {s: [f"{s}-search-{PROMPT}-{CONFIG}-*"] for s in SPLITS}
if "--with-selection" in sys.argv and PROMPT == "exabase" and CONFIG == "final2":
    OURS["1m"] += ["1m-search-exabase-t35-a", "1m-search-exabase-t35-b"]
    OURS["10m"] += ["10m-search-exabase-t34-user1-time-a", "10m-search-exabase-t34-user1-time-b"]
# Replays of the unmodified reference evidence: the first ones (2026-11-10) and the ones made on the day of the reported
# runs (2026-11-12). By default they are pooled; --first-replays and --same-day take one set.
FIRST_REPLAYS = (
    {
        "100k": ["replay-100k-raw_x3"],
        "500k": ["replay-500k-raw_x3"],
        "1m": ["replay-1m-raw", "replay-1m-raw_x3"],
        "10m": ["replay-10m-raw", "replay-10m-raw_more"],
    }
    if PROMPT == "exabase"
    else {s: [f"replay-{s}-raw_paper", f"replay-{s}-raw_paper2"] for s in SPLITS}
)
SAME_DAY_REPLAYS = {
    s: [f"replay-{s}-raw_1112" if PROMPT == "exabase" else f"replay-{s}-raw_paper_1112"] for s in SPLITS
}
REPLAY = {s: FIRST_REPLAYS[s] + SAME_DAY_REPLAYS[s] for s in SPLITS}
if "--first-replays" in sys.argv:
    REPLAY = FIRST_REPLAYS
if "--same-day" in sys.argv:
    REPLAY = SAME_DAY_REPLAYS
# --ref VARIANT compares against the reference evidence re-presented (replay_reference.py variants time, ourfmt-time):
# a robustness check that OpenCrawl's lead is not only a presentation effect.
if "--ref" in sys.argv:
    variant = sys.argv[sys.argv.index("--ref") + 1]
    REPLAY = {s: [f"replay-{s}-{variant}_x3" if PROMPT == "exabase" else f"replay-{s}-{variant}_paper"] for s in SPLITS}


# --route or: both systems answered through OpenRouter (the reference harness's route), same judge as everywhere else.
if "--route" in sys.argv and sys.argv[sys.argv.index("--route") + 1] == "or":
    REPLAY = {s: [f"replay-{s}-raw_or", f"replay-{s}-raw_or2"] for s in SPLITS}


def load():
    data = {}
    for split in SPLITS:
        ours, failed = {}, 0
        dirs = sorted(
            (d for pat in OURS[split] for d in paths.run_dirs(pat) if (d / "summary.json").exists()),
            key=lambda d: d.name,
        )
        for d in dirs:
            for r in paths.read_rows(d):
                ours.setdefault(r["questionId"], {"category": r["category"], "scores": []})["scores"].append(r["score"])
                failed += bool(r.get("error"))
        replay = {}
        for d in REPLAY[split]:
            if paths.find_run(d):
                for r in paths.read_rows(d):
                    replay.setdefault(r["questionId"], {"category": r["category"], "scores": []})["scores"] += r[
                        "scores"
                    ]
        published = (
            {r["questionId"]: r for r in paths.read_rows(f"published-answers-{split}")} if PROMPT == "exabase" else {}
        )
        data[split] = {
            "ours": ours,
            "replay": replay,
            "published": published,
            "dirs": dirs,
            "failed": failed,
            "run_means": [st.mean(r["score"] for r in paths.read_rows(d)) for d in dirs],
        }
    return data


def mean(d):
    return st.mean(st.mean(v["scores"]) for v in d.values())


def bootstrap(pairs, n=10000, seed=7):
    rng = random.Random(seed)
    k = len(pairs)
    diffs = []
    for _ in range(n):
        sample = [pairs[rng.randrange(k)] for _ in range(k)]
        diffs.append(st.mean(a - b for a, b in sample))
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)], sum(d > 0 for d in diffs) / n


def points(value, digits=2):
    """A score in points, or a dash where the reference system published no answers under this prompt."""
    return "—" if value != value else f"{100 * value:.{digits}f}"


def main():
    data = load()
    print(
        "| Split (questions) | OpenCrawl | Reference evidence, same answer call | Δ (95% CI, paired bootstrap) | P(Δ>0) | Reference published answers | OpenCrawl runs | failed |"
    )
    print("|---|---:|---:|---|---:|---:|---|---:|")
    allpairs = []
    tot = {"ours": 0, "replay": 0, "pub": 0, "n": 0}
    for split in SPLITS:
        d = data[split]
        if not d["ours"] or not d["replay"]:
            print(f"| {split.upper()} | not run | | | | | | |")
            continue
        common = sorted(set(d["ours"]) & set(d["replay"]))
        pairs = [(st.mean(d["ours"][q]["scores"]), st.mean(d["replay"][q]["scores"])) for q in common]
        lo, hi, p = bootstrap(pairs)
        allpairs += pairs
        o, r = st.mean(a for a, _ in pairs), st.mean(b for _, b in pairs)
        pub = st.mean(x["score"] for x in d["published"].values()) if d["published"] else float("nan")
        tot["ours"] += o * len(pairs)
        tot["replay"] += r * len(pairs)
        tot["pub"] += pub * len(pairs)
        tot["n"] += len(pairs)
        runs = ", ".join(f"{100 * m:.1f}" for m in d["run_means"])
        nrep = len(next(iter(d["replay"].values()))["scores"])
        print(
            f"| {split.upper()} ({len(pairs)}) | **{100 * o:.2f}** | {100 * r:.2f} ({nrep} runs) | {100 * (o - r):+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} | {points(pub)} | {runs} | {d['failed']} |"
        )
    if allpairs:
        lo, hi, p = bootstrap(allpairs)
        n = tot["n"]
        print(
            f"| **All ({n})** | **{100 * tot['ours'] / n:.2f}** | {100 * tot['replay'] / n:.2f} | {100 * (tot['ours'] - tot['replay']) / n:+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} | {points(tot['pub'] / n)} | | |"
        )
    print()
    if PROMPT == "exabase":
        # OpenCrawl against the reference system's published answers themselves (same judge, three judge passes):
        # is OpenCrawl behind, tied or ahead of the published answer set?
        print("| Split | OpenCrawl | Reference published answers | Δ (95% CI, paired bootstrap) | P(Δ>0) |")
        print("|---|---:|---:|---|---:|")
        everything = []
        for split in SPLITS:
            d = data[split]
            if not d["ours"] or not d["published"]:
                continue
            common = sorted(set(d["ours"]) & set(d["published"]))
            pairs = [(st.mean(d["ours"][q]["scores"]), d["published"][q]["score"]) for q in common]
            lo, hi, p = bootstrap(pairs)
            everything += pairs
            o, b = st.mean(a for a, _ in pairs), st.mean(b for _, b in pairs)
            print(
                f"| {split.upper()} ({len(pairs)}) | {100 * o:.2f} | {100 * b:.2f} | {100 * (o - b):+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} |"
            )
        if everything:
            lo, hi, p = bootstrap(everything)
            o, b = st.mean(a for a, _ in everything), st.mean(b for _, b in everything)
            print(
                f"| **All ({len(everything)})** | {100 * o:.2f} | {100 * b:.2f} | {100 * (o - b):+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f}) | {p:.3f} |"
            )
        print()
    for split in SPLITS:
        d = data[split]
        if not d["ours"] or not d["replay"]:
            continue
        cats = sorted({v["category"] for v in d["ours"].values()})
        print(f"**{split.upper()} by ability** (OpenCrawl / reference evidence / reference published answers)\n")
        print("| Ability | OpenCrawl | Reference evidence | Published answers |")
        print("|---|---:|---:|---:|")
        for c in cats:
            o = st.mean(st.mean(v["scores"]) for v in d["ours"].values() if v["category"] == c)
            r = st.mean(st.mean(v["scores"]) for v in d["replay"].values() if v["category"] == c)
            p = (
                st.mean(v["score"] for v in d["published"].values() if v["category"] == c)
                if d["published"]
                else float("nan")
            )
            print(f"| {c} | {100 * o:.1f} | {100 * r:.1f} | {points(p, 1)} |")
        print()


if __name__ == "__main__":
    main()
