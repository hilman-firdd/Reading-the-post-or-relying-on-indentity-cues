#!/bin/bash
# run_common.sh — shared checks for run_repeats.sh, run_ablation.sh and run_extra_models.sh (sourced, not run).
# Written for bash 3.2 (the bash that ships with macOS) and newer.

P=${PYTHON:-$HOME/.venvs/modkit/bin/python}
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }
set -f   # no filename globbing when lists such as "qwen2.5:7b gemma2:9b" are split into words
check_python() {
  [ -x "$P" ] || die "Python not found at $P (set PYTHON=/path/to/python)"
}

check_ollama() {
  curl -sf http://localhost:11434/api/version >/dev/null || die "Ollama is not running (start: OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024 OLLAMA_KEEP_ALIVE=30m ollama serve)"
  [ "$OLLAMA_NUM_PARALLEL" = "6" ] && [ "$OLLAMA_CONTEXT_LENGTH" = "1024" ] || \
    echo "WARNING: run 'export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024' in this shell too, so the manifest records the setting"
}

check_models() {  # every model must be pulled
  local m
  for m in "$@"; do
    ollama show "$m" >/dev/null 2>&1 || die "model '$m' is not pulled: ollama pull $m"
  done
}

check_prompts() {  # every prompt must be known to run_llm.py
  local p
  for p in "$@"; do
    case "$p" in direct|evidence|abl_quote_first|abl_quote_only) ;; *) die "unknown prompt '$p'";; esac
  done
}

# run_one ITEMS MODEL PROMPT OUT [extra args]  — resumable; failed calls of an earlier attempt are asked again
run_one() {
  local items=$1 m=$2 p=$3 out=$4; shift 4
  log "$m $p -> $out"
  "$P" run_llm.py run --items "$items" --model "$m" --prompt "$p" --workers 6 --max-tokens 256 \
       --log-errors --retry-errors "$@" --out "$out"
}
