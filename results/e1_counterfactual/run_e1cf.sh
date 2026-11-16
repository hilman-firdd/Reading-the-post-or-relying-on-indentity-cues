#!/bin/zsh
# E1-CF runs (protocol: PROTOCOL.md). Same configuration as the main runs; resumable; never writes to runs/.
# Ollama must be running with: OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024 OLLAMA_KEEP_ALIVE=30m ollama serve
set -e
cd "$(dirname "$0")/../.."
P=~/.venvs/modkit/bin/python; ITEMS=results/e1_counterfactual/items_e1cf.jsonl; OUT=results/e1_counterfactual/runs
mkdir -p $OUT
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
[ -f $OUT/cf_char-LR.jsonl ] || $P baseline.py --data data/dataset.json --splits data/post_id_divisions.json --items $ITEMS --out-prefix $OUT/cf
for m in qwen2.5:7b llama3.1:8b gemma2:9b; do
  for p in direct evidence; do
    log "run $m $p"; $P run_llm.py run --items $ITEMS --model $m --prompt $p --workers 6 --max-tokens 256 --out $OUT/${m//:/_}_$p.jsonl
  done
done
log "E1CF DONE"
