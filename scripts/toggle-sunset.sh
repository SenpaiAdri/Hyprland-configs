#!/usr/bin/env bash
# Toggle hyprsunset 4000K <-> 6500K (off)
set -euo pipefail
STATE_FILE="$HOME/.cache/hyprsunset-state"

if ! command -v hyprsunset >/dev/null 2>&1; then
  notify-send "hyprsunset" "Not installed (pacman -S hyprsunset)" 2>/dev/null || echo "hyprsunset not installed"
  exit 0
fi

# ensure daemon
pgrep -x hyprsunset >/dev/null 2>&1 || hyprsunset --temperature 6500 >/dev/null 2>&1 &

current=$(cat "$STATE_FILE" 2>/dev/null || echo "off")

if [[ "$current" == "warm" ]]; then
  hyprsunset --temperature 6500 2>/dev/null || pkill hyprsunset 2>/dev/null || true
  # restart cold
  hyprsunset --temperature 6500 >/dev/null 2>&1 &
  echo "off" > "$STATE_FILE"
  notify-send "Night light" "Off (6500K)" 2>/dev/null || true
else
  pkill hyprsunset 2>/dev/null || true
  sleep 0.2
  hyprsunset --temperature 4000 >/dev/null 2>&1 &
  echo "warm" > "$STATE_FILE"
  notify-send "Night light" "Warm (4000K)" 2>/dev/null || true
fi
