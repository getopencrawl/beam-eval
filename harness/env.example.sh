# Copy to env.sh, fill in, and source it before running the harness:  . ./env.sh

export OPENAI_API_KEY=                 # answer model and judge (gpt-5.6-luna, reasoning off)
export OPENCRAWL_DEPLOY_DIR=           # deploy/ directory of a running self-hosted OpenCrawl (opencrawl-core)
export BEAM_CACHE=$HOME/.cache/beam-eval    # where the BEAM dataset is kept after its first download

# Optional
# export BEAM_LLM_CONCURRENCY=8        # model calls at once per run (default 24; 8 was used for the reported runs)
# export BEAM_REFERENCE_RESULTS=       # the reference system's published records, for replay_reference.py (not included here)
# export OPENROUTER_API_KEY=           # only with BEAM_ANSWER_API=openrouter (the API-router check)
