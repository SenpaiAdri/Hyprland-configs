#!/usr/bin/env python3
"""
Dynamic theme generator — matugen replacement
Generates Material tonal-spot dark palette from wallpaper dominant color
Outputs: hyprland, waybar, kitty, rofi, swaync, hyprlock

Usage: theme-generator.py /path/to/wallpaper.jpg
       theme-generator.py --matugen-compat image /path  (wrapper for wallpaper.sh)
"""
import sys
import os
import pathlib
import colorsys
from PIL import Image

# --------------------------- color utils ---------------------------
def hex_to_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

def hls_to_hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(int(round(r*255)), int(round(g*255)), int(round(b*255)))

def hex_to_hls(h):
    r, g, b = hex_to_rgb(h)
    return colorsys.rgb_to_hls(r/255, g/255, b/255)

def rgba_str_from_hex(hexc, alpha=1.0):
    r, g, b = hex_to_rgb(hexc)
    if alpha >= 1.0:
        return f"rgba({r}, {g}, {b}, 1.0)"
    return f"rgba({r}, {g}, {b}, {alpha})"

def hex_stripped(h):
    return h.lstrip('#')

# --------------------------- palette generation ---------------------------
PRETUNED = {
    # Hand-tuned overrides for known wallpapers (basename -> partial palette)
    # If not listed, algorithmic generation is used.
    # These ensure each wallpaper has a distinctive, well-balanced theme.
    # mountain_art.jpg — deep violet dusk (purple/mauve)
    "mountain_art.jpg": {
        "primary": "#b9a0ff",
        "primary_container": "#3d3168",
        "secondary": "#c8b0e8",
        "tertiary": "#e8a0c8",
        "surface": "#1b1926",
        "surface_container": "#252336",
        "background": "#13111c",
        "on_surface": "#e6e0f7",
        "surface_variant": "#2e2a3d",
        "outline": "#938caa",
        "error": "#ffb4ab",
    },
    "dark-minimalist.jpg": {
        # True grayscale — monochrome charcoal (blue accent removed per request)
        "primary": "#d0d0d0",
        "primary_container": "#3a3a3a",
        "secondary": "#b8b8b8",
        "tertiary": "#a8a8a8",
        "surface": "#161616",
        "surface_container": "#1e1e1e",
        "background": "#0f0f0f",
        "on_surface": "#ececec",
        "surface_variant": "#2c2c2c",
        "outline": "#6e6e6e",
        "error": "#9e9e9e",
        "on_primary": "#0f0f0f",
    },
    "dark_minimalist.jpg": {
        # True grayscale — monochrome charcoal (blue accent removed per request)
        "primary": "#d0d0d0",
        "primary_container": "#3a3a3a",
        "secondary": "#b8b8b8",
        "tertiary": "#a8a8a8",
        "surface": "#161616",
        "surface_container": "#1e1e1e",
        "background": "#0f0f0f",
        "on_surface": "#ececec",
        "surface_variant": "#2c2c2c",
        "outline": "#6e6e6e",
        "error": "#9e9e9e",
        "on_primary": "#0f0f0f",
    },
}

def extract_dominant(image_path, num_colors=6):
    """Return dominant hex and sorted palette list [(count, hex), ...]"""
    try:
        im = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Invalid image {image_path}: {e}", file=sys.stderr)
        return "#7b68ee", []
    # quantize to get dominant
    small = im.resize((200, 200), Image.Resampling.LANCZOS)
    q = small.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    qrgb = q.convert("RGB")
    colors = qrgb.getcolors(200*200)
    if not colors:
        # fallback average
        avg = im.resize((1, 1)).getpixel((0, 0))
        avg_hex = rgb_to_hex(*avg[:3])
        return avg_hex, []
    # sort by count descending
    colors_sorted = sorted(colors, reverse=True)
    palette = []
    for cnt, col in colors_sorted:
        if isinstance(col, int):
            # palette mode returns int? convert
            r, g, b = q.getpalette()[col*3:col*3+3]
            hexc = rgb_to_hex(r, g, b)
        else:
            hexc = rgb_to_hex(*col)
        palette.append((cnt, hexc))
    dominant = palette[0][1]
    return dominant, palette

def is_grayscale(hexc, thresh=0.12):
    r, g, b = hex_to_rgb(hexc)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    return s < thresh

def generate_palette(dominant_hex, palette_list=None):
    """Generate full dark tonal-spot palette from dominant hex."""
    basename = ""
    # check pretuned first via caller? handled outside
    r, g, b = hex_to_rgb(dominant_hex)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    # detect grayscale / low chroma
    gray = is_grayscale(dominant_hex)
    if gray:
        # True grayscale — no blue tint, pure neutral greys
        # primary light grey, surface charcoal
        primary = "#d0d0d0"
        primary_container = "#3a3a3a"
        secondary = "#b8b8b8"
        tertiary = "#a8a8a8"
        surface = "#161616"
        surface_container = "#1e1e1e"
        background = "#0f0f0f"
        on_surface = "#ececec"
        surface_variant = "#2c2c2c"
        outline = "#6e6e6e"
        error = "#9e9e9e"
        # derive outline_variant etc if needed
        return {
            "primary": primary,
            "primary_container": primary_container,
            "on_primary": "#0f0f0f",
            "secondary": secondary,
            "tertiary": tertiary,
            "surface": surface,
            "surface_container": surface_container,
            "background": background,
            "on_surface": on_surface,
            "surface_variant": surface_variant,
            "outline": outline,
            "error": error,
            "dominant": dominant_hex,
        }
    # chromatic case: boost saturation for primary, lighten
    # primary: light pastel (~0.75 lumi)
    s_primary = min(max(s * 1.15, 0.65), 0.85)
    # if original s is high, keep high; if moderate, bump
    l_primary = 0.75
    # special handling for very dark dominant (low l) → still light primary
    # special handling for yellow/green hue: reduce lightness slightly to avoid neon
    # hue green ~120 deg, yellow ~60. Keep l 0.72 for those
    hue_deg = h * 360
    if 50 < hue_deg < 150:
        l_primary = 0.72
        s_primary = min(s_primary, 0.70)
    primary = hls_to_hex(h, l_primary, s_primary)

    # primary_container: dark desaturated
    primary_container = hls_to_hex(h, 0.30, s_primary * 0.52)
    # on_primary: dark for text on primary (approx 15% lightness)
    on_primary = hls_to_hex(h, 0.15, 0.30)

    # secondary: shift hue +18 deg, slightly desaturated
    h_sec = (h + 18/360) % 1.0
    secondary = hls_to_hex(h_sec, 0.74, s_primary * 0.75)
    # tertiary: shift +50 deg
    h_ter = (h + 50/360) % 1.0
    tertiary = hls_to_hex(h_ter, 0.72, s_primary * 0.68)

    # surface family: desaturated dark, tiny hue influence
    # Use original hue but low saturation
    surf_h = h
    surface = hls_to_hex(surf_h, 0.12, 0.14)
    surface_container = hls_to_hex(surf_h, 0.15, 0.13)
    background = hls_to_hex(surf_h, 0.09, 0.13)
    on_surface = hls_to_hex(surf_h, 0.88, 0.15)
    surface_variant = hls_to_hex(surf_h, 0.20, 0.10)
    outline = hls_to_hex(surf_h, 0.45, 0.08)
    error = "#f38ba8"  # keep catppuccin error for dark consistency
    # For forest green wallpapers, tweak error to not clash? keep.

    # If palette_list provided and we have second dominant distinct hue, use it for secondary/tertiary?
    # Try to pick second color if its hue differs >30 deg from dominant
    if palette_list and len(palette_list) >= 2:
        # palette_list is [(cnt, hex), ...]
        second_hex = palette_list[1][1]
        r2, g2, b2 = hex_to_rgb(second_hex)
        h2, l2, s2 = colorsys.rgb_to_hls(r2/255, g2/255, b2/255)
        hue_diff = min(abs(h - h2), 1-abs(h-h2)) * 360
        if hue_diff > 22 and s2 > 0.25:
            # use second hue for secondary instead of shifted
            # generate secondary lighter version of second hue
            s2b = min(max(s2*1.1, 0.60), 0.82)
            secondary = hls_to_hex(h2, 0.74, s2b*0.75)
            # tertiary from third if exists
            if len(palette_list) >= 3:
                third_hex = palette_list[2][1]
                r3,g3,b3 = hex_to_rgb(third_hex)
                h3,l3,s3 = colorsys.rgb_to_hls(r3/255,g3/255,b3/255)
                if s3>0.25:
                    tertiary = hls_to_hex(h3, 0.72, min(max(s3*1.0,0.55),0.75))

    return {
        "primary": primary,
        "primary_container": primary_container,
        "on_primary": on_primary,
        "secondary": secondary,
        "tertiary": tertiary,
        "surface": surface,
        "surface_container": surface_container,
        "background": background,
        "on_surface": on_surface,
        "surface_variant": surface_variant,
        "outline": outline,
        "error": error,
        "dominant": dominant_hex,
    }

def finalize_palette(image_path):
    """Return final palette dict, using pretuned if available else algorithmic."""
    base = os.path.basename(image_path)
    # also try without path variations
    if base in PRETUNED:
        pal = PRETUNED[base].copy()
        # ensure required keys
        # fill missing derived keys
        if "on_primary" not in pal:
            pal["on_primary"] = "#1e1e2e"
        if "dominant" not in pal:
            dom,_ = extract_dominant(image_path)
            pal["dominant"] = dom
        # ensure all keys present
        for k in ["primary","primary_container","secondary","tertiary","surface","surface_container","background","on_surface","surface_variant","outline","error"]:
            if k not in pal:
                # fallback algorithmic for missing
                dom,_=extract_dominant(image_path)
                algo=generate_palette(dom)
                pal[k]=algo[k]
        return pal
    # not pretuned: algorithmic
    dom, plist = extract_dominant(image_path)
    return generate_palette(dom, plist)

# --------------------------- writers ---------------------------
def write_hyprland(pal, out_path):
    content = f"""# Generated by theme-generator — wall: {pal.get('dominant','?')} primary {pal['primary']}
general {{
    col.active_border = rgba({hex_stripped(pal['primary'])}ff) rgba({hex_stripped(pal['primary_container'])}ff) 45deg
    col.inactive_border = rgba({hex_stripped(pal['surface_variant'])}aa)
}}
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def write_waybar(pal, out_path):
    content = f"""/* Generated by theme-generator — dominant {pal.get('dominant','?')} */
@define-color primary {pal['primary']};
@define-color primary_container {pal['primary_container']};
@define-color on_primary {pal['on_primary']};
@define-color secondary {pal['secondary']};
@define-color tertiary {pal['tertiary']};
@define-color surface {pal['surface']};
@define-color surface_container {pal['surface_container']};
@define-color background {pal['background']};
@define-color on_surface {pal['on_surface']};
@define-color surface_variant {pal['surface_variant']};
@define-color outline {pal['outline']};
@define-color error {pal['error']};
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def write_kitty(pal, out_path):
    content = f"""# Generated by theme-generator — primary {pal['primary']} surface {pal['surface']}
foreground {pal['on_surface']}
background {pal['surface']}
cursor {pal['primary']}
cursor_text_color {pal['on_primary']}
selection_foreground {pal['on_primary']}
selection_background {pal['primary']}

# Normal
color0 {pal['surface']}
color1 {pal['error']}
color2 {pal['tertiary']}
color3 {pal['secondary']}
color4 {pal['primary']}
color5 {pal['primary']}
color6 {pal['secondary']}
color7 {pal['on_surface']}
# Bright
color8 {pal['outline']}
color9 {pal['error']}
color10 {pal['tertiary']}
color11 {pal['secondary']}
color12 {pal['primary']}
color13 {pal['primary_container']}
color14 {pal['secondary']}
color15 {pal['surface_variant']}

# Tabs — dynamic (overrides kitty.conf fallback)
active_tab_foreground {pal['on_primary']}
active_tab_background {pal['primary']}
inactive_tab_foreground {pal['on_surface']}
inactive_tab_background {pal['surface_variant']}
tab_bar_background {pal['surface']}
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def write_rofi(pal, out_path):
    content = f"""/* Generated by theme-generator — {pal['primary']} */
* {{
    background: {pal['surface']};
    background-alt: {pal['surface_container']};
    foreground: {pal['on_surface']};
    selected: {pal['primary']};
    active: {pal['outline']};
    urgent: {pal['error']};
}}
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def write_swaync(pal, out_path):
    content = f"""/* Generated by theme-generator — {pal['primary']} */
@define-color primary {pal['primary']};
@define-color surface {pal['surface']};
@define-color surface_variant {pal['surface_variant']};
@define-color surface_container {pal['surface_container']};
@define-color on_surface {pal['on_surface']};
@define-color outline {pal['outline']};
@define-color error {pal['error']};
@define-color secondary {pal['secondary']};
@define-color tertiary {pal['tertiary']};
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def write_hyprlock(pal, out_path):
    r, g, b = hex_to_rgb(pal['primary'])
    rs, gs, bs = hex_to_rgb(pal['surface'])
    ron, gon, bon = hex_to_rgb(pal['on_surface'])
    re, ge, be = hex_to_rgb(pal['error'])
    # tertiary for check color (success green-ish) — use tertiary if available else primary
    rt, gt, bt = hex_to_rgb(pal.get('tertiary', pal['primary']))
    # generate vars with proper alpha handling (hyprlock supports rgba(r,g,b,a))
    content = f"""# Generated by theme-generator — wall {pal.get('dominant','?')}
# Hyprlock dynamic colors — sourced by hyprlock.conf
# Primary: {pal['primary']}  Surface: {pal['surface']}  OnSurface: {pal['on_surface']}

$primary = rgba({r}, {g}, {b}, 1.0)
$primary30 = rgba({r}, {g}, {b}, 0.30)
$primary90 = rgba({r}, {g}, {b}, 0.90)
$surface = rgba({rs}, {gs}, {bs}, 1.0)
$surface55 = rgba({rs}, {gs}, {bs}, 0.55)
$surface75 = rgba({rs}, {gs}, {bs}, 0.75)
$on_surface = rgba({ron}, {gon}, {bon}, 0.95)
$on_surface70 = rgba({ron}, {gon}, {bon}, 0.70)
$on_surface85 = rgba({ron}, {gon}, {bon}, 0.85)
$error = rgba({re}, {ge}, {be}, 1.0)
$error90 = rgba({re}, {ge}, {be}, 0.90)
$tertiary90 = rgba({rt}, {gt}, {bt}, 0.90)
$outline = rgba({hex_to_rgb(pal['outline'])[0]}, {hex_to_rgb(pal['outline'])[1]}, {hex_to_rgb(pal['outline'])[2]}, 1.0)
# also hex for Hyprland rgba(hex) compat
$primary_hex = rgba({pal['primary'].lstrip('#')}ff)
$surface_hex = rgba({pal['surface'].lstrip('#')}ff)

"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(content)

def generate_all(image_path):
    pal = finalize_palette(image_path)
    home = pathlib.Path.home()
    # ensure cache for compat with wallpaper.sh
    # Write all targets
    write_hyprland(pal, str(home / ".config/hypr/colors.conf"))
    write_waybar(pal, str(home / ".config/waybar/colors.css"))
    write_kitty(pal, str(home / ".config/kitty/colors.conf"))
    write_rofi(pal, str(home / ".config/rofi/colors.rasi"))
    write_swaync(pal, str(home / ".config/swaync/colors.css"))
    write_hyprlock(pal, str(home / ".config/hypr/hyprlock-colors.conf"))
    # also write a debug palette file
    debug_path = home / ".cache" / "theme-palette.json"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(debug_path, 'w') as f:
        json.dump(pal, f, indent=2)
    # write current wallpaper cache tag
    # Also produce a summary notify string
    return pal

def main():
    args = sys.argv[1:]
    # matugen compat: matugen image <path> --mode dark ...
    # we accept: theme-generator.py [image] <path>  OR  theme-generator.py <path>
    wall = None
    if not args:
        print("Usage: theme-generator.py <wallpaper>  OR  theme-generator.py image <wallpaper>", file=sys.stderr)
        sys.exit(1)
    # if first arg is 'image', skip
    if args[0] == "image":
        args = args[1:]
    # skip flags like --mode, --type, etc and pick first non-flag existing file
    for a in args:
        if a.startswith("-"):
            continue
        # also skip values for flags? we skip next if previous was flag with value, but we just pick first file that exists
        if os.path.isfile(os.path.expanduser(a)):
            wall = os.path.expanduser(a)
            break
        # if not existing, maybe still treat as wall if ends with jpg/png
        if a.lower().endswith(('.jpg','.jpeg','.png','.webp')):
            # expand
            cand = os.path.expanduser(a)
            # if cand exists, use; else maybe wall not found yet
            wall = cand
            break
    if wall is None:
        # fallback: take last arg that looks like path
        for a in reversed(args):
            if not a.startswith("-"):
                wall = os.path.expanduser(a)
                break
    if wall is None or not os.path.isfile(wall):
        print(f"Wallpaper not found: {wall}", file=sys.stderr)
        sys.exit(1)
    pal = generate_all(wall)
    print(f"Theme generated for {os.path.basename(wall)}: primary {pal['primary']} surface {pal['surface']} dominant {pal.get('dominant')}")

if __name__ == "__main__":
    main()
