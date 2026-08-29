#!/usr/bin/env bash
# Rofi picker for wallpapers — cozy minimal dark
set -euo pipefail

WALL_DIR="$HOME/Pictures/wallpapers"
SCRIPT="$HOME/.config/hypr/scripts/wallpaper.sh"

walls=$(find "$WALL_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) 2>/dev/null | sort)
if [[ -z "$walls" ]]; then
  notify-send "Wallpaper picker" "No images in $WALL_DIR" 2>/dev/null || true
  exit 1
fi

# Build display names (basename)
display=$(printf '%s\n' $walls | while read -r f; do basename "$f"; done)

# Use rofi
if command -v rofi >/dev/null 2>&1; then
  choice=$(printf '%s\n' $walls | while read -r f; do echo "$(basename "$f")"; done | rofi -dmenu -theme ~/.config/rofi/config.rasi -p "Wallpaper" -show-icons false)
else
  choice=$(printf '%s\n' $display | wofi --dmenu --prompt "Wallpaper" 2>/dev/null || bemenu -p "Wallpaper" 2>/dev/null)
fi

if [[ -z "${choice:-}" ]]; then exit 0; fi

# Resolve back to full path (first match by basename)
selected=$(printf '%s\n' $walls | grep -F "/$choice" | head -n1)
if [[ -z "$selected" ]]; then
  # fallback: try exact
  selected=$(printf '%s\n' $walls | grep -F "$choice" | head -n1)
fi

if [[ -n "$selected" && -f "$selected" ]]; then
  exec "$SCRIPT" "$selected"
else
  notify-send "Wallpaper" "Not found: $choice" 2>/dev/null || true
fi
