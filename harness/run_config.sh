#!/usr/bin/env bash
# Run one of the three reported configurations: three answer runs per conversation length under one prompt.
#
#   bash run_config.sh <base|base-fact-cards|full-system> <paper|exabase> [tag]
#
#   paper    BEAM's own answer prompt (no dataset annotations)
#   exabase  the annotation-aided prompt
#
# Runs are written to ../results/local/<length>-search-<prompt>-<tag>-<a|b|c>. The default tag is "my-<config tag>",
# so a rerun never collides with a published run; compare it with the reference evidence through
#   python final_compare.py --config <tag> [--paper]
#
# SAVE_CONTEXT=a stores the exact prompt the answer model received with every record of run a (large files).
#
# The context cap per length is the reference system's mean context size (results/reference/context-tokens.json).
# At most five runs go at once: more than that made the search time out on an 8-vCPU machine.
set -euo pipefail
cd "$(dirname "$0")"
[ -f env.sh ] && . ./env.sh
export BEAM_LLM_CONCURRENCY=${BEAM_LLM_CONCURRENCY:-8}
PYTHON=${PYTHON:-python}

BASE="--expand 3 --follow-up 3 --point-in-time --memories --deep 12 --deep-whole --memory-share 0.2 --user-pass 1.0 --order time"
case "${1:-}" in
  base)            FLAGS="$BASE";                                                        CONFIG=final2 ;;
  base-fact-cards) FLAGS="$BASE --facts --clean-notes";                                  CONFIG=final3 ;;
  full-system)     FLAGS="$BASE --facts --clean-notes --conflicts --conflicts-share 0.03"; CONFIG=final5 ;;
  *) echo "usage: bash run_config.sh <base|base-fact-cards|full-system> <paper|exabase> [tag]" >&2; exit 2 ;;
esac
PROMPT=${2:?paper or exabase}
TAG=${3:-my-$CONFIG}
mkdir -p logs

run() {  # <length> <context cap> <a|b|c>
  local extra=""
  [ "${SAVE_CONTEXT:-}" = "$3" ] && extra="--save-context"
  "$PYTHON" run.py --split "$1" $FLAGS $extra --prompt "$PROMPT" --context-tokens "$2" --tag "$TAG-$3" > "logs/$TAG-$PROMPT-$1-$3.log" 2>&1
}

run 10m 10467 a & run 10m 10467 b & run 10m 10467 c & run 1m 11339 a & run 1m 11339 b &
wait
run 1m 11339 c & run 500k 11749 a & run 500k 11749 b & run 500k 11749 c & run 100k 11001 a &
wait
run 100k 11001 b & run 100k 11001 c &
wait
echo "$TAG under the $PROMPT prompt: done. Compare with: python final_compare.py --config $TAG$([ "$PROMPT" = paper ] && echo ' --paper')"
