# PDF Direct Viewer

PDF Direct Viewer is a high-performance, native PDF reader designed specifically for the Linux desktop. Developed by **Daniel Lee**, it focuses on speed, security, and a premium reading experience with built-in native Dark Mode support.

Unlike traditional wrappers, PDF Direct Viewer is built on top of the industry-standard **Poppler** rendering engine, ensuring 100% compatibility with the PDF specification while maintaining a minimal resource footprint.

## 🚀 Features

- **⚡ Native Performance:** Powered by the Poppler C++ engine (via PyGObject), providing near-instant page rendering and smooth scrolling.
- **🌙 Native Reader Mode:** A high-quality, eye-friendly Dark Mode implemented at the GPU level using Cairo, allowing for comfortable night-time reading without flickering.
- **📑 Multi-Tab Interface:** Efficiently manage multiple documents with a Firefox-inspired tabbed interface.
- **🎨 Modern GTK3 Design:** Seamlessly integrates with the GNOME desktop using a clean HeaderBar and native icons.
- **📂 Drag & Drop Support:** Open files instantly by dragging them into the application window.
- **🔒 Flatpak Security:** Fully sandboxed using Flatpak technology, ensuring your system remains secure while viewing untrusted documents.

## 🛠️ Technology Stack

- **Language:** Python 3
- **GUI Toolkit:** GTK 3 (via PyGObject)
- **Rendering Engine:** [Poppler](https://poppler.freedesktop.org/)
- **Graphics Library:** [Cairo](https://www.cairographics.org/)
- **Packaging:** Flatpak (GNOME 45+ Runtime)

## 🏗️ Installation (Local Build)

To build and run the application locally using Flatpak Builder:

```bash
# Clone the repository
git clone https://github.com/Daniellee0305/PDF-direct-viewer.git
cd PDF-direct-viewer

# Build the Flatpak
flatpak-builder --user --install --force-clean build-dir io.github.daniellee0305.PdfDirectViewer.yml

# Run the application
flatpak run io.github.daniellee0305.PdfDirectViewer
```

## 📜 Acknowledgements

This project is maintained by **Daniel Lee**. 

It stands on the shoulders of giants in the open-source community:
- **Poppler Project:** For the world-class PDF rendering engine.
- **GNOME Project:** For the GTK toolkit and the GNOME SDK.
- **Cairo:** For the advanced 2D graphics API used for our Reader Mode.

*Note: This project was originally inspired by the "doqment" browser extension, but has since been completely rewritten as a native desktop application to provide better performance and a more integrated experience.*

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
