# PDF Direct Viewer

A high-performance, native Linux PDF reader powered by **Mozilla's PDF.js** engine — the same rendering engine used in Firefox.

Developed by **Daniel Lee**.

## ✨ Features

- **🔥 Firefox PDF Engine:** Uses Mozilla's open-source [PDF.js](https://github.com/nicbarker/pdfjs-dist) to render documents, giving you the exact same quality and feature set as Firefox's built-in PDF viewer — including full-text search, outline/bookmarks sidebar, thumbnails, zoom, and print.
- **🎨 9-Color Reader Palette:** Choose from 9 carefully curated color themes (Original, Dark, Sepia, Night Green, Ocean Blue, High Contrast, Rose, Slate, Cream) via a one-click popover in the title bar.
- **📑 Multi-Tab Interface:** Open multiple PDFs in tabs, just like a browser. Each tab runs independently.
- **📂 Drag & Drop:** Drop PDF files directly onto the window to open them in new tabs.
- **🖥️ Native Desktop Integration:** Double-click any PDF in your file manager to open it in PDF Direct Viewer.
- **🔒 Sandboxed Security:** Fully sandboxed via Flatpak. A local `127.0.0.1` HTTP micro-server securely bridges the gap between local files and the WebKit renderer — no data ever leaves your machine.

## 🛠️ Technology Stack

| Component         | Technology                                                                 |
|--------------------|---------------------------------------------------------------------------|
| Language           | Python 3                                                                  |
| GUI Toolkit        | GTK 3 (via [PyGObject](https://pygobject.readthedocs.io/))               |
| Web Engine         | [WebKit2GTK](https://webkitgtk.org/) 4.1                                 |
| PDF Rendering      | [Mozilla PDF.js](https://mozilla.github.io/pdf.js/) (Apache 2.0 License) |
| Graphics / Theming | CSS Filters injected at runtime via JavaScript                            |
| Packaging          | Flatpak (GNOME Platform 50)                                              |

## 🏗️ Build & Run (Flatpak)

```bash
# Clone the build recipe
git clone https://github.com/Daniellee0305/PDF-direct-viewer.git

# Build the Flatpak
cd PDF-direct-viewer
flatpak-builder --user --install --force-clean build-dir io.github.daniellee0305.PdfDirectViewer.yml

# Run
flatpak run io.github.daniellee0305.PdfDirectViewer
```

## 📜 Acknowledgements & Open-Source Credits

This project gratefully builds upon the following open-source projects:

| Project | License | Usage |
|---------|---------|-------|
| [Mozilla PDF.js](https://github.com/nicbarker/pdfjs-dist) | Apache 2.0 | Core PDF rendering engine |
| [pdfjs-generic](https://github.com/shivaprsd/pdfjs-generic) by Shiva Prasad | Apache 2.0 | Pre-built generic viewer distribution |
| [GTK](https://www.gtk.org/) | LGPL | Native desktop UI toolkit |
| [WebKit2GTK](https://webkitgtk.org/) | LGPL/BSD | Web content engine for rendering PDF.js |
| [PyGObject](https://pygobject.readthedocs.io/) | LGPL | Python bindings for GTK/GLib |

## ⚖️ License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
