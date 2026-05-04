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
        settings.set_enable_developer_extras(True) # Enabled for debugging
        
        # Inject doqment extension modules into the viewer
        doq_inject_script = WebKit2.UserScript(
            "import('file:///app/share/doqment/src/doq/addon/doq.js').catch(e => console.error('Failed to load doq.js', e));",
            WebKit2.UserContentInjectedFrames.TOP_FRAME,
            WebKit2.UserScriptInjectionTime.END,
            None, None
        )
        self.webview.get_user_content_manager().add_script(doq_inject_script)

        # Connect load-changed to open the PDF safely after the viewer initializes
        self.webview.connect("load-changed", self.on_load_changed)
        self.current_pdf_path = pdf_path
        
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
        self.current_pdf_path = pdf_path
        url = "file://" + os.path.abspath(self.viewer_path)
        if pdf_path:
            self.header_bar.set_subtitle(os.path.basename(pdf_path))
        else:
            self.header_bar.set_subtitle("No file loaded")
            
        self.webview.load_uri(url)

    def on_load_changed(self, webview, event):
        # Read the PDF directly in Python to bypass ALL WebKit and PDF.js local file/CORS security blocks
        if event == WebKit2.LoadEvent.FINISHED and self.current_pdf_path:
            import base64
            try:
                with open(self.current_pdf_path, "rb") as f:
                    pdf_b64 = base64.b64encode(f.read()).decode('ascii')
                
                # Pass the raw PDF binary data directly into memory
                js = f"""
                setTimeout(function() {{
                    if(window.PDFViewerApplication) {{
                        var pdfData = atob('{pdf_b64}');
                        var uint8Array = new Uint8Array(pdfData.length);
                        for (var i = 0; i < pdfData.length; i++) {{
                            uint8Array[i] = pdfData.charCodeAt(i);
                        }}
                        PDFViewerApplication.open(uint8Array);
                    }}
                }}, 500);
                """
                self.webview.run_javascript(js, None, None, None)
            except Exception as e:
                print("Failed to read or load PDF data:", e)

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

    def on_sidebar_toggle(self, widget):
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfSidebar.toggle();", None, None, None)

    def on_prev_page(self, widget):
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.previousPage();", None, None, None)

    def on_next_page(self, widget):
        self.webview.run_javascript("if(window.PDFViewerApplication) PDFViewerApplication.pdfViewer.nextPage();", None, None, None)

    def on_theme_toggle(self, widget):
        # Cycle through available doqment themes via the hidden radio buttons
        js = """
        var radios = Array.from(document.querySelectorAll('#tonePicker input[type="radio"]'));
        if (radios.length > 0) {
            var idx = radios.findIndex(r => r.checked);
            var nextIdx = (idx + 1) % radios.length;
            radios[nextIdx].click();
        }
        """
        self.webview.run_javascript(js, None, None, None)

class DoqmentApp(Gtk.Application):
    def __init__(self):
        # App ID updated to Daniellee0305
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
            self.window.load_pdf(files[0].get_path())
        self.window.show_all()
        self.window.present()

if __name__ == "__main__":
    app = DoqmentApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
