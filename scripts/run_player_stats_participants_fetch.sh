#!/usr/bin/env bash
set -u

cd "$(dirname "$0")/.."
mkdir -p logs

LOG="logs/player_stats_participants_fetch.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RETRY_SLEEP_SECONDS="${RETRY_SLEEP_SECONDS:-120}"

exec >> "$LOG" 2>&1

while true; do
  printf '\n[%s] starting participant PlayerStats fetch\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  "$PYTHON_BIN" scripts/fetch_source.py --player-stats-participants
  status=$?
  printf '[%s] fetch exited with status %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$status"

  if [ -f player_stats_participants.json ]; then
    printf '[%s] final player_stats_participants.json exists; stopping restart loop\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    break
  fi

  printf '[%s] sleeping %s seconds before resume\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RETRY_SLEEP_SECONDS"
  sleep "$RETRY_SLEEP_SECONDS"
done
