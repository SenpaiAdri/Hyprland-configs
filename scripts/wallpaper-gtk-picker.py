#!/usr/bin/env python3
# Wallpaper GTK Picker — MINIMAL — 2 column: left preview | right list
# Strict GTK-only. Fast switch: ↑/↓ navigate, Enter apply, Esc cancel
import os
import sys
import subprocess
import pathlib
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

WALL_DIR = os.path.expanduser("~/Pictures/wallpapers")
SCRIPT = os.path.expanduser("~/.config/hypr/scripts/wallpaper.sh")
CACHE_CURRENT = os.path.expanduser("~/.cache/current_wallpaper")
THUMB_SIZE = 72
# smaller window — was 1180×680, now 1024×600 (~13% smaller, same 1.7 ratio)
WIN_W, WIN_H = 1024, 500
PANED_POS = 600  # left preview column width (right ~424)
# cover target = left inner size minus borders (computed at runtime, fallback below)
PREVIEW_COVER_W, PREVIEW_COVER_H = 576, 468

def load_colors():
    colors = {
        "background": "#1e1e2e",
        "background_alt": "#181825",
        "foreground": "#cdd6f4",
        "selected": "#89b4fa",
        "active": "#6c7086",
    }
    rasi = os.path.expanduser("~/.config/rofi/colors.rasi")
    if os.path.exists(rasi):
        import re
        txt = open(rasi).read()
        for key, val in re.findall(r'(\w+):\s*(#[0-9a-fA-F]{6})', txt):
            if key == "background":
                colors["background"] = val
            if key == "background-alt":
                colors["background_alt"] = val
            if key == "selected":
                colors["selected"] = val
            if key == "foreground":
                colors["foreground"] = val
    return colors

COLORS = load_colors()

def get_walls():
    exts = {'.jpg','.jpeg','.png','.webp'}
    walls = []
    if not os.path.isdir(WALL_DIR):
        return walls
    for f in os.listdir(WALL_DIR):
        p = os.path.join(WALL_DIR, f)
        if os.path.isfile(p) and pathlib.Path(f).suffix.lower() in exts:
            walls.append(p)
    walls.sort()
    return walls

def current_wallpaper():
    if os.path.exists(CACHE_CURRENT):
        return open(CACHE_CURRENT).read().strip()
    return ""

class WallpaperPicker(Gtk.Window):
    def __init__(self):
        super().__init__(title="Wallpaper Picker")
        self.set_default_size(WIN_W, WIN_H)
        self.set_size_request(WIN_W, WIN_H)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        try:
            self.set_wmclass("wallpaper-picker", "wallpaper-picker")
        except:
            pass
        self.set_role("wallpaper-picker")
        try:
            GLib.set_prgname("wallpaper-picker")
        except:
            pass
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", Gtk.main_quit)
        self.walls = get_walls()
        if not self.walls:
            print(f"No wallpapers in {WALL_DIR}", file=sys.stderr)
            sys.exit(1)
        self.current = current_wallpaper()
        self.selected_path = None
        self.preview_cache = {}
        self._preview_timeout = None
        self._pending_preview = None
        self.setup_css()
        self.build_ui()
        GLib.idle_add(self.populate_list_idle)
        GLib.idle_add(self.select_initial)
        GLib.timeout_add(150, self._kick_preload)

    def setup_css(self):
        c = COLORS
        css = f"""
        window {{
            background-color: {c['background']};
            border-radius: 16px;
        }}
        decoration {{
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.45), 0 2px 12px rgba(0,0,0,0.3);
        }}
        .preview-box {{
            background-color: {c['background_alt']};
            border-radius: 16px;
            margin: 14px 6px 14px 14px;
            border: 1px solid alpha({c['foreground']}, 0.07);
            padding: 0;
        }}
        .preview-image {{
            background-color: {c['background_alt']};
            border-radius: 15px;
            border: none;
        }}
        .choice-list {{
            background-color: transparent;
        }}
        .choice-scrolled {{
            background-color: transparent;
            border: none;
        }}
        .choice-scrolled viewport {{
            background-color: transparent;
        }}
        .choice-row {{
            background-color: alpha({c['foreground']}, 0.035);
            border-radius: 14px;
            margin: 5px 10px 5px 8px;
            padding: 6px;
            border: 1px solid alpha({c['foreground']}, 0.05);
        }}
        .choice-row:hover {{
            background-color: alpha({c['selected']}, 0.11);
            border-color: alpha({c['selected']}, 0.18);
        }}
        .choice-row:selected {{
            background-color: {c['selected']};
            border-color: {c['selected']};
        }}
        .choice-row:selected label {{
            color: {c['background']};
        }}
        .choice-row:selected .thumb {{
            border-color: alpha({c['background']}, 0.28);
        }}
        .thumb {{
            background-color: {c['background']};
            border: 1px solid alpha({c['foreground']}, 0.07);
        }}
        .file-name {{
            font-family: 'Inter', 'Cantarell', sans-serif;
            font-size: 10.5pt;
            font-weight: 500;
            color: {c['foreground']};
            letter-spacing: 0.1px;
        }}
        .file-ext {{
            font-family: 'Inter', 'Cantarell', monospace;
            font-size: 8.5pt;
            font-weight: 600;
            color: alpha({c['foreground']}, 0.42);
            letter-spacing: 0.5px;
        }}
        .choice-row:selected .file-ext {{
            color: alpha({c['background']}, 0.62);
        }}
        scrollbar.vertical slider {{
            background-color: alpha({c['active']}, 0.42);
            border-radius: 10px;
            min-width: 5px;
            min-height: 42px;
            border: none;
        }}
        scrollbar.vertical slider:hover {{
            background-color: alpha({c['selected']}, 0.58);
            min-width: 6px;
        }}
        scrollbar.vertical trough {{
            background-color: transparent;
        }}
        .paned separator {{
            background-color: alpha({c['foreground']}, 0.07);
            min-width: 1px;
        }}
        .paned separator:hover {{
            background-color: alpha({c['selected']}, 0.18);
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        screen = Gdk.Screen.get_default()
        if screen is None:
            screen = self.get_screen()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.get_style_context().add_class("paned")
        paned.set_position(PANED_POS)
        paned.set_wide_handle(False)
        self.add(paned)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.get_style_context().add_class("preview-box")
        self.left = left
        # preview fills entire left column — object-cover (Tailwind) — no padding, image expands
        self.preview_image = Gtk.Image()
        self.preview_image.get_style_context().add_class("preview-image")
        self.preview_image.set_hexpand(True)
        self.preview_image.set_vexpand(True)
        self.preview_image.set_halign(Gtk.Align.FILL)
        self.preview_image.set_valign(Gtk.Align.FILL)
        self.preview_image.set_from_icon_name("preferences-desktop-wallpaper", Gtk.IconSize.DIALOG)
        self.preview_image.set_pixel_size(96)
        # wrap in EventBox so border-radius clips correctly and image can expand
        left.pack_start(self.preview_image, True, True, 0)
        paned.pack1(left, resize=False, shrink=False)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.set_margin_top(8)
        right.set_margin_bottom(8)
        right.set_margin_start(2)
        right.set_margin_end(6)
        scrolled = Gtk.ScrolledWindow()
        scrolled.get_style_context().add_class("choice-scrolled")
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(False)
        scrolled.set_overlay_scrolling(False)
        scrolled.set_min_content_width(404)
        scrolled.set_propagate_natural_width(False)
        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("choice-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_can_focus(True)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.connect("row-selected", self.on_row_selected)
        self.listbox.connect("row-activated", self.on_row_activated)
        scrolled.add(self.listbox)
        right.pack_start(scrolled, True, True, 0)
        paned.pack2(right, resize=True, shrink=True)

        self.paned = paned
        self.show_all()
        GLib.idle_add(lambda: paned.set_position(PANED_POS) or False)
        self.listbox.set_can_focus(True)
        self.listbox.set_focus_on_click(True)
        GLib.timeout_add(80, self._focus_list)
        GLib.timeout_add(300, self._focus_list)

    def populate_list_idle(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self.rows = []
        for path in self.walls:
            row = self.create_row(path)
            self.listbox.add(row)
            self.rows.append((path, row))
        self.listbox.show_all()
        return False

    def get_thumb_path(self, path):
        thumb_dir = os.path.expanduser("~/.cache/wallpaper-thumbs")
        base = os.path.basename(path)
        return os.path.join(thumb_dir, os.path.splitext(base)[0] + ".png")

    def create_row(self, path):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("choice-row")
        row.path = path
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_start(6)
        hbox.set_margin_end(10)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        hbox.set_hexpand(False)
        hbox.set_halign(Gtk.Align.FILL)

        thumb = Gtk.Image()
        thumb.get_style_context().add_class("thumb")
        thumb.set_size_request(THUMB_SIZE, THUMB_SIZE)
        thumb.set_halign(Gtk.Align.START)
        thumb.set_valign(Gtk.Align.CENTER)
        tp = self.get_thumb_path(path)
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(tp, THUMB_SIZE, THUMB_SIZE, True)
        thumb.set_from_pixbuf(pix)
        # clip thumb to fixed box so it never expands into preview column
        thumb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        thumb_box.set_size_request(THUMB_SIZE, THUMB_SIZE)
        thumb_box.set_halign(Gtk.Align.START)
        thumb_box.set_valign(Gtk.Align.CENTER)
        thumb_box.pack_start(thumb, False, False, 0)
        hbox.pack_start(thumb_box, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_halign(Gtk.Align.FILL)
        vbox.set_hexpand(True)

        base = os.path.basename(path)
        name, ext = os.path.splitext(base)
        label = Gtk.Label(label=name)
        label.get_style_context().add_class("file-name")
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_ellipsize(3)  # END
        label.set_max_width_chars(22)
        label.set_hexpand(True)
        label.set_line_wrap(False)
        label.set_tooltip_text(path)
        vbox.pack_start(label, False, False, 0)

        ext_label = Gtk.Label(label=ext.lstrip('.').upper() if ext else "")
        ext_label.get_style_context().add_class("file-ext")
        ext_label.set_halign(Gtk.Align.START)
        ext_label.set_valign(Gtk.Align.CENTER)
        ext_label.set_ellipsize(3)
        vbox.pack_start(ext_label, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)

        # chevron hint — stays inside row, won't overlap preview
        chev = Gtk.Label(label="›")
        chev.get_style_context().add_class("file-ext")
        chev.set_halign(Gtk.Align.END)
        chev.set_valign(Gtk.Align.CENTER)
        chev.set_margin_end(2)
        hbox.pack_start(chev, False, False, 0)

        row.add(hbox)
        row.show_all()
        return row

    def _focus_list(self):
        try:
            self.present()
            self.set_focus(self.listbox)
            self.listbox.grab_focus()
            row = self.listbox.get_selected_row()
            if row:
                row.grab_focus()
        except Exception as e:
            print(f"focus failed: {e}", file=sys.stderr)
        return False

    def select_initial(self):
        target = self.current if self.current in self.walls else (self.walls[0] if self.walls else None)
        if target:
            for p, r in self.rows:
                if p == target:
                    self.listbox.select_row(r)
                    break
        elif self.walls:
            self.listbox.select_row(self.rows[0][1])
        self._focus_list()
        GLib.timeout_add(100, self._focus_list)
        return False

    def _get_preview_target(self):
        # fixed object-cover size for Tailwind-style fill — keeps window at WIN_W×WIN_H
        # dynamic allocation previously caused loop: larger allocation → larger cover → larger window (656)
        return (PREVIEW_COVER_W, PREVIEW_COVER_H)

    def _cover_pixbuf(self, path, tw, th):
        # Tailwind object-cover: scale to fill, center-crop — preserves aspect, no letterbox
        src = GdkPixbuf.Pixbuf.new_from_file(path)
        sw, sh = src.get_width(), src.get_height()
        if sw <= 0 or sh <= 0:
            raise ValueError("invalid image size")
        scale = max(tw / sw, th / sh)
        nw = int(sw * scale + 0.5)
        nh = int(sh * scale + 0.5)
        if nw < tw:
            nw = tw
        if nh < th:
            nh = th
        scaled = src.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
        if scaled is None:
            raise RuntimeError("scale failed")
        x = max(0, (nw - tw) // 2)
        y = max(0, (nh - th) // 2)
        # clamp to scaled size
        tw = min(tw, nw - x)
        th = min(th, nh - y)
        cropped = scaled.new_subpixbuf(x, y, tw, th)
        # copy to detach from parent (avoids lifetime issues on some GTK versions)
        return cropped.copy() if hasattr(cropped, "copy") else cropped

    def update_preview(self, path):
        if not path or not os.path.exists(path):
            return
        self.selected_path = path
        tw, th = self._get_preview_target()
        cached = self.preview_cache.get(path)
        if cached is not None:
            # check cached size matches current target — if window resized, regenerate
            if cached.get_width() == tw and cached.get_height() == th:
                self.preview_image.set_from_pixbuf(cached)
                return
        # instant thumb placeholder — also cover so no letterbox flash
        try:
            tp = self.get_thumb_path(path)
            # fast cover from thumb (tiny, ~256px) — looks filled immediately before HQ loads
            pix = self._cover_pixbuf(tp, tw, th)
            self.preview_image.set_from_pixbuf(pix)
        except:
            pass
        if self._preview_timeout is not None:
            try:
                GLib.source_remove(self._preview_timeout)
            except:
                pass
            self._preview_timeout = None
        self._pending_preview = path
        self._preview_timeout = GLib.timeout_add(22, self._trigger_preview_load)

    def _trigger_preview_load(self):
        path = self._pending_preview
        self._preview_timeout = None
        self._pending_preview = None
        tw, th = self._get_preview_target()
        if not path:
            return False
        cached = self.preview_cache.get(path)
        if cached is not None and cached.get_width() == tw and cached.get_height() == th:
            if self.selected_path == path:
                self.preview_image.set_from_pixbuf(cached)
            return False
        def do_load():
            try:
                pix = self._cover_pixbuf(path, tw, th)
            except Exception as e:
                print(f"cover failed {path}: {e}", file=sys.stderr)
                return
            self.preview_cache[path] = pix
            GLib.idle_add(lambda: self._on_preview_loaded(path, pix) or False)
            for nb in self._neighbor_paths(path):
                if nb not in self.preview_cache:
                    try:
                        pix2 = self._cover_pixbuf(nb, tw, th)
                        self.preview_cache[nb] = pix2
                    except:
                        pass
        threading.Thread(target=do_load, daemon=True).start()
        return False

    def _on_preview_loaded(self, path, pix):
        if self.selected_path == path:
            self.preview_image.set_from_pixbuf(pix)
        return False

    def _neighbor_paths(self, path):
        idx = self.walls.index(path)
        res = []
        if idx > 0:
            res.append(self.walls[idx-1])
        if idx + 1 < len(self.walls):
            res.append(self.walls[idx+1])
        return res

    def _kick_preload(self):
        tw, th = self._get_preview_target()
        def preload_all():
            for p in self.walls:
                if p not in self.preview_cache:
                    try:
                        pix = self._cover_pixbuf(p, tw, th)
                        self.preview_cache[p] = pix
                    except:
                        pass
            if self.selected_path and self.selected_path in self.preview_cache:
                GLib.idle_add(lambda: self._on_preview_loaded(self.selected_path, self.preview_cache[self.selected_path]) or False)
        threading.Thread(target=preload_all, daemon=True).start()
        return False

    def on_row_selected(self, lb, row):
        if row:
            p = getattr(row, 'path', None)
            if p:
                self.update_preview(p)

    def on_row_activated(self, lb, row):
        if row:
            p = getattr(row, 'path', None)
            if p:
                self.apply_wallpaper(p)

    def apply_wallpaper(self, path):
        subprocess.Popen([SCRIPT, path])
        GLib.timeout_add(200, Gtk.main_quit)

    def _move_selection(self, direction):
        visible = [r for p, r in self.rows if r.get_visible()]
        if not visible:
            return False
        cur = self.listbox.get_selected_row()
        if cur is None:
            self.listbox.select_row(visible[0])
            return True
        idx = visible.index(cur) if cur in visible else 0
        new_idx = max(0, min(idx + direction, len(visible)-1))
        if new_idx != idx:
            self.listbox.select_row(visible[new_idx])
            visible[new_idx].grab_focus()
        return True

    def on_key(self, w, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            Gtk.main_quit()
            return True
        if key in ("Return", "KP_Enter", "ISO_Enter"):
            row = self.listbox.get_selected_row()
            if row:
                p = getattr(row, 'path', None)
                if p:
                    self.apply_wallpaper(p)
                    return True
        if key in ("Up", "KP_Up", "k", "K"):
            return self._move_selection(-1)
        if key in ("Down", "KP_Down", "j", "J"):
            return self._move_selection(1)
        return False

def main():
    walls = get_walls()
    if not walls:
        print(f"No wallpapers in {WALL_DIR}", file=sys.stderr)
        sys.exit(1)
    app = WallpaperPicker()
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
