#!/bin/bash
# run_ablation.sh — prompt ablation (reviewer R3): which part of the evidence prompt changes the verdicts?
#
# The two original prompts differ in three ways. The ablation adds them one at a time:
#   direct
#   abl_quote_first  = direct + A  (two steps: quote the relevant words first; quotes first in the JSON)
#   abl_quote_only   = A + B       (decide ONLY from the quoted words and the policy)
#   evidence         = A + B + C   (answer 'insufficient' when the quoted words do not settle the case)
# tests/test_prompt_ablation.py verifies that A+B+C reproduces the evidence prompt exactly and that the steps
# differ only in the stated parts.
#
# Start Ollama exactly as for run_repeats.sh, then:
#   export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024
#   nohup caffeinate -is ./run_ablation.sh > logs/ablation.log 2>&1 &
#   python analysis_systems.py ablation       -> results/ablation/summary.md
#
# Defaults: Qwen2.5 and Gemma 2 only (Llama 3.1 refuses most items, so its answers come from a self-selected subset),
# all 4,233 items. Override with MODELS="..." or MRS="ORIG,E1,E2,R1,R2" (faster; keep the same MRS for every model).
# Interrupted or stopped? Run the same command again: done items are kept, failed calls are asked again.
set -e
cd "$(dirname "$0")"
. ./run_common.sh
MODELS_=(${MODELS:-qwen2.5:7b gemma2:9b})
MRS_ARG=(); [ -n "$MRS" ] && MRS_ARG=(--mrs "$MRS")
check_python; check_ollama; check_models "${MODELS_[@]}"
log "models=${MODELS_[*]} mrs=${MRS:-all}"
mkdir -p runs_ablation logs
"$P" env_manifest.py --out "runs_ablation/manifest_$(date +%Y%m%d_%H%M%S).json" --note "prompt ablation ${MRS:-all MRs}"
for m in "${MODELS_[@]}"; do
  for p in abl_quote_first abl_quote_only; do
    run_one items_llm600.jsonl "$m" "$p" "runs_ablation/${m//:/_}_$p.jsonl" ${MRS_ARG[@]+"${MRS_ARG[@]}"}
  done
done
log "ABLATION DONE"
