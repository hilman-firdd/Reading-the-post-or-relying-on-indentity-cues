#!/bin/bash
# run_repeats.sh — repeat the LLM runs with ONE uniform setting to measure run-to-run variation (reviewer R3).
#
# The original runs in runs/ (and results/e1_counterfactual/runs/) count as repetition 1. This script adds
# repetitions 2 and 3 (change with REPS="2 3 4"). Nothing in runs/ or results/ is overwritten.
#
#   1) Start Ollama in ANOTHER terminal with exactly this setting and leave it running:
#        OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024 OLLAMA_KEEP_ALIVE=30m ollama serve
#   2) In this terminal (the export line makes the manifest record the same setting):
#        export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024
#        nohup caffeinate -is ./run_repeats.sh cf   > logs/repeats_cf.log   2>&1 &    # E1-CF only   (~1-2 h)
#        nohup caffeinate -is ./run_repeats.sh main > logs/repeats_main.log 2>&1 &    # 4,233 items x 6 conditions per rep (long)
#      Run cf and main one after the other (or ./run_repeats.sh all), not at the same time on one laptop.
#      Interrupted or stopped? Run the same command again: done items are kept, failed calls are asked again.
#   3) python analysis_repeats.py      -> results/repeats/stability.md and stability.json
#
# Uniform setting for every call: 6 parallel slots, 1,024-token context, max 256 output tokens, temperature 0,
# seed 42, one user message. A failed call is written as GENERATION_ERROR; 20 failures in a row stop the run.
set -e
cd "$(dirname "$0")"
. ./run_common.sh
MODE=${1:-all}
case "$MODE" in cf|main|all) ;; *) die "usage: ./run_repeats.sh cf|main|all";; esac
REPS_=(${REPS:-2 3})
MODELS_=(${MODELS:-qwen2.5:7b llama3.1:8b gemma2:9b})
PROMPTS_=(${PROMPTS:-direct evidence})
for r in "${REPS_[@]}"; do case "$r" in *[!0-9]*|""|1) die "REPS must be numbers >= 2 (repetition 1 = original runs), got '$r'";; esac; done
check_python; check_prompts "${PROMPTS_[@]}"; check_ollama; check_models "${MODELS_[@]}"
log "mode=$MODE reps=${REPS_[*]} models=${MODELS_[*]} prompts=${PROMPTS_[*]}"
mkdir -p runs_repeat logs

for r in "${REPS_[@]}"; do
  mkdir -p "runs_repeat/rep$r/e1cf" "runs_repeat/rep$r/main"
  "$P" env_manifest.py --out "runs_repeat/rep$r/manifest_$(date +%Y%m%d_%H%M%S).json" --note "repetition $r, mode $MODE"
done
if [ "$MODE" = "cf" ] || [ "$MODE" = "all" ]; then
  for r in "${REPS_[@]}"; do for m in "${MODELS_[@]}"; do for p in "${PROMPTS_[@]}"; do
    run_one results/e1_counterfactual/items_e1cf.jsonl "$m" "$p" "runs_repeat/rep$r/e1cf/${m//:/_}_$p.jsonl"
  done; done; done
fi
if [ "$MODE" = "main" ] || [ "$MODE" = "all" ]; then
  for r in "${REPS_[@]}"; do for m in "${MODELS_[@]}"; do for p in "${PROMPTS_[@]}"; do
    run_one items_llm600.jsonl "$m" "$p" "runs_repeat/rep$r/main/${m//:/_}_$p.jsonl"
  done; done; done
fi
log "REPEATS DONE ($MODE)"
