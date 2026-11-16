#!/bin/zsh
# Full LLM pipeline from README (resumable). Start Ollama with: OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024 OLLAMA_KEEP_ALIVE=30m ollama serve
# Then:  nohup caffeinate -is ./run_all.sh > logs/run_all.log 2>&1 &
# Re-run the same command after an interruption: finished steps are skipped, runs resume where they stopped.
set -e
cd "$(dirname "$0")"
P=${PYTHON:-$HOME/.venvs/modkit/bin/python}; ITEMS=items_llm600.jsonl; mkdir -p runs results logs
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 1) paraphrase I3 (gemma2 paraphrases, qwen2.5 judges; llama3.1 refuses this task); keep an untouched copy first
[ -f items_llm600.orig.jsonl ] || cp $ITEMS items_llm600.orig.jsonl
if grep -qE '"pending_(paraphrase|judge)": true' $ITEMS; then
  log "paraphrase start"; $P run_llm.py paraphrase --items $ITEMS --model gemma2:9b --judge-model qwen2.5:7b; log "paraphrase done"
fi

# 2) human-validation workbook (HITL: E1,E2,I1,I3 + ambiguous R2) - never overwrite one that may already be filled
[ -f human_validation.xlsx ] || $P run_llm.py export --items $ITEMS --out human_validation.xlsx

# 3) local baselines on the same 600-post items (comparison systems)
[ -f runs/llm600_char-LR.jsonl ] || $P baseline.py --data data/dataset.json --splits data/post_id_divisions.json --items $ITEMS --out-prefix runs/llm600

# 4) every model x prompt (resumable)
for m in qwen2.5:7b llama3.1:8b gemma2:9b; do
  for p in direct evidence; do
    log "run $m $p"; $P run_llm.py run --items $ITEMS --model $m --prompt $p --out runs/${m//:/_}_$p.jsonl --workers 6 --verbose
  done
done

# 5) evaluation
RUNS=(runs/*_direct.jsonl runs/*_evidence.jsonl runs/llm600_word-LR.jsonl runs/llm600_char-LR.jsonl)
$P evaluate.py --items $ITEMS --runs $RUNS --out results/llm600.json
$P evaluate.py --items $ITEMS --runs $RUNS --lenient --out results/llm600_lenient.json
$P analysis_residual.py --items $ITEMS --runs $RUNS --out results/residual_llm600.json
$P revise_eval.py --items $ITEMS --runs $RUNS --out results/revised_llm600.json
log "ALL DONE"
