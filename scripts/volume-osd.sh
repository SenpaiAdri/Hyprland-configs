#!/bin/bash
# Volume / brightness keys with quickshell OSD feedback.
# Usage: volume-osd.sh up|down|mute|micmute|bright-up|bright-down
set -u

SINK="@DEFAULT_AUDIO_SINK@"
SOURCE="@DEFAULT_AUDIO_SOURCE@"

osd() {
    # osd <kind> <level> <muted true|false> — never break the keybind if OSD is down
    quickshell ipc call osd popup "$1" "$2" "$3" >/dev/null 2>&1 || true
}

sink_level() {
    local out vol
    out=$(wpctl get-volume "$SINK")
    vol=$(echo "$out" | awk '{print int($2 * 100)}')
    echo "$vol"
}

sink_muted() {
    wpctl get-volume "$SINK" | grep -q "MUTED" && echo true || echo false
}

case "${1:-}" in
    up)
        wpctl set-volume -l 1 "$SINK" 5%+
        osd volume "$(sink_level)" "$(sink_muted)"
        ;;
    down)
        wpctl set-volume "$SINK" 5%-
        osd volume "$(sink_level)" "$(sink_muted)"
        ;;
    mute)
        wpctl set-mute "$SINK" toggle
        osd volume "$(sink_level)" "$(sink_muted)"
        ;;
    micmute)
        wpctl set-mute "$SOURCE" toggle
        if wpctl get-volume "$SOURCE" | grep -q "MUTED"; then
            osd mic 0 true
        else
            osd mic 100 false
        fi
        ;;
    bright-up)
        brightnessctl set 5%+ >/dev/null
        osd brightness "$(brightnessctl -m | cut -d, -f4 | tr -d %)" false
        ;;
    bright-down)
        brightnessctl set 5%- >/dev/null
        osd brightness "$(brightnessctl -m | cut -d, -f4 | tr -d %)" false
        ;;
    *)
        echo "usage: $0 up|down|mute|micmute|bright-up|bright-down" >&2
        exit 1
        ;;
esac
