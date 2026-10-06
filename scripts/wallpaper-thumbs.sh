#!/usr/bin/env bash
# Wallpaper thumbnails + picker listing (single python pass — fast no-op when fresh).
# Thumbs are plain 480px-wide RGB files in ~/.cache, regenerated only when the
# source is newer, or the thumb is missing/small/not plain RGB.
# Prints: "CUR:<current>" followed by "<full>|<thumb>" lines, sorted.
exec python3 - <<'EOF'
import os
from PIL import Image

wall_dirs = [
    os.path.expanduser("~/Pictures/wallpapers"),
    os.path.expanduser("~/Pictures/Wallpapers"),
]
# dedupe (same dir different case on case-insensitive fs, or symlink)
seen_dirs = set()
wall_dirs = [d for d in wall_dirs if not (d in seen_dirs or seen_dirs.add(d))]
thumb_dir = os.path.expanduser("~/.cache/wallpaper-thumbs")
os.makedirs(thumb_dir, exist_ok=True)

TW = 480


def thumb_ok(thumb, full):
    try:
        im = Image.open(thumb)
        return (im.size[0] >= TW and im.mode == "RGB"
                and os.path.getmtime(full) <= os.path.getmtime(thumb))
    except OSError:
        return False


try:
    with open(os.path.expanduser("~/.cache/current_wallpaper")) as f:
        cur = f.read().strip()
except OSError:
    cur = ""
print(f"CUR:{cur}")

exts = {".jpg", ".jpeg", ".png", ".webp"}
# collect from both dirs (lowercase legacy + capital), dedupe by real path, sorted by name
entries = {}  # realpath -> (name, full)
for wall_dir in wall_dirs:
    try:
        names = sorted(os.listdir(wall_dir))
    except OSError:
        continue
    for name in names:
        full = os.path.join(wall_dir, name)
        if not os.path.isfile(full) or os.path.splitext(name)[1].lower() not in exts:
            continue
        try:
            key = os.path.realpath(full)
        except OSError:
            continue
        # keep first; if basename collision across dirs, keep both by keying on realpath
        entries.setdefault(key, (name, full))

used_thumbs = set()
for name, full in sorted(entries.values(), key=lambda t: t[0].lower()):
    stem = os.path.splitext(name)[0]
    thumb = os.path.join(thumb_dir, stem + ".png")
    # disambiguate same basename coming from both dirs (e.g. mountain_art.jpg x2)
    n = 2
    while thumb in used_thumbs:
        thumb = os.path.join(thumb_dir, f"{stem}_{n}.png")
        n += 1
    used_thumbs.add(thumb)
    if not thumb_ok(thumb, full):
        try:
            im = Image.open(full).convert("RGB")
            w, h = im.size
            im.resize((TW, max(1, round(h * TW / w))),
                      Image.Resampling.LANCZOS).save(thumb, "PNG")
        except OSError:
            pass
    print(f"{full}|{thumb if os.path.isfile(thumb) else full}")
EOF
