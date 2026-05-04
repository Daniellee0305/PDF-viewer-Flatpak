#!/usr/bin/env python3
import sys
import os
import urllib.parse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1') # Using 4.1 for modern GNOME runtimes
from gi.repository import Gtk, WebKit2, GLib, Gio, Pango
import threading
import http.server
import socketserver

# A simple local HTTP server to serve the viewer and PDF files, completely bypassing CORS and file:// restrictions
class LocalFileServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/', **kwargs)
    def log_message(self, format, *args):
        pass # Suppress logs

httpd = socketserver.TCPServer(("127.0.0.1", 0), LocalFileServer)
LOCAL_PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

class DoqmentViewer(Gtk.ApplicationWindow):
    def __init__(self, app, pdf_path=None):
        super().__init__(application=app, title="Doqment")
        self.set_default_size(1024, 768)

        # 1. Design the Interface - Native GTK HeaderBar
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)
        self.header_bar.set_title("Doqment PDF Viewer")
        self.set_titlebar(self.header_bar)

        # Open Button
        open_button = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        open_button.set_tooltip_text("Open PDF Document in New Tab")
        open_button.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_button)

        # Sidebar Toggle Button
        sidebar_button = Gtk.Button.new_from_icon_name("view-sidebar-symbolic", Gtk.IconSize.BUTTON)
        sidebar_button.set_tooltip_text("Toggle Sidebar")
        sidebar_button.connect("clicked", self.on_sidebar_toggle)
        self.header_bar.pack_start(sidebar_button)

        # Pagination Controls
        page_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(page_box.get_style_context(), "linked")
        
        prev_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        prev_btn.set_tooltip_text("Previous Page")
        prev_btn.connect("clicked", self.on_prev_page)
        page_box.add(prev_btn)
        
        next_btn = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        next_btn.set_tooltip_text("Next Page")
        next_btn.connect("clicked", self.on_next_page)
        page_box.add(next_btn)
        
        self.header_bar.pack_start(page_box)

        # Zoom Controls
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(zoom_box.get_style_context(), "linked")
        
        zoom_out_btn = Gtk.Button.new_from_icon_name("zoom-out-symbolic", Gtk.IconSize.BUTTON)
        zoom_out_btn.set_tooltip_text("Zoom Out")
        zoom_out_btn.connect("clicked", self.on_zoom_out)
        zoom_box.add(zoom_out_btn)

        zoom_fit_btn = Gtk.Button.new_from_icon_name("zoom-fit-best-symbolic", Gtk.IconSize.BUTTON)
        zoom_fit_btn.set_tooltip_text("Adaptive Scaling (Fit Width)")
        zoom_fit_btn.connect("clicked", self.on_zoom_fit)
        zoom_box.add(zoom_fit_btn)

        zoom_in_btn = Gtk.Button.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)
        zoom_in_btn.set_tooltip_text("Zoom In")
        zoom_in_btn.connect("clicked", self.on_zoom_in)
        zoom_box.add(zoom_in_btn)
        
        self.header_bar.pack_end(zoom_box)

        # Theme Toggle
        theme_btn = Gtk.Button.new_from_icon_name("weather-clear-night-symbolic", Gtk.IconSize.BUTTON)
        theme_btn.set_tooltip_text("Toggle Reader Theme")
        theme_btn.connect("clicked", self.on_theme_toggle)
        self.header_bar.pack_end(theme_btn)

        # 2. Setup Notebook (Tabs - Firefox Style)
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self.on_tab_switched)
        self.add(self.notebook)

        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        viewer_local_path = os.path.join(self.base_dir, 'doqment', 'src', 'pdfjs', 'web', 'viewer.html')
        if not os.path.exists(viewer_local_path):
            viewer_local_path = os.path.join(os.path.dirname(self.base_dir), 'share', 'doqment', 'src', 'pdfjs', 'web', 'viewer.html')
            
        self.viewer_url = f"http://127.0.0.1:{LOCAL_PORT}" + os.path.abspath(viewer_local_path)

        if pdf_path:
            self.add_tab(pdf_path)
        else:
            # If launched without a file, just open an empty tab
            self.add_tab(None)

    def get_current_webview(self):
        page_num = self.notebook.get_current_page()
        if page_num >= 0:
            return self.notebook.get_nth_page(page_num)
        return None

    def add_tab(self, pdf_path):
        webview = WebKit2.WebView()
        webview.pdf_path = pdf_path # Attach custom property to store the path

        settings = webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_developer_extras(True)
        
        doq_inject_script = WebKit2.UserScript(
            f"import('http://127.0.0.1:{LOCAL_PORT}/app/share/doqment/src/doq/addon/doq.js').catch(e => console.error('Failed to load doq.js', e));",
            WebKit2.UserContentInjectedFrames.TOP_FRAME,
            WebKit2.UserScriptInjectionTime.END,
            None, None
        )
        webview.get_user_content_manager().add_script(doq_inject_script)

        hide_toolbar_script = WebKit2.UserScript(
            "document.head.insertAdjacentHTML('beforeend', '<style>#toolbarContainer { display: none !important; } #viewerContainer { top: 0 !important; }</style>');",
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserScriptInjectionTime.END,
            None, None
        )
        webview.get_user_content_manager().add_script(hide_toolbar_script)

        # Build Tab Label & Close Button
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        title = os.path.basename(pdf_path) if pdf_path else "New Document"
        
        tab_label = Gtk.Label(label=title)
        tab_label.set_max_width_chars(25)
        tab_label.set_ellipsize(Pango.EllipsizeMode.END)
        tab_box.pack_start(tab_label, True, True, 0)

        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", self.on_close_tab, webview)
        tab_box.pack_end(close_btn, False, False, 0)
        
        tab_box.show_all()

        # Load Document
        url = self.viewer_url
        if pdf_path:
            pdf_url = f"http://127.0.0.1:{LOCAL_PORT}" + urllib.parse.quote(os.path.abspath(pdf_path))
            url += "?file=" + urllib.parse.quote(pdf_url)
            
        webview.load_uri(url)
        webview.show_all()
        
        # Add to notebook and focus it
        page_num = self.notebook.append_page(webview, tab_box)
        self.notebook.set_current_page(page_num)

    def on_close_tab(self, button, webview):
        page_num = self.notebook.page_num(webview)
        if page_num >= 0:
            self.notebook.remove_page(page_num)
            webview.destroy()
        # Close the whole app if the last tab is closed
        if self.notebook.get_n_pages() == 0:
            self.close()

    def on_tab_switched(self, notebook, page, page_num):
        webview = notebook.get_nth_page(page_num)
        if webview and webview.pdf_path:
            self.header_bar.set_subtitle(os.path.basename(webview.pdf_path))
        else:
            self.header_bar.set_subtitle("No file loaded")

    # 3. Actions interacting with PDF.js via JS
    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserNative.new("Open PDF Document", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF files")
        filter_pdf.add_mime_type("application/pdf")
        dialog.add_filter(filter_pdf)
        
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.add_tab(dialog.get_filename())
        dialog.destroy()

    def on_zoom_in(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.zoomIn();", None, None, None)

    def on_zoom_out(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.zoomOut();", None, None, None)

    def on_zoom_fit(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.currentScaleValue = 'page-width';", None, None, None)

    def on_sidebar_toggle(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfSidebar.toggle();", None, None, None)

    def on_prev_page(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.previousPage();", None, None, None)

    def on_next_page(self, widget):
        wv = self.get_current_webview()
        if wv: wv.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.nextPage();", None, None, None)

    def on_theme_toggle(self, widget):
        wv = self.get_current_webview()
        if wv:
            js = """
            var radios = Array.from(document.querySelectorAll('#tonePicker input[type="radio"]'));
            if (radios.length > 0) {
                var idx = radios.findIndex(r => r.checked);
                var nextIdx = (idx + 1) % radios.length;
                radios[nextIdx].click();
            }
            """
            wv.run_javascript(js, None, None, None)

class DoqmentApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.daniellee0305.PdfDirectViewer", flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = DoqmentViewer(self)
        self.window.show_all()
        self.window.present()

    def do_open(self, files, n_files, hint):
        if not self.window:
            self.window = DoqmentViewer(self, files[0].get_path())
        else:
            self.window.add_tab(files[0].get_path())
        self.window.show_all()
        self.window.present()

if __name__ == "__main__":
    app = DoqmentApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
