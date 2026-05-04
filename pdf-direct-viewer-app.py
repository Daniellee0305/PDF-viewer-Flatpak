#!/usr/bin/env python3
import sys
import os
import urllib.parse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1') 
from gi.repository import Gtk, WebKit2, GLib, Gio, Pango, Gdk
import threading
import http.server
import socketserver

# A simple local HTTP server to serve the pre-built PDF.js and documents
class LocalFileServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/', **kwargs)
    def log_message(self, format, *args):
        pass

httpd = socketserver.TCPServer(("127.0.0.1", 0), LocalFileServer)
LOCAL_PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

class PdfDirectViewer(Gtk.ApplicationWindow):
    def __init__(self, app, pdf_path=None):
        super().__init__(application=app, title="PDF Direct Viewer")
        self.set_default_size(1024, 768)

        # 1. Interface Design
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)
        self.header_bar.set_title("PDF Direct Viewer")
        self.set_titlebar(self.header_bar)

        open_button = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        open_button.set_tooltip_text("Open PDF Document in New Tab")
        open_button.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_button)

        # Theme/Color Palette Button
        palette_button = Gtk.MenuButton()
        palette_button.set_image(Gtk.Image.new_from_icon_name("applications-graphics-symbolic", Gtk.IconSize.BUTTON))
        palette_button.set_tooltip_text("Reader Mode Color Palette")
        
        palette_popover = Gtk.Popover()
        palette_grid = Gtk.Grid()
        palette_grid.set_column_spacing(5)
        palette_grid.set_row_spacing(5)
        palette_grid.set_margin_start(10)
        palette_grid.set_margin_end(10)
        palette_grid.set_margin_top(10)
        palette_grid.set_margin_bottom(10)

        # Define color presets (Background, Text)
        colors = [
            ("Light", "#ffffff", "#000000"),
            ("Dark", "#121212", "#e0e0e0"),
            ("Sepia", "#f4ecd8", "#5b4636"),
            ("Green", "#0a1a0a", "#00ff00"),
            ("Blue", "#e3edff", "#001a4d"),
            ("Contrast", "#000000", "#ffff00")
        ]

        for i, (name, bg, fg) in enumerate(colors):
            btn = Gtk.Button()
            btn.set_tooltip_text(name)
            btn.set_size_request(30, 30)
            btn.get_style_context().add_class("circular")
            # Apply color to the button itself
            btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA())
            rgba_bg = Gdk.RGBA()
            rgba_bg.parse(bg)
            btn.override_background_color(Gtk.StateFlags.NORMAL, rgba_bg)
            btn.connect("clicked", self.on_palette_color_selected, bg, fg)
            palette_grid.attach(btn, i % 3, i // 3, 1, 1)

        palette_grid.show_all()
        palette_popover.add(palette_grid)
        palette_button.set_popover(palette_popover)
        self.header_bar.pack_end(palette_button)

        # 2. Setup Notebook (Tabs)
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self.on_tab_switched)
        self.add(self.notebook)

        self.viewer_url = f"http://127.0.0.1:{LOCAL_PORT}/app/share/pdfjs/web/viewer.html"

        if pdf_path:
            self.add_tab(pdf_path)
        else:
            self.add_tab(None)

        # Drag and Drop support
        TARGET_ENTRY_URI_LIST = Gtk.TargetEntry.new("text/uri-list", 0, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [TARGET_ENTRY_URI_LIST], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        uris = data.get_uris()
        for uri in uris:
            if uri.startswith("file://"):
                pdf_path = urllib.parse.unquote(uri[7:])
                self.add_tab(pdf_path)
        Gtk.drag_finish(drag_context, True, False, time)

    def get_current_webview(self):
        page_num = self.notebook.get_current_page()
        if page_num >= 0:
            return self.notebook.get_nth_page(page_num)
        return None

    def add_tab(self, pdf_path):
        webview = WebKit2.WebView()
        webview.pdf_path = pdf_path

        settings = webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        
        # Invert colors logic via CSS injection for native Firefox-like feel
        # This will be controlled by the palette
        
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        title = os.path.basename(pdf_path) if pdf_path else "Firefox PDF Engine"
        tab_label = Gtk.Label(label=title)
        tab_label.set_max_width_chars(25)
        tab_label.set_ellipsize(Pango.EllipsizeMode.END)
        tab_box.pack_start(tab_label, True, True, 0)

        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", self.on_close_tab, webview)
        tab_box.pack_end(close_btn, False, False, 0)
        
        tab_box.show_all()
        webview.show_all()
        
        url = self.viewer_url
        if pdf_path:
            pdf_url = f"http://127.0.0.1:{LOCAL_PORT}" + urllib.parse.quote(os.path.abspath(pdf_path))
            url += "?file=" + urllib.parse.quote(pdf_url)
            
        webview.load_uri(url)
        page_num = self.notebook.append_page(webview, tab_box)
        self.notebook.set_current_page(page_num)

    def on_close_tab(self, button, webview):
        page_num = self.notebook.page_num(webview)
        if page_num >= 0:
            self.notebook.remove_page(page_num)
            webview.destroy()
        if self.notebook.get_n_pages() == 0:
            self.close()

    def on_tab_switched(self, notebook, page, page_num):
        webview = notebook.get_nth_page(page_num)
        if webview and webview.pdf_path:
            self.header_bar.set_subtitle(os.path.basename(webview.pdf_path))
        else:
            self.header_bar.set_subtitle("Powered by Firefox PDF.js")

    def on_palette_color_selected(self, button, bg, fg):
        webview = self.get_current_webview()
        if not webview: return
        
        # Inject advanced CSS filter to modify PDF.js rendering colors dynamically
        # This is the "Lightweight" way to change colors without re-rendering the whole PDF
        js = f"""
        (function() {{
            var style = document.getElementById('reader-mode-style');
            if (!style) {{
                style = document.createElement('style');
                style.id = 'reader-mode-style';
                document.head.appendChild(style);
            }}
            
            // Apply color to the entire viewer container
            style.innerHTML = `
                #viewerContainer, .pdfViewer {{ background-color: {bg} !important; }}
                .page {{ 
                    filter: brightness(0.8) contrast(1.2); 
                    background-color: {bg} !important;
                }}
                canvas {{ 
                    filter: invert({ "1" if bg != "#ffffff" else "0" }) hue-rotate(180deg) brightness(1.1); 
                }}
                .textLayer {{ mix-blend-mode: multiply; color: {fg} !important; }}
            `;
            
            // Special handling for predefined themes
            if ("{bg}" == "#ffffff") {{
                style.innerHTML = ""; // Reset to original
            }} else if ("{bg}" == "#f4ecd8") {{ // Sepia
                style.innerHTML = `
                    #viewerContainer, .pdfViewer {{ background-color: #f4ecd8 !important; }}
                    canvas {{ filter: sepia(0.8) contrast(1.1); }}
                `;
            }}
        }})();
        """
        webview.run_javascript(js, None, None, None)

    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserNative.new("Open PDF Document", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF files")
        filter_pdf.add_mime_type("application/pdf")
        dialog.add_filter(filter_pdf)
        dialog.connect("response", self.on_file_chooser_response)
        dialog.show()

    def on_file_chooser_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.add_tab(dialog.get_filename())
        dialog.destroy()

class PdfDirectApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.daniellee0305.PdfDirectViewer", flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = PdfDirectViewer(self)
        self.window.show_all()
        self.window.present()

    def do_open(self, files, n_files, hint):
        if not self.window:
            self.window = PdfDirectViewer(self, files[0].get_path())
        else:
            self.window.add_tab(files[0].get_path())
        self.window.show_all()
        self.window.present()

if __name__ == "__main__":
    app = PdfDirectApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
