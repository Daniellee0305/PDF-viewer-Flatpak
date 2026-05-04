#!/usr/bin/env python3
import sys
import os
import urllib.parse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1') # Using 4.1 for modern GNOME runtimes
from gi.repository import Gtk, WebKit2, GLib, Gio

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
        open_button.set_tooltip_text("Open PDF Document")
        open_button.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_button)

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

        # 2. Setup WebKit Webview
        self.webview = WebKit2.WebView()
        self.add(self.webview)

        # Flatpak resolves this as /app/bin/doqment-app.py, so assets are in /app/share/doqment/src
        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        self.viewer_path = os.path.join(self.base_dir, 'doqment', 'src', 'pdfjs', 'web', 'viewer.html')
        if not os.path.exists(self.viewer_path):
            self.viewer_path = os.path.join(os.path.dirname(self.base_dir), 'share', 'doqment', 'src', 'pdfjs', 'web', 'viewer.html')

        # Allow local file access for PDFs
        settings = self.webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_developer_extras(False)
        
        # We can inject CSS to hide the ugly web PDF.js toolbar to make it look completely native!
        hide_toolbar_script = WebKit2.UserScript(
            "document.head.insertAdjacentHTML('beforeend', '<style>#toolbarContainer { display: none !important; } #viewerContainer { top: 0 !important; }</style>');",
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserScriptInjectionTime.END,
            None, None
        )
        self.webview.get_user_content_manager().add_script(hide_toolbar_script)

        self.load_pdf(pdf_path)

    def load_pdf(self, pdf_path):
        url = "file://" + os.path.abspath(self.viewer_path)
        if pdf_path:
            url += "?file=" + urllib.parse.quote("file://" + os.path.abspath(pdf_path))
            self.header_bar.set_subtitle(os.path.basename(pdf_path))
        else:
            self.header_bar.set_subtitle("No file loaded")
            
        self.webview.load_uri(url)

    # 3. Actions interacting with PDF.js via JS
    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserNative.new("Open PDF Document", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF files")
        filter_pdf.add_mime_type("application/pdf")
        dialog.add_filter(filter_pdf)
        
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.load_pdf(dialog.get_filename())
        dialog.destroy()

    def on_zoom_in(self, widget):
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.zoomIn();", None, None, None)

    def on_zoom_out(self, widget):
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.zoomOut();", None, None, None)

    def on_zoom_fit(self, widget):
        # Adaptive scaling: Fit Width
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.currentScaleValue = 'page-width';", None, None, None)

class DoqmentApp(Gtk.Application):
    def __init__(self):
        # App ID updated to Daniellee0305
        super().__init__(application_id="io.github.daniellee0305.doqment", flags=Gio.ApplicationFlags.HANDLES_OPEN)
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
            self.window.load_pdf(files[0].get_path())
        self.window.show_all()
        self.window.present()

if __name__ == "__main__":
    app = DoqmentApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
