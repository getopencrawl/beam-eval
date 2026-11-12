"""The README's chart: OpenCrawl and the reference system on BEAM, by conversation length, under BEAM's own prompt.

Form: paired horizontal bars from a zero baseline (the scores themselves), with the lead and its 95% interval in a
column beside them. OpenCrawl is the subject, so it takes the accent colour and the reference takes the neutral grey.
The two colours were checked for separation under colour-vision deficiency and for at least 3:1 contrast against the
light and the dark surface.

The numbers are read from results/expected.json, the values that verify.py recomputes from the per-question records
and checks. The interval shown is the most cautious of the three that verify.py computes: a t interval over conversations.

    python make_chart.py                              # beam-head-to-head.svg, .png and -dark.png (PNGs need resvg_py)
"""
import json
from html import escape
from pathlib import Path

QUOTED = json.loads((Path(__file__).resolve().parent.parent / "results" / "expected.json").read_text(encoding="utf-8"))
TABLE = "BEAM's own prompt: reported system against the reference evidence"
LABELS = (("100k", "100K tokens", "~290 messages · 400 questions"), ("500k", "500K tokens", "~1,100 messages · 700 questions"),
          ("1m", "1M tokens", "~2,100 messages · 700 questions"), ("10m", "10M tokens", "~21,000 messages · 200 questions"),
          ("all", "All lengths", "2,000 questions"))
# label, sub-label, OpenCrawl, reference evidence, lead, low and high of the 95% t interval over conversations
ROWS = [(label, sub, *(QUOTED[f"{TABLE} | {key}"][i] for i in (1, 2, 3, 8, 9))) for key, label, sub in LABELS]
LIGHT = {"surface": "#fcfcfb", "t1": "#0b0b0b", "t2": "#52514e", "t3": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
         "ours": "#2a78d6", "ref": "#898781"}
DARK = {"surface": "#1a1a19", "t1": "#f0efec", "t2": "#c3c2b7", "t3": "#898781", "grid": "#2c2c2a", "axis": "#383835",
        "ours": "#3987e5", "ref": "#898781"}
FONT = "'Noto Sans', 'Liberation Sans', system-ui, sans-serif"

W, H = 1600, 900
PAD = 72
PLOT_X0, PLOT_X1 = 430, 1230          # the score axis, 0 to DOMAIN
DOMAIN = 70
TOP, BAND, GAP = 214, 104, 22          # first row's top, row height, space before the pooled row
BAR = 24                               # bar thickness (the cap for a bar)
LEAD_X = W - PAD                       # right edge of the lead column


def x(value: float) -> float:
    return PLOT_X0 + value / DOMAIN * (PLOT_X1 - PLOT_X0)


def bar(x0: float, x1: float, y: float, fill: str, tip: str) -> str:
    """A bar that is square at the baseline and rounded (4px) at the data end."""
    r = 4
    d = (f"M{x0:.1f},{y:.1f} H{x1 - r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} V{y + BAR - r:.1f} "
         f"Q{x1:.1f},{y + BAR:.1f} {x1 - r:.1f},{y + BAR:.1f} H{x0:.1f} Z")
    return f'<path d="{d}" fill="{fill}"><title>{escape(tip)}</title></path>'


def signed(value: float) -> str:
    return f"{value:+.2f}"  # ASCII minus: the PNG renderer's font has no U+2212


def build(c: dict, reference: str) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="t d" font-family="{FONT}">',
           '<title id="t">OpenCrawl and the reference memory system on the BEAM benchmark, by conversation length</title>',
           '<desc id="d">Paired horizontal bars of BEAM scores out of 100 under the benchmark\'s own answer prompt. '
           + " ".join(f"{label}: OpenCrawl {ours:.2f}, reference {ref:.2f}, lead {signed(lead)} "
                      f"(95% interval {signed(low)} to {signed(high)})." for label, _, ours, ref, lead, low, high in ROWS)
           + "</desc>",
           f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>',
           f'<text x="{PAD}" y="92" font-size="46" font-weight="700" fill="{c["t1"]}">'
           f'OpenCrawl and the reference system on BEAM</text>',
           f'<text x="{PAD}" y="134" font-size="21" fill="{c["t2"]}">Long-term memory benchmark (ICLR 2026) · 2,000 questions · '
           f'the benchmark’s own answer prompt · same answer model and judge for both</text>']
    # legend: a swatch and a name per series, in text ink; the lead column's header shares its line
    ly = 178
    lx = PAD
    for key, name in (("ours", "OpenCrawl"), ("ref", reference + " (its published evidence, replayed)")):
        out.append(f'<rect x="{lx}" y="{ly - 15}" width="30" height="16" rx="3" fill="{c[key]}"/>'
                   f'<text x="{lx + 42}" y="{ly}" font-size="23" fill="{c["t2"]}">{escape(name)}</text>')
        lx += 42 + 13.0 * len(name) + 44
    out.append(f'<text x="{LEAD_X}" y="{ly}" font-size="21" text-anchor="end" fill="{c["t3"]}">OpenCrawl’s lead, points</text>')
    out.append(f'<text x="{LEAD_X}" y="{ly + 21}" font-size="15" text-anchor="end" fill="{c["t3"]}">lighter figure: the interval includes zero</text>')

    bottom = TOP + BAND * len(ROWS) + GAP
    for tick in (0, 20, 40, 60):  # hairlines; the zero baseline one step stronger
        out.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{TOP}" y2="{bottom}" stroke="{c["axis" if tick == 0 else "grid"]}" stroke-width="1"/>'
                   f'<text x="{x(tick):.1f}" y="{bottom + 28}" font-size="19" text-anchor="middle" fill="{c["t3"]}">{tick}</text>')
    out.append(f'<text x="{x(0) - 22:.1f}" y="{bottom + 28}" font-size="19" text-anchor="end" fill="{c["t3"]}">Score out of 100</text>')

    for index, (label, sub, ours, ref, lead, low, high) in enumerate(ROWS):
        last = index == len(ROWS) - 1
        top = TOP + BAND * index + (GAP if last else 0)
        mid = top + BAND / 2
        if last:  # a hairline sets the pooled row apart from the four lengths
            out.append(f'<line x1="{PAD}" x2="{W - PAD}" y1="{top - GAP / 2:.1f}" y2="{top - GAP / 2:.1f}" stroke="{c["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{PAD}" y="{mid - 3:.1f}" font-size="30" font-weight="700" fill="{c["t1"]}">{escape(label)}</text>'
                   f'<text x="{PAD}" y="{mid + 26:.1f}" font-size="19" fill="{c["t3"]}">{escape(sub)}</text>')
        y_ours, y_ref = mid - BAR - 3, mid + 3
        out.append(bar(x(0), x(ours), y_ours, c["ours"], f"{label}: OpenCrawl {ours:.2f}"))
        out.append(bar(x(0), x(ref), y_ref, c["ref"], f"{label}: {reference} {ref:.2f}"))
        out.append(f'<text x="{x(ours) + 12:.1f}" y="{y_ours + 20:.1f}" font-size="25" font-weight="700" fill="{c["t1"]}">{ours:.2f}</text>'
                   f'<text x="{x(ref) + 12:.1f}" y="{y_ref + 20:.1f}" font-size="25" fill="{c["t2"]}">{ref:.2f}</text>')
        clear = low > 0 or high < 0  # a lead whose interval includes zero is drawn lighter
        out.append(f'<text x="{LEAD_X}" y="{mid + 4:.1f}" font-size="42" font-weight="{700 if clear else 400}" text-anchor="end" '
                   f'fill="{c["t1"] if clear else c["t2"]}">{signed(lead)}</text>'
                   f'<text x="{LEAD_X}" y="{mid + 32:.1f}" font-size="18" text-anchor="end" fill="{c["t3"]}">95% interval {signed(low)} to {signed(high)}</text>')

    fy = bottom + 74
    out.append(f'<text x="{PAD}" y="{fy}" font-size="18" fill="{c["t3"]}">Reference: the evidence a published memory system released for each question, '
               f'replayed through the same answer model and the same judge.</text>')
    out.append(f'<text x="{PAD}" y="{fy + 27}" font-size="18" fill="{c["t3"]}">Answer model gpt-5.6-luna without reasoning, one call per question. '
               f'Interval: 95% t interval over conversations. BEAM: Tavakoli et al., arXiv 2510.27246.</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    here = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."
    reference = "Reference memory system"
    light, dark = build(LIGHT, reference), build(DARK, reference)
    open(f"{here}/beam-head-to-head.svg", "w").write(light)
    try:
        import resvg_py
        for name, svg in (("beam-head-to-head.png", light), ("beam-head-to-head-dark.png", dark)):
            open(f"{here}/{name}", "wb").write(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=W, sans_serif_family="Noto Sans")))
        print("wrote beam-head-to-head.svg, beam-head-to-head.png, beam-head-to-head-dark.png")
    except ImportError:
        print("wrote beam-head-to-head.svg (install resvg_py for the PNG files)")
