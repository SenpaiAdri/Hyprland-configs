#!/usr/bin/env bash
# Dynamic wallpaper + matugen theming — cozy minimal dark
# Usage: wallpaper.sh <path> | wallpaper.sh --random | wallpaper.sh --init
set -euo pipefail

WALL_DIR="$HOME/Pictures/wallpapers"
FALLBACK="$HOME/.config/hypr/mountain_art.jpg"
CACHE_CURRENT="$HOME/.cache/current_wallpaper"

get_random_wall() {
  local walls=()
  while IFS= read -r -d '' f; do walls+=("$f"); done < <(find "$WALL_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) -print0 2>/dev/null)
  if [[ ${#walls[@]} -eq 0 ]]; then
    echo "$FALLBACK"
    return
  fi
  printf '%s\n' "${walls[RANDOM % ${#walls[@]}]}"
}

WALL="${1:-}"

if [[ "$WALL" == "--random" ]]; then
  WALL="$(get_random_wall)"
elif [[ "$WALL" == "--init" ]]; then
  if [[ -f "$CACHE_CURRENT" ]]; then
    WALL="$(cat "$CACHE_CURRENT")"
    [[ -f "$WALL" ]] || WALL="$(get_random_wall)"
  else
    WALL="$(get_random_wall)"
  fi
elif [[ -z "$WALL" ]]; then
  # no arg -> pick random
  WALL="$(get_random_wall)"
fi

if [[ ! -f "$WALL" ]]; then
  echo "Wallpaper not found: $WALL" >&2
  WALL="$FALLBACK"
fi

mkdir -p "$(dirname "$CACHE_CURRENT")"
echo "$WALL" > "$CACHE_CURRENT"
# also store for hyprlock fallback
mkdir -p "$HOME/.cache"
cp -f "$WALL" "$HOME/.cache/wallpaper_current.jpg" 2>/dev/null || true

# 1) Set wallpaper — prefer awww, fallback to hyprpaper / swaybg
set_wallpaper() {
  local img="$1"
  if command -v awww >/dev/null 2>&1; then
    # ensure daemon
    pgrep -x awww-daemon >/dev/null 2>&1 || awww-daemon >/dev/null 2>&1 &
    sleep 0.3
    awww img "$img" --transition-type wipe --transition-duration 0.8 --transition-fps 60 2>/dev/null || \
    awww img "$img" --transition-type fade --transition-duration 0.8 2>/dev/null || \
    awww img "$img" 2>/dev/null || true
    # also set for each output explicitly
    for mon in eDP-1 HDMI-A-1; do
      awww img "$img" -o "$mon" --transition-type wipe --transition-duration 0.8 2>/dev/null || true
    done
    return 0
  fi
  if command -v swww >/dev/null 2>&1; then
    pgrep -x swww-daemon >/dev/null 2>&1 || swww-daemon >/dev/null 2>&1 &
    sleep 0.3
    swww img "$img" --transition-type wipe --transition-duration 0.8 --transition-fps 60 2>/dev/null || swww img "$img" 2>/dev/null || true
    return 0
  fi
  if command -v hyprpaper >/dev/null 2>&1; then
    # hyprpaper via hyprctl
    hyprctl hyprpaper preload "$img" 2>/dev/null || true
    hyprctl hyprpaper wallpaper "eDP-1,$img" 2>/dev/null || true
    hyprctl hyprpaper wallpaper "HDMI-A-1,$img" 2>/dev/null || true
    hyprctl hyprpaper wallpaper ",$img" 2>/dev/null || true
    hyprctl hyprpaper unload unused 2>/dev/null || true
    # also update hyprpaper.conf for persistence
    cat > "$HOME/.config/hypr/hyprpaper.conf" <<EOF
preload = $img
wallpaper {
    monitor = eDP-1
    path = $img
    fit_mode = cover
}
wallpaper {
    monitor = HDMI-A-1
    path = $img
    fit_mode = cover
}
wallpaper {
    monitor =
    path = $img
    fit_mode = cover
}
EOF
    return 0
  fi
  echo "No wallpaper daemon found (awww/swww/hyprpaper)" >&2
  return 1
}

set_wallpaper "$WALL"

# 2) Generate colors via matugen (tonalSpot dark 0.15)
if command -v matugen >/dev/null 2>&1; then
  matugen image "$WALL" --mode dark --type scheme-tonal-spot --contrast 0.15 2>/dev/null || \
  matugen image "$WALL" 2>/dev/null || true
fi

# 3) Reload consumers
pkill -SIGUSR2 waybar 2>/dev/null || (killall -SIGUSR2 waybar 2>/dev/null || true)
# swaync reload
swaync-client --reload-css 2>/dev/null || swaync-client -rs 2>/dev/null || true
# kitty reload (if kitty is running, it will auto-reload on SIGUSR1 or config change)
pkill -SIGUSR1 kitty 2>/dev/null || true
# hyprland reload to pick new colors.conf
hyprctl reload 2>/dev/null || true

if command -v notify-send >/dev/null 2>&1; then
  notify-send -i preferences-desktop-wallpaper "Wallpaper" "$(basename "$WALL")" 2>/dev/null || true
fi

echo "Wallpaper set: $WALL"
