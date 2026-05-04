#!/usr/bin/env python3
"""
PDF Direct Viewer
A native Linux PDF reader powered by Mozilla's PDF.js engine.
Features multi-tab browsing and a customizable color palette for reader mode.

Copyright (c) 2026 Daniel Lee
Licensed under the MIT License.
"""
import sys
import os
import urllib.parse
import threading
import http.server
import socketserver

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib, Gio, Pango, Gdk


# ---------------------------------------------------------------------------
# 1. Local HTTP server
#    WebKit2GTK in Flatpak blocks file:// access due to sandboxing.
#    We spin up a tiny HTTP server on 127.0.0.1 to serve both the PDF.js
#    viewer assets and the user's local PDF files.
# ---------------------------------------------------------------------------
class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves any file under / via HTTP, with logging suppressed."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/', **kwargs)

    def log_message(self, format, *args):
        pass  # keep the terminal clean

_server = socketserver.TCPServer(("127.0.0.1", 0), _QuietHandler)
SERVER_PORT = _server.server_address[1]
threading.Thread(target=_server.serve_forever, daemon=True).start()

# Path to the bundled PDF.js viewer inside the Flatpak
PDFJS_VIEWER = f"http://127.0.0.1:{SERVER_PORT}/app/share/pdfjs/web/viewer.html"


# ---------------------------------------------------------------------------
# 2. Color palette presets
#    Each entry: (Display name, CSS background color, CSS text hint color)
# ---------------------------------------------------------------------------
COLOR_PRESETS = [
    ("Original",       "#ffffff", "#000000"),
    ("Dark",           "#1a1a2e", "#e0e0e0"),
    ("Sepia",          "#f4ecd8", "#5b4636"),
    ("Night Green",    "#0d1117", "#39d353"),
    ("Ocean Blue",     "#0d1b2a", "#e0e1dd"),
    ("High Contrast",  "#000000", "#ffff00"),
    ("Rose",           "#2d142c", "#e8a0bf"),
    ("Slate",          "#1e293b", "#cbd5e1"),
    ("Cream",          "#fdf6e3", "#657b83"),
]


# ---------------------------------------------------------------------------
# 3. Main application window
# ---------------------------------------------------------------------------
class PdfDirectViewer(Gtk.ApplicationWindow):

    def __init__(self, app, pdf_path=None):
        super().__init__(application=app, title="PDF Direct Viewer")
        self.set_default_size(1100, 800)

        # ---- Header bar ----
        self.hbar = Gtk.HeaderBar()
        self.hbar.set_show_close_button(True)
        self.hbar.set_title("PDF Direct Viewer")
        self.hbar.set_subtitle("Powered by Mozilla PDF.js")
        self.set_titlebar(self.hbar)

        # Open button (left)
        btn_open = Gtk.Button.new_from_icon_name(
            "document-open-symbolic", Gtk.IconSize.BUTTON)
        btn_open.set_tooltip_text("Open PDF file in a new tab")
        btn_open.connect("clicked", self._on_open_clicked)
        self.hbar.pack_start(btn_open)

        # Color palette button (right)
        palette_mbtn = Gtk.MenuButton()
        palette_mbtn.set_image(Gtk.Image.new_from_icon_name(
            "applications-graphics-symbolic", Gtk.IconSize.BUTTON))
        palette_mbtn.set_tooltip_text("Reader color theme")

        popover = Gtk.Popover()
        grid = Gtk.Grid(column_spacing=6, row_spacing=6)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)

        for idx, (name, bg, _fg) in enumerate(COLOR_PRESETS):
            btn = Gtk.Button()
            btn.set_tooltip_text(name)
            btn.set_size_request(32, 32)
            btn.get_style_context().add_class("circular")
            rgba = Gdk.RGBA()
            rgba.parse(bg)
            btn.override_background_color(Gtk.StateFlags.NORMAL, rgba)
            btn.connect("clicked", self._on_palette_clicked, idx)
            grid.attach(btn, idx % 3, idx // 3, 1, 1)

        grid.show_all()
        popover.add(grid)
        palette_mbtn.set_popover(popover)
        self.hbar.pack_end(palette_mbtn)

        # ---- Notebook (tabbed interface) ----
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self._on_tab_switched)
        self.add(self.notebook)

        # Open initial tab
        if pdf_path:
            self.add_tab(pdf_path)
        else:
            self.add_tab(None)

        # ---- Drag & drop ----
        target = Gtk.TargetEntry.new("text/uri-list", 0, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [target], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self._on_drag_data)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------
    def add_tab(self, pdf_path):
        """Create a new tab with a WebKit view loading the PDF.js viewer."""
        wv = WebKit2.WebView()
        wv.pdf_path = pdf_path  # stash the path on the widget

        settings = wv.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)

        # Tab label with a close button
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label_text = os.path.basename(pdf_path) if pdf_path else "New Tab"
        label = Gtk.Label(label=label_text)
        label.set_max_width_chars(25)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        box.pack_start(label, True, True, 0)

        close_btn = Gtk.Button.new_from_icon_name(
            "window-close-symbolic", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", self._on_close_tab, wv)
        box.pack_end(close_btn, False, False, 0)

        box.show_all()
        wv.show()

        # Build the URL for PDF.js
        url = PDFJS_VIEWER
        if pdf_path:
            abs_path = os.path.abspath(pdf_path)
            file_url = (f"http://127.0.0.1:{SERVER_PORT}"
                        + urllib.parse.quote(abs_path))
            url += "?file=" + urllib.parse.quote(file_url)

        wv.load_uri(url)
        page_idx = self.notebook.append_page(wv, box)
        self.notebook.set_current_page(page_idx)

    def _on_close_tab(self, _btn, wv):
        idx = self.notebook.page_num(wv)
        if idx >= 0:
            self.notebook.remove_page(idx)
            wv.destroy()
        if self.notebook.get_n_pages() == 0:
            self.close()

    def _on_tab_switched(self, _nb, page, _idx):
        path = getattr(page, "pdf_path", None)
        if path:
            self.hbar.set_subtitle(os.path.basename(path))
        else:
            self.hbar.set_subtitle("Powered by Mozilla PDF.js")

    # ------------------------------------------------------------------
    # Color palette  (inject CSS into the PDF.js viewer at runtime)
    # ------------------------------------------------------------------
    def _current_webview(self):
        idx = self.notebook.get_current_page()
        return self.notebook.get_nth_page(idx) if idx >= 0 else None

    def _on_palette_clicked(self, _btn, preset_idx):
        wv = self._current_webview()
        if wv is None:
            return

        name, bg, _fg = COLOR_PRESETS[preset_idx]

        if name == "Original":
            # Remove all custom styling → back to default white
            js = "(function(){var s=document.getElementById('pdv-theme');" \
                 "if(s)s.remove();})();"

        elif name in ("Sepia", "Cream"):
            # Warm tint via CSS sepia filter
            js = f"""(function(){{
                var s=document.getElementById('pdv-theme');
                if(!s){{s=document.createElement('style');
                    s.id='pdv-theme';document.head.appendChild(s);}}
                s.textContent=`
                    #viewerContainer{{background:{bg}!important}}
                    .page{{background:{bg}!important}}
                    .canvasWrapper canvas{{
                        filter:sepia(0.55) contrast(1.05) brightness(0.95);}}
                `;
            }})();"""

        else:
            # Dark / colored themes: invert + hue-rotate preserves readability
            js = f"""(function(){{
                var s=document.getElementById('pdv-theme');
                if(!s){{s=document.createElement('style');
                    s.id='pdv-theme';document.head.appendChild(s);}}
                s.textContent=`
                    #viewerContainer{{background:{bg}!important}}
                    .page{{background:{bg}!important}}
                    .canvasWrapper canvas{{
                        filter:invert(1) hue-rotate(180deg)
                               brightness(1.05) contrast(1.1);}}
                    .textLayer{{mix-blend-mode:difference}}
                `;
            }})();"""

        wv.run_javascript(js, None, None, None)

    # ------------------------------------------------------------------
    # File open dialog  (async to avoid Flatpak portal crash)
    # ------------------------------------------------------------------
    def _on_open_clicked(self, _btn):
        dlg = Gtk.FileChooserNative.new(
            "Open PDF", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        pdf_filter = Gtk.FileFilter()
        pdf_filter.set_name("PDF files")
        pdf_filter.add_mime_type("application/pdf")
        dlg.add_filter(pdf_filter)
        dlg.connect("response", self._on_file_response)
        dlg.show()

    def _on_file_response(self, dlg, resp):
        if resp == Gtk.ResponseType.ACCEPT:
            self.add_tab(dlg.get_filename())
        dlg.destroy()

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------
    def _on_drag_data(self, _w, ctx, _x, _y, data, _info, time):
        for uri in data.get_uris():
            if uri.startswith("file://"):
                self.add_tab(urllib.parse.unquote(uri[7:]))
        Gtk.drag_finish(ctx, True, False, time)


# ---------------------------------------------------------------------------
# 4. Gtk.Application
# ---------------------------------------------------------------------------
class PdfDirectApp(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id="io.github.daniellee0305.PdfDirectViewer",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = PdfDirectViewer(self)
        self.window.show_all()
        self.window.present()

    def do_open(self, files, _n_files, _hint):
        self.do_activate()
        for f in files:
            self.window.add_tab(f.get_path())


if __name__ == "__main__":
    app = PdfDirectApp()
    sys.exit(app.run(sys.argv))
