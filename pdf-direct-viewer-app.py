#!/usr/bin/env python3
import sys
import os
import urllib.parse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Poppler', '0.18')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, Poppler
import cairo

class PdfTab(Gtk.ScrolledWindow):
    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.current_page_idx = 0
        self.zoom = 1.0
        self.dark_mode = False
        
        self.document = None
        if pdf_path and os.path.exists(pdf_path):
            uri = "file://" + urllib.parse.quote(os.path.abspath(pdf_path))
            try:
                self.document = Poppler.Document.new_from_file(uri, None)
            except GLib.Error as e:
                print(f"Failed to load PDF: {e}")
                
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self.on_draw)
        
        # Add a viewport to enable scrolling for the DrawingArea
        self.viewport = Gtk.Viewport()
        self.viewport.add(self.drawing_area)
        self.add(self.viewport)
        self.update_size()

    def update_size(self):
        if not self.document:
            self.drawing_area.set_size_request(800, 600)
            return
            
        page = self.document.get_page(self.current_page_idx)
        width, height = page.get_size()
        self.drawing_area.set_size_request(int(width * self.zoom), int(height * self.zoom))
        self.drawing_area.queue_draw()

    def on_draw(self, widget, cr):
        if not self.document:
            cr.set_source_rgb(0.9, 0.9, 0.9)
            cr.paint()
            return

        page = self.document.get_page(self.current_page_idx)
        width, height = page.get_size()

        cr.scale(self.zoom, self.zoom)

        if self.dark_mode:
            # Draw white background first
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            
            # Render PDF on top of white
            page.render(cr)
            
            # Invert colors for dark mode using Cairo DIFFERENCE
            cr.set_operator(cairo.Operator.DIFFERENCE)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        else:
            # Draw white background
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            # Render PDF normally
            page.render(cr)

    def next_page(self):
        if self.document and self.current_page_idx < self.document.get_n_pages() - 1:
            self.current_page_idx += 1
            self.update_size()

    def prev_page(self):
        if self.document and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.update_size()

    def zoom_in(self):
        self.zoom *= 1.2
        self.update_size()

    def zoom_out(self):
        self.zoom /= 1.2
        self.update_size()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.drawing_area.queue_draw()


class PdfDirectViewer(Gtk.ApplicationWindow):
    def __init__(self, app, pdf_path=None):
        super().__init__(application=app, title="PDF Direct Viewer")
        self.set_default_size(1024, 768)

        # 1. Design the Interface - Native GTK HeaderBar
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)
        self.header_bar.set_title("PDF Direct Viewer")
        self.set_titlebar(self.header_bar)

        # Open Button
        open_button = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        open_button.set_tooltip_text("Open PDF Document in New Tab")
        open_button.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_button)

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

        # 2. Setup Notebook (Tabs)
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self.on_tab_switched)
        self.add(self.notebook)

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

    def get_current_tab(self):
        page_num = self.notebook.get_current_page()
        if page_num >= 0:
            return self.notebook.get_nth_page(page_num)
        return None

    def add_tab(self, pdf_path):
        tab = PdfTab(pdf_path)
        
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        title = os.path.basename(pdf_path) if pdf_path else "New Document"
        
        tab_label = Gtk.Label(label=title)
        tab_label.set_max_width_chars(25)
        tab_label.set_ellipsize(Pango.EllipsizeMode.END)
        tab_box.pack_start(tab_label, True, True, 0)

        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", self.on_close_tab, tab)
        tab_box.pack_end(close_btn, False, False, 0)
        
        tab_box.show_all()
        tab.show_all()
        
        page_num = self.notebook.append_page(tab, tab_box)
        self.notebook.set_current_page(page_num)

    def on_close_tab(self, button, tab):
        page_num = self.notebook.page_num(tab)
        if page_num >= 0:
            self.notebook.remove_page(page_num)
            tab.destroy()
        if self.notebook.get_n_pages() == 0:
            self.close()

    def on_tab_switched(self, notebook, page, page_num):
        tab = notebook.get_nth_page(page_num)
        if tab and tab.pdf_path:
            self.header_bar.set_subtitle(os.path.basename(tab.pdf_path))
        else:
            self.header_bar.set_subtitle("No file loaded")

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

    def on_zoom_in(self, widget):
        tab = self.get_current_tab()
        if tab: tab.zoom_in()

    def on_zoom_out(self, widget):
        tab = self.get_current_tab()
        if tab: tab.zoom_out()

    def on_prev_page(self, widget):
        tab = self.get_current_tab()
        if tab: tab.prev_page()

    def on_next_page(self, widget):
        tab = self.get_current_tab()
        if tab: tab.next_page()

    def on_theme_toggle(self, widget):
        tab = self.get_current_tab()
        if tab: tab.toggle_theme()

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
