#!/usr/bin/env bash
# Run paper cycles one at a time and send a Telegram status after each.
# Usage: ./run-with-telegram.sh [cycles] [sleep_minutes]
# Paper only: --real is refused here. Needs TELEGRAM_BOT_TOKEN and
# TELEGRAM_CHAT_ID in the environment (see notify_telegram.py).
set -uo pipefail
cd "$(dirname "$0")"

for a in "$@"; do
  if [ "$a" = "--real" ]; then
    echo "ERROR: run-with-telegram.sh is paper-only; --real is not supported" >&2
    exit 1
  fi
done

# Korean Windows defaults Python to cp949, which breaks core/ reading UTF-8 JSON.
export PYTHONUTF8=1

CYCLES="${1:-1}"
SLEEP_MIN="${2:-45}"

for i in $(seq 1 "$CYCLES"); do
  before=$(grep -c . journal/cycles.log 2>/dev/null); before=${before:-0}
  # loop.sh exits 1 even after a good single cycle (its final sleep test),
  # so success is judged by a new journal/cycles.log line, not the exit code.
  ./loop.sh 1
  after=$(grep -c . journal/cycles.log 2>/dev/null); after=${after:-0}
  if [ "$after" -gt "$before" ]; then
    python3 notify_telegram.py done "$i" "$CYCLES"
  else
    python3 notify_telegram.py failed "$i" "$CYCLES"
  fi
  [ "$i" -lt "$CYCLES" ] && sleep $((SLEEP_MIN * 60))
done
exit 0
