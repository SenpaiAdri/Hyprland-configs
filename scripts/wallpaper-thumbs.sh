#!/usr/bin/env bash
# Wallpaper thumbnails + picker listing (single python pass — fast no-op when fresh).
# Thumbs are plain 480px-wide RGB files in ~/.cache, regenerated only when the
# source is newer, or the thumb is missing/small/not plain RGB.
# Prints: "CUR:<current>" followed by "<full>|<thumb>" lines, sorted.
exec python3 - <<'EOF'
import os
from PIL import Image

wall_dir = os.path.expanduser("~/Pictures/wallpapers")
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
try:
    names = sorted(os.listdir(wall_dir))
except OSError:
    names = []

for name in names:
    full = os.path.join(wall_dir, name)
    if not os.path.isfile(full) or os.path.splitext(name)[1].lower() not in exts:
        continue
    thumb = os.path.join(thumb_dir, os.path.splitext(name)[0] + ".png")
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
