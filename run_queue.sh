#!/bin/bash
# run_queue.sh — ONE sequential queue for the remaining prompt-ablation runs and the E1-CF repetitions (reviewer R3).
#
# Why: running run_repeats.sh and run_ablation.sh at the same time on one GPU made Ollama swap models back and forth;
# requests timed out (ReadTimeout) and throughput fell to ~0.5 items/s. Here a single process works through the
# conditions model by model, so each model is loaded once. Same items, prompts and uniform setting as the other scripts
# (6 parallel slots, 1,024 context, max 256 output tokens, temperature 0, seed 42). Resumable: finished items are kept,
# GENERATION_ERROR records are asked again. Nothing in runs/ or results/ is touched.
#
#   export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024     (Ollama must be started with the same setting)
#   nohup caffeinate -is ./run_queue.sh > logs/queue.log 2>&1 &
#
# Battery guard: before each condition, if the laptop runs on battery at <= MIN_BATT % (default 8) the queue stops cleanly
# (exit 3). Plug in and run the same command again.
# Timing: logs/queue_times.tsv gets one line per finished condition (start, end, seconds, items done, items/s).
set -e
cd "$(dirname "$0")"
. ./run_common.sh
MIN_BATT=${MIN_BATT:-8}
check_python; check_ollama; check_models qwen2.5:7b llama3.1:8b gemma2:9b
mkdir -p runs_ablation runs_repeat logs
TIMES=logs/queue_times.tsv; [ -f "$TIMES" ] || printf "start\tend\tseconds\tmodel\tprompt\tfile\titems_in_file\tnew_items\titems_per_s\n" > "$TIMES"

battery_guard() {
  local line pct
  line=$(pmset -g batt 2>/dev/null | grep -i InternalBattery || true)
  pct=$(echo "$line" | grep -o '[0-9]*%' | head -1 | tr -d '%')
  if echo "$line" | grep -q discharging && [ -n "$pct" ] && [ "$pct" -le "$MIN_BATT" ]; then
    log "STOP: on battery at ${pct}% (<= ${MIN_BATT}%). Plug in, then run ./run_queue.sh again (resumes)."; exit 3
  fi
}

# cond ITEMS MODEL PROMPT OUT [extra args]
cond() {
  local items=$1 m=$2 p=$3 out=$4; shift 4
  battery_guard
  local t0 t1 n0 n1 s
  t0=$(date +%s); n0=$( [ -f "$out" ] && wc -l < "$out" | tr -d ' ' || echo 0 )
  run_one "$items" "$m" "$p" "$out" "$@"
  t1=$(date +%s); n1=$(wc -l < "$out" | tr -d ' '); s=$((t1 - t0)); [ "$s" -gt 0 ] || s=1
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$(date -r $t0 '+%m-%d %H:%M:%S')" "$(date -r $t1 '+%m-%d %H:%M:%S')" "$s" "$m" "$p" "$out" "$n1" "$((n1 - n0))" \
    "$(echo "scale=3; ($n1 - $n0) / $s" | bc)" >> "$TIMES"
}

CF=results/e1_counterfactual/items_e1cf.jsonl; MAIN=items_llm600.jsonl
for r in 2 3; do mkdir -p "runs_repeat/rep$r/e1cf" "runs_repeat/rep$r/main"
  "$P" env_manifest.py --out "runs_repeat/rep$r/manifest_queue_$(date +%Y%m%d_%H%M%S).json" --note "repetition $r (queue)"; done
"$P" env_manifest.py --out "runs_ablation/manifest_queue_$(date +%Y%m%d_%H%M%S).json" --note "prompt ablation (queue)"

log "QUEUE START (one model at a time)"
# ---- Qwen2.5 ----
cond $MAIN qwen2.5:7b abl_quote_first runs_ablation/qwen2.5_7b_abl_quote_first.jsonl
cond $MAIN qwen2.5:7b abl_quote_only  runs_ablation/qwen2.5_7b_abl_quote_only.jsonl
for p in direct evidence; do cond $CF qwen2.5:7b $p runs_repeat/rep2/e1cf/qwen2.5_7b_$p.jsonl; done   # already complete: no-op
for p in direct evidence; do cond $CF qwen2.5:7b $p runs_repeat/rep3/e1cf/qwen2.5_7b_$p.jsonl; done
# ---- Llama 3.1 (E1-CF repetitions only) ----
for r in 2 3; do for p in direct evidence; do cond $CF llama3.1:8b $p runs_repeat/rep$r/e1cf/llama3.1_8b_$p.jsonl; done; done
# ---- Gemma 2 ----
for r in 2 3; do for p in direct evidence; do cond $CF gemma2:9b $p runs_repeat/rep$r/e1cf/gemma2_9b_$p.jsonl; done; done
cond $MAIN gemma2:9b abl_quote_first runs_ablation/gemma2_9b_abl_quote_first.jsonl
cond $MAIN gemma2:9b abl_quote_only  runs_ablation/gemma2_9b_abl_quote_only.jsonl
log "QUEUE DONE"
