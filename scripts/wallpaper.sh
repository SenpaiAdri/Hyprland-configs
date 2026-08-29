#!/usr/bin/env bash
# Dynamic wallpaper + matugen theming — hyprpaper (0.8.4) primary, awww/swww fallback
# Usage: wallpaper.sh <path> | wallpaper.sh --random | wallpaper.sh --init
set -euo pipefail

WALL_DIR="$HOME/Pictures/wallpapers"
CACHE_CURRENT="$HOME/.cache/current_wallpaper"

get_random_wall() {
  local walls=()
  while IFS= read -r -d '' f; do walls+=("$f"); done < <(find "$WALL_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) -print0 2>/dev/null)
  if [[ ${#walls[@]} -eq 0 ]]; then
    echo "No wallpapers in $WALL_DIR" >&2
    exit 1
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
  WALL="$(get_random_wall)"
fi

if [[ ! -f "$WALL" ]]; then
  echo "Wallpaper not found: $WALL" >&2
  exit 1
fi

mkdir -p "$(dirname "$CACHE_CURRENT")"
echo "$WALL" > "$CACHE_CURRENT"
mkdir -p "$HOME/.cache"
cp -f "$WALL" "$HOME/.cache/wallpaper_current.jpg" 2>/dev/null || true

set_wallpaper() {
  local img="$1"
  # 1) try awww (if installed) — keep for users who have it
  if command -v awww >/dev/null 2>&1; then
    pgrep -x awww-daemon >/dev/null 2>&1 || awww-daemon >/dev/null 2>&1 &
    sleep 0.2
    awww img "$img" --transition-type wipe --transition-duration 0.8 --transition-fps 60 2>/dev/null || \
    awww img "$img" 2>/dev/null || true
    for mon in eDP-1 HDMI-A-1; do
      awww img "$img" -o "$mon" --transition-type wipe --transition-duration 0.8 2>/dev/null || true
    done
    return 0
  fi
  # 2) swww fallback
  if command -v swww >/dev/null 2>&1; then
    pgrep -x swww-daemon >/dev/null 2>&1 || swww-daemon >/dev/null 2>&1 &
    sleep 0.2
    swww img "$img" --transition-type wipe --transition-duration 0.8 --transition-fps 60 2>/dev/null || swww img "$img" 2>/dev/null || true
    return 0
  fi
  # 3) hyprpaper 0.8.4 — Hyprland 0.56: only 'wallpaper' IPC (preload/unload removed)
  if command -v hyprpaper >/dev/null 2>&1; then
    # ensure daemon is running (hyprland exec-once starts it, but double-check)
    pgrep -x hyprpaper >/dev/null 2>&1 || hyprpaper >/dev/null 2>&1 &
    sleep 0.2
    # new IPC: hyprctl hyprpaper wallpaper "mon,path" — no preload needed
    hyprctl hyprpaper wallpaper "eDP-1,$img" 2>/dev/null || true
    hyprctl hyprpaper wallpaper "HDMI-A-1,$img" 2>/dev/null || true
    hyprctl hyprpaper wallpaper ",$img" 2>/dev/null || true
    # persist for next boot
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

# --- Dynamic theming (theme-generator + matugen compat) ---
# Ensure local bin in PATH for our matugen wrapper
export PATH="$HOME/.local/bin:$PATH"
THEME_GEN="$HOME/.config/hypr/scripts/theme-generator.py"

# Prefer our theme-generator directly (fast, no matugen needed)
if [[ -x "$THEME_GEN" ]]; then
  python3 "$THEME_GEN" "$WALL" 2>/dev/null || true
elif command -v matugen >/dev/null 2>&1; then
  matugen image "$WALL" --mode dark --type scheme-tonal-spot --contrast 0.15 2>/dev/null || true
fi

# Reload dynamic targets
pkill -SIGUSR2 waybar 2>/dev/null || (killall -SIGUSR2 waybar 2>/dev/null || true)
# waybar may need restart if SIGUSR2 not enough (CSS reload)
# (keep SIGUSR2 first for smooth, fallback to restart after hyprctl reload)
swaync-client --reload-css 2>/dev/null || swaync-client -rs 2>/dev/null || true
# kitty live reload (SIGUSR1 reloads colors.conf if `include` is used)
pkill -SIGUSR1 kitty 2>/dev/null || true
# hyprland/hyprlock will pick new colors via `source` on reload
hyprctl reload 2>/dev/null || true
# force swaync style reload via css timestamp touch
touch "$HOME/.config/swaync/style.css" 2>/dev/null || true
touch "$HOME/.config/waybar/style.css" 2>/dev/null || true

if command -v notify-send >/dev/null 2>&1; then
  notify-send -i preferences-desktop-wallpaper "Wallpaper" "$(basename "$WALL")" 2>/dev/null || true
fi

echo "Wallpaper set: $WALL"
