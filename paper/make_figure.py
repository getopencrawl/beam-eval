"""Figure 1 of the paper: OpenCrawl's lead over the reference evidence, with 95% intervals, by conversation length
and answer prompt. Writes figure-lead.svg (light, with a dark-scheme override) next to this file.

The numbers are read from results/expected.json, the values that `verify.py` recomputes from the per-question
records and checks; they are in Tables 3 and 4 of the paper, which serve as the table view of this chart.

    python make_figure.py            # figure-lead.svg
    python make_figure.py --dark     # also writes figure-lead-dark.svg (dark colours as the base, for inspection)
"""
import json
import math
import sys
from html import escape
from pathlib import Path

QUOTED = json.loads((Path(__file__).resolve().parent.parent / "results" / "expected.json").read_text(encoding="utf-8"))


def lead(prompt: str, key: str) -> tuple:
    """(lead, low, high) of the reported comparison, with the 95% t interval over conversations."""
    row = QUOTED[f"{prompt}: reported system against the reference evidence | {key}"]
    return row[3], row[8], row[9]


# label, questions, own prompt (lead, low, high), annotation-aided prompt (lead, low, high)
ROWS = [(label, sub, lead("BEAM's own prompt", key), lead("Annotation-aided prompt", key))
        for key, label, sub in (("100k", "100K", "400 questions"), ("500k", "500K", "700 questions"), ("1m", "1M", "700 questions"),
                                ("10m", "10M", "200 questions"), ("all", "All splits", "2,000 questions"))]
SERIES = [("s1", "BEAM's own prompt (no annotations)", "BEAM's own prompt"),
          ("s2", "Annotation-aided prompt", "annotation-aided prompt")]
LIGHT = {"surface": "#fcfcfb", "t1": "#0b0b0b", "t2": "#52514e", "t3": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
         "s1": "#2a78d6", "s2": "#eb6834"}
DARK = {"surface": "#1a1a19", "t1": "#f0efec", "t2": "#c3c2b7", "t3": "#898781", "grid": "#2c2c2a", "axis": "#383835",
        "s1": "#3987e5", "s2": "#d95926"}

W, LEFT, RIGHT, TOP, BAND, GAP = 860, 150, 40, 100, 58, 14
LOW = min(low for _, _, own, aided in ROWS for _, low, _ in (own, aided))
HIGH = max(high for _, _, own, aided in ROWS for _, _, high in (own, aided))
X0, X1 = float(min(-2, 2 * math.floor(LOW / 2))), float(max(10, 2 * math.ceil(HIGH / 2))) + 1  # even ticks, a little air on the right
PLOT_W = W - LEFT - RIGHT
BOTTOM = TOP + BAND * len(ROWS) + GAP
H = BOTTOM + 56


def x(value: float) -> float:
    return LEFT + (value - X0) / (X1 - X0) * PLOT_W


def above_zero() -> str:
    """Which of the plotted intervals lie wholly above zero, in words, for the figure's description."""
    parts = []
    for index, article in ((0, ""), (1, "the ")):
        rows = [("all splits together" if label == "All splits" else label) for label, _, *leads in ROWS if leads[index][1] > 0]
        where = "for no row" if not rows else "at " + (", ".join(rows[:-1]) + " and for " + rows[-1] if len(rows) > 1 else rows[0])
        parts.append(f"under {article}{SERIES[index][2]} the interval lies wholly above zero {where}")
    text = "; ".join(parts) + "."
    return text[0].upper() + text[1:]


def css(colors: dict) -> str:
    return (f".surface{{fill:{colors['surface']}}} .t1{{fill:{colors['t1']}}} .t2{{fill:{colors['t2']}}} .t3{{fill:{colors['t3']}}} "
            f".grid{{stroke:{colors['grid']}}} .axis{{stroke:{colors['axis']}}} "
            f".s1{{stroke:{colors['s1']};fill:{colors['s1']}}} .s2{{stroke:{colors['s2']};fill:{colors['s2']}}} "
            f".ring{{stroke:{colors['surface']}}}")


def build(base: dict, override: dict | None) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="fig-title fig-desc" font-family="system-ui, -apple-system, \'Segoe UI\', sans-serif">',
           '<title id="fig-title">OpenCrawl\'s lead over the reference evidence on BEAM, by conversation length and answer prompt</title>',
           '<desc id="fig-desc">Dot and interval chart. For each conversation length and for all splits together, the lead of OpenCrawl '
           'over the reference system\'s evidence in points, with its 95% interval, under BEAM\'s own prompt and under the '
           'annotation-aided prompt. ' + escape(above_zero(), quote=False) + '</desc>',
           "<style>" + css(base) + (" @media (prefers-color-scheme: dark){" + css(override) + "}" if override else "") + "</style>",
           f'<rect class="surface" width="{W}" height="{H}"/>',
           f'<text class="t1" x="{LEFT - 126}" y="30" font-size="15" font-weight="600">OpenCrawl\'s lead over the reference evidence, in points</text>',
           f'<text class="t2" x="{LEFT - 126}" y="50" font-size="12">Same answer model and judge for both systems; dot = mean lead, line = 95% t interval over conversations</text>']
    # legend: a line key with its dot per series, labels in text ink
    lx = LEFT - 126
    for cls, name, _ in SERIES:
        out.append(f'<line class="{cls}" x1="{lx}" x2="{lx + 26}" y1="74" y2="74" stroke-width="2" stroke-linecap="round"/>'
                   f'<circle class="{cls}" cx="{lx + 13}" cy="74" r="4.5" stroke="none"/>'
                   f'<text class="t2" x="{lx + 34}" y="78" font-size="12">{escape(name)}</text>')
        lx += 34 + 7.0 * len(name) + 28
    # grid: hairlines every two points, the zero baseline one step stronger
    for tick in range(int(X0), int(X1), 2):
        cls = "axis" if tick == 0 else "grid"
        out.append(f'<line class="{cls}" x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{TOP - 6}" y2="{BOTTOM}" stroke-width="1"/>')
        label = "0" if tick == 0 else f"{tick:+d}".replace("-", "−")
        out.append(f'<text class="t3" x="{x(tick):.1f}" y="{BOTTOM + 18}" font-size="11" text-anchor="middle" '
                   f'style="font-variant-numeric:tabular-nums">{label}</text>')
    out.append(f'<text class="t2" x="{x(4.5):.1f}" y="{BOTTOM + 40}" font-size="12" text-anchor="middle">'
               f'Lead over the reference evidence (points; right of 0 = OpenCrawl ahead)</text>')
    for index, (label, sub, own, aided) in enumerate(ROWS):
        last = index == len(ROWS) - 1
        top = TOP + BAND * index + (GAP if last else 0)
        mid = top + BAND / 2
        if last:  # a hairline sets the pooled row apart from the four splits
            out.append(f'<line class="grid" x1="{LEFT - 126}" x2="{W - RIGHT}" y1="{top - GAP / 2:.1f}" y2="{top - GAP / 2:.1f}" stroke-width="1"/>')
        out.append(f'<text class="t1" x="{LEFT - 126}" y="{mid - 1:.1f}" font-size="13" font-weight="600">{escape(label)}</text>'
                   f'<text class="t3" x="{LEFT - 126}" y="{mid + 15:.1f}" font-size="11">{escape(sub)}</text>')
        for (cls, name, short), (lead, low, high), dy in zip(SERIES, (own, aided), (-10, 10)):
            y = mid + dy
            tip = f"{label}, {name}: {lead:+.2f} points (95% interval {low:+.2f} to {high:+.2f})".replace("-", "−")
            out.append(f'<g><title>{escape(tip)}</title>'
                       f'<rect x="{x(low) - 6:.1f}" y="{y - 12:.1f}" width="{x(high) - x(low) + 12:.1f}" height="24" fill="none" pointer-events="all"/>'
                       f'<line class="{cls}" x1="{x(low):.1f}" x2="{x(high):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke-width="2" stroke-linecap="round"/>'
                       f'<circle class="{cls} ring" cx="{x(lead):.1f}" cy="{y:.1f}" r="5.5" stroke-width="2"/></g>')
            if last:  # direct labels on the pooled row only: the value in primary ink, the series name beside it
                out.append(f'<text x="{x(high) + 12:.1f}" y="{y + 4:.1f}" font-size="12"><tspan class="t1" font-weight="600">'
                           f'{lead:+.2f}</tspan><tspan class="t2" dx="6">{escape(short)}</tspan></text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    here = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."
    open(f"{here}/figure-lead.svg", "w").write(build(LIGHT, DARK))
    if "--dark" in sys.argv:
        open(f"{here}/figure-lead-dark.svg", "w").write(build(DARK, None))
    print("wrote figure-lead.svg")
