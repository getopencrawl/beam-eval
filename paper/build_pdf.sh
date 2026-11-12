#!/usr/bin/env bash
# Build opencrawl-beam.pdf from opencrawl-beam.md with pandoc (>= 3.2) and typst (>= 0.12). No LaTeX needed.
#   PANDOC=/path/to/pandoc TYPST=/path/to/typst bash build_pdf.sh [--png]   (--png also writes page images to /tmp)
set -euo pipefail
cd "$(dirname "$0")"
PANDOC=${PANDOC:-pandoc}; TYPST=${TYPST:-typst}
tmp=$(mktemp -d)
# The title block comes from metadata; drop the Markdown title, subtitle and byline lines.
awk 'NR==1 && /^# /{next} /^\*\*Point-in-time, role-aware/{next} /^\*OpenCrawl team/{next} {print}' opencrawl-beam.md > "$tmp/body.md"
cat > "$tmp/header.typ" <<'TYP'
#set page(paper: "a4", margin: (x: 1.9cm, y: 2.1cm), numbering: "1")
#set text(size: 10pt)
#set par(justify: true)
#show table: set text(size: 7.6pt)
#show table: set par(justify: false)
#set table(inset: (x: 4pt, y: 3.5pt), stroke: 0.4pt + luma(170))
#show raw: set text(size: 8.5pt)
#show heading.where(level: 1): set block(above: 1.4em, below: 0.7em)
#show figure: set block(breakable: true)
TYP
"$PANDOC" "$tmp/body.md" -f gfm -t typst --standalone --shift-heading-level-by=-1 \
  --metadata title="Searchable Agent Memory at Ten Million Tokens" \
  --metadata subtitle="Point-in-time, role-aware and note-augmented retrieval in OpenCrawl, and a controlled way to compare memory systems" \
  --metadata author="OpenCrawl team" --metadata date="November 2026" \
  --include-in-header "$tmp/header.typ" -o "$tmp/paper.typ"
cp figure-lead.svg "$tmp/"
"$TYPST" compile "$tmp/paper.typ" opencrawl-beam.pdf
if [ "${1:-}" = "--png" ]; then "$TYPST" compile --ppi 70 "$tmp/paper.typ" "$tmp/paper-page-{0p}.png"; echo "page images in $tmp"; fi
echo "wrote $(pwd)/opencrawl-beam.pdf"
