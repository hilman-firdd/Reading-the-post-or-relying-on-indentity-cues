#!/bin/bash
# run_extra_models.sh — add models with the SAME items, prompts and uniform setting (reviewer R3).
#
#   ollama pull mistral:7b                                  (pull every model first; pick models that fit in memory)
#   export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024
#   MODELS="mistral:7b" nohup caffeinate -is ./run_extra_models.sh > logs/extra.log 2>&1 &
#   The manifest records the digest and quantisation of every installed model.
#
# Writes runs_extra/main/<model>_<prompt>.jsonl (4,233 items) and runs_extra/e1cf/<model>_<prompt>.jsonl (440 items).
# Analysis:  python analysis_systems.py extra   -> results/extra_models/summary.md
#            python analyze_e1_counterfactual.py --runs-dir runs_extra/e1cf --out-dir results/extra_models/e1cf \
#                   --systems "mistral:7b|direct,mistral:7b|evidence"
# The pre-specified E1-CF decision rule covers only the original four Qwen2.5/Gemma 2 conditions; results for added
# models are reported descriptively (Holm over the added conditions).
# Interrupted or stopped? Run the same command again: done items are kept, failed calls are asked again.
set -e
cd "$(dirname "$0")"
. ./run_common.sh
[ -n "$MODELS" ] || die 'set MODELS, e.g. MODELS="mistral:7b" ./run_extra_models.sh'
MODELS_=($MODELS)
PROMPTS_=(${PROMPTS:-direct evidence})
check_python; check_prompts "${PROMPTS_[@]}"; check_ollama; check_models "${MODELS_[@]}"
log "models=${MODELS_[*]} prompts=${PROMPTS_[*]}"
mkdir -p runs_extra/main runs_extra/e1cf logs
"$P" env_manifest.py --out "runs_extra/manifest_$(date +%Y%m%d_%H%M%S).json" --note "extra models: ${MODELS_[*]}"
for m in "${MODELS_[@]}"; do
  for p in "${PROMPTS_[@]}"; do
    run_one results/e1_counterfactual/items_e1cf.jsonl "$m" "$p" "runs_extra/e1cf/${m//:/_}_$p.jsonl"
    run_one items_llm600.jsonl "$m" "$p" "runs_extra/main/${m//:/_}_$p.jsonl"
  done
done
log "EXTRA MODELS DONE"
