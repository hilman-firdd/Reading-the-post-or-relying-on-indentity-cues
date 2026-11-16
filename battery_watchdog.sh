#!/bin/bash
# battery_watchdog.sh — stop the LLM queue cleanly when the laptop runs on battery at <= LIMIT % (default 9).
# run_queue.sh only checks the battery BEFORE each condition; this checks every 20 s, so a long condition cannot run the
# battery flat. Results are written per item, so stopping loses at most the items in flight; resume by running
# ./run_queue.sh again once the charger is connected.
#   nohup ./battery_watchdog.sh > logs/battery_watchdog.log 2>&1 &
LIMIT=${LIMIT:-9}
echo "[$(date '+%F %T')] watchdog on, limit ${LIMIT}%"
while pgrep -f "run_queue.sh" >/dev/null; do
  line=$(pmset -g batt 2>/dev/null | grep -i InternalBattery)
  pct=$(echo "$line" | grep -o '[0-9]*%' | head -1 | tr -d '%')
  if echo "$line" | grep -q discharging && [ -n "$pct" ] && [ "$pct" -le "$LIMIT" ]; then
    echo "[$(date '+%F %T')] battery ${pct}% on battery power -> stopping the queue"
    pkill -f "caffeinate -is ./run_queue.sh"; pkill -f "run_queue.sh"; sleep 2; pkill -f "run_llm.py run"
    echo "[$(date '+%F %T')] stopped. Plug in the charger and run ./run_queue.sh again (resumes)."; exit 0
  fi
  sleep 20
done
echo "[$(date '+%F %T')] queue no longer running; watchdog exits"
