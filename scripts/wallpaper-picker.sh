#!/usr/bin/env bash
# Wallpaper picker — strict kitty+fzf only
# GTK picker is primary: wallpaper-gtk-picker.py
# This script only provides kitty+fzf 2-column preview.
set -euo pipefail

WALL_DIR="$HOME/Pictures/wallpapers"
SCRIPT="$HOME/.config/hypr/scripts/wallpaper.sh"
CACHE_CURRENT="$HOME/.cache/current_wallpaper"

get_walls() {
  find "$WALL_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) 2>/dev/null | sort
}

notify() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Wallpaper" "$1" 2>/dev/null || true
  else
    echo "$1" >&2
  fi
}

fzf_colors() {
  echo "bg:#1e1e2e,bg+:#313244,fg:#cdd6f4,fg+:#cdd6f4,hl:#89b4fa,hl+:#89b4fa,info:#6c7086,prompt:#89b4fa,pointer:#f38ba8,marker:#a6e3a1,spinner:#f9e2af,header:#6c7086,border:#585b70,label:#cdd6f4"
}

current_wallpaper() {
  [[ -f "$CACHE_CURRENT" ]] && cat "$CACHE_CURRENT" 2>/dev/null || echo ""
}

run_fzf_inner() {
  local walls
  walls=$(get_walls)
  if [[ -z "$walls" ]]; then
    notify "No images in $WALL_DIR"
    exit 1
  fi

  local wall_count
  wall_count=$(printf '%s\n' "$walls" | wc -l)
  local cur
  cur=$(current_wallpaper)

  local preview_sh
  preview_sh=$(mktemp /tmp/wallpaper-fzf-preview-XXXXXX.sh)
  trap 'rm -f "$preview_sh"' EXIT

  cat > "$preview_sh" <<'PREVIEW_EOF'
#!/usr/bin/env bash
file="$1"
cols="${FZF_PREVIEW_COLUMNS:-60}"
lines="${FZF_PREVIEW_LINES:-22}"
kitty +kitten icat --clear 2>/dev/null || true
if [[ -f "$file" ]]; then
  if kitty +kitten icat --transfer-mode=stream --place "${cols}x${lines}@0x0" --scale-up --align center "$file" 2>/dev/null; then
    exit 0
  fi
  if kitty +kitten icat --transfer-mode=memory --place "${cols}x${lines}@0x0" --scale-up --align center "$file" 2>/dev/null; then
    exit 0
  fi
  if kitty +kitten icat --transfer-mode=file --place "${cols}x${lines}@0x0" --scale-up --align center "$file" 2>/dev/null; then
    exit 0
  fi
  if kitty +kitten icat --transfer-mode=stream "$file" 2>/dev/null; then
    exit 0
  fi
fi
echo "Preview unavailable: $file"
[[ -f "$file" ]] && ls -lh "$file" 2>/dev/null | awk '{print $9, "(" $5 ")"}' || true
PREVIEW_EOF
  chmod +x "$preview_sh"

  local header="󰸉  $wall_count wallpapers  •  Enter: apply  •  Esc: cancel  •  Type to filter"
  if [[ -n "$cur" && -f "$cur" ]]; then
    header="$header  •  current: $(basename "$cur")"
  fi

  local label=" 󰸉 Wallpaper Picker — ${wall_count} images — left: preview  |  right: choices "

  local selected
  selected=$(printf '%s\n' $walls | \
    fzf \
      --prompt="   " \
      --pointer="▶" \
      --marker="✓" \
      --header="$header" \
      --header-first \
      --border=rounded \
      --border-label="$label" \
      --border-label-pos=3 \
      --preview="$preview_sh {}" \
      --preview-window="left,60%,border-right,wrap" \
      --height=100% \
      --layout=reverse \
      --info=inline-right \
      --ansi \
      --delimiter='/' \
      --with-nth=-1 \
      --nth=-1 \
      --color="$(fzf_colors)" \
      --no-multi \
      --cycle
  ) || true

  rm -f "$preview_sh"
  trap - EXIT

  if [[ -z "${selected:-}" ]]; then
    exit 0
  fi

  local target="$selected"
  if [[ ! -f "$target" ]]; then
    target=$(printf '%s\n' $walls | grep -F "/$selected" | head -n1 || true)
    [[ -z "$target" ]] && target=$(printf '%s\n' $walls | grep -F "$selected" | head -n1 || true)
  fi

  if [[ -n "$target" && -f "$target" ]]; then
    kitty +kitten icat --clear 2>/dev/null || true
    exec "$SCRIPT" "$target"
  else
    notify "Not found: $selected"
    exit 1
  fi
}

spawn_kitty_picker() {
  local self="$HOME/.config/hypr/scripts/wallpaper-picker.sh"
  if ! command -v kitty >/dev/null 2>&1; then
    echo "kitty not found — cannot show fzf picker" >&2
    exit 1
  fi
  if ! command -v fzf >/dev/null 2>&1; then
    echo "fzf not found — cannot show picker" >&2
    exit 1
  fi
  if command -v hyprctl >/dev/null 2>&1 && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    hyprctl dispatch exec "[float; size 1180 680; center] kitty --class wallpaper-picker --title 'Wallpaper Picker' -o background_opacity=0.96 -o window_padding_width=0 -o confirm_os_window_close=0 -e bash -c '$self --inner-fzf'" >/dev/null 2>&1 || \
    kitty --class wallpaper-picker --title 'Wallpaper Picker' -o background_opacity=0.96 -o window_padding_width=0 -o confirm_os_window_close=0 -e bash -c "$self --inner-fzf" >/dev/null 2>&1 &
    exit 0
  fi
  kitty --class wallpaper-picker --title 'Wallpaper Picker' -o background_opacity=0.96 -o window_padding_width=0 -o confirm_os_window_close=0 -e bash -c "$self --inner-fzf" >/dev/null 2>&1 &
  exit 0
}

case "${1:-}" in
  --inner-fzf|--fzf-inner)
    if ! command -v fzf >/dev/null 2>&1; then
      echo "fzf not found" >&2; exit 1
    fi
    if ! command -v kitty >/dev/null 2>&1; then
      echo "kitty not found" >&2; exit 1
    fi
    run_fzf_inner
    ;;
  --fzf|--kitty|--inner)
    if [[ -t 0 && -t 1 ]]; then
      run_fzf_inner
    else
      spawn_kitty_picker
    fi
    ;;
  --help|-h)
    echo "Usage: wallpaper-picker.sh [--inner-fzf|--fzf|--help]"
    echo "  GTK picker is primary: python3 ~/.config/hypr/scripts/wallpaper-gtk-picker.py"
    echo "  This script is strict kitty+fzf only"
    exit 0
    ;;
  "")
    if command -v fzf >/dev/null 2>&1 && command -v kitty >/dev/null 2>&1; then
      if [[ -t 0 && -t 1 ]]; then
        run_fzf_inner
      else
        spawn_kitty_picker
      fi
    else
      echo "fzf and kitty required" >&2
      exit 1
    fi
    ;;
  *)
    if [[ -f "${1:-}" ]]; then
      exec "$SCRIPT" "$1"
    else
      echo "Unknown arg: $1" >&2
      exit 1
    fi
    ;;
esac
