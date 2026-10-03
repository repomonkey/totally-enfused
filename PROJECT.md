# Totally Enfused

A cross-platform GUI for Enfuse and align_image_stack, because CLI tools deserve better than being typed into a terminal like it's 1997.

**License:** MIT

---

## What It Does

Totally Enfused wraps two Hugin command-line tools into a single, modern desktop application:

1. **align_image_stack** -- aligns a set of input images (correcting for handheld camera movement, tripod shifts, etc.)
2. **Enfuse** -- blends the aligned images using exposure fusion (no HDR tone mapping, no clown vomit)

The app handles the full pipeline: drop your bracketed exposures in, get a beautifully blended result out. No terminal. No memorising flags. No crying.

---

## Architecture

### Backend: Python

Python handles all the heavy lifting:

- Subprocess management for `align_image_stack` and `enfuse`
- File I/O (temp directories, image validation, output management)
- Settings/preferences persistence
- EXIF metadata reading (to auto-detect bracketed sequences)
- Image preview generation (thumbnails, before/after)

### Frontend: Svelte + Vite

Svelte was chosen over React for this project for good reasons:

- **Smaller bundle size** -- matters for a desktop app where you're shipping the frontend
- **Less boilerplate** -- no useState/useEffect ceremony, reactive by default
- **Faster rendering** -- compiles to vanilla JS, no virtual DOM overhead
- **Simpler state management** -- built-in stores, no Redux/Zustand rabbit holes
- **Better for small-to-mid complexity UIs** -- this isn't a SaaS dashboard with 400 components

The frontend communicates with the Python backend via a local WebSocket or HTTP API.

### Desktop Shell: pywebview

[pywebview](https://pywebview.flowrl.com/) provides the native window wrapper:

- MIT-licensed (compatible with our MIT release)
- Lightweight (not shipping all of Chromium like Electron)
- Uses the OS-native webview (WebKit on macOS, WebView2 on Windows, WebKitGTK on Linux)
- Python-native API for bridging JS <-> Python
- Window management, file dialogs, system tray support

### Packaging: PyInstaller

Builds standalone executables for each platform. Single-file or single-folder distribution, no Python installation required for end users.

---

## Core Features

### Image Input
- **Drag and drop** -- primary input method, drop a set of bracketed exposures onto the app
- Auto-detection of bracketed sequences from EXIF data (exposure values)
- Support for common RAW formats (via rawpy/LibRaw) and standard formats (JPEG, TIFF, PNG)
- Thumbnail preview strip showing all loaded images with EV overlay

### Alignment (align_image_stack)
- Toggle alignment on/off (skip if images are already aligned, e.g. tripod shots)
- Alignment mode selection:
  - **Translation only** -- locked-off tripod, just minor shifts
  - **Translation + rotation** -- handheld or slight tripod movement
  - **Full homography** -- significant perspective differences
- Control point grid density (fine/medium/coarse)
- Crop or fill options for aligned output
- Visual feedback showing alignment correction applied

### Fusion (Enfuse)
- **Exposure weight** (mu/sigma) -- how much to favour well-exposed pixels
- **Saturation weight** -- preference for saturated colours
- **Contrast weight** -- preference for local contrast
- **Hard/soft mask toggle**
- **Blend levels** (pyramid depth)
- Preset system:
  - "Natural" -- balanced weights for landscape/general use
  - "Real Estate" -- optimised for interior/architecture brackets
  - "Macro" -- focus stacking-friendly settings
  - Custom presets (save/load)
- Live preview of blend result (downscaled for speed)
- Before/after comparison slider

### Output
- Format selection: TIFF (16-bit), JPEG, PNG
- Quality/compression controls
- Output naming (template system: `{original}_enfused.{ext}`)
- Output directory selection (default: same as input)
- Option to embed original EXIF from middle exposure

---

## UI Design Direction

### Aesthetic: Dark, Photographic, Functional

This is a tool for photographers. The UI should feel like a digital darkroom, not a startup landing page.

- **Dark theme** as default (with light theme option), muted background so images aren't competing with the chrome
- **Monochrome UI** with a single accent colour for active states and progress indicators
- Generous spacing, nothing cramped
- Typography: clean sans-serif, good weight hierarchy, no decorative nonsense
- Image previews are the hero -- the UI exists to serve the images, not the other way around
- Subtle transitions, nothing that bounces or swooshes

### Layout

```
+------------------------------------------------------------------+
|  [Logo/Title]                              [Settings] [About]     |
+------------------------------------------------------------------+
|                                                                    |
|  +--------------------------------------------+  +-----------+   |
|  |                                            |  |           |   |
|  |           IMAGE PREVIEW AREA               |  |  CONTROLS |   |
|  |        (before/after comparison)            |  |  PANEL    |   |
|  |                                            |  |           |   |
|  |                                            |  |  Align    |   |
|  |                                            |  |  --------  |   |
|  |                                            |  |  Fusion   |   |
|  |                                            |  |  --------  |   |
|  |                                            |  |  Output   |   |
|  |                                            |  |  --------  |   |
|  +--------------------------------------------+  |  Presets  |   |
|                                                   |           |   |
|  +--------------------------------------------+  +-----------+   |
|  | [img1] [img2] [img3] [img4]  DROP ZONE     |                   |
|  +--------------------------------------------+                   |
|                                                                    |
|  [===================] Processing...  67%                          |
+------------------------------------------------------------------+
```

- **Left/centre:** large image preview with before/after slider
- **Right:** collapsible control panel with accordion sections (Alignment, Fusion, Output, Presets)
- **Bottom strip:** thumbnail rail of loaded images + drag-and-drop zone
- **Footer:** progress bar and status during processing

---

## Project Structure

```
totally-enfused/
+-- backend/
|   +-- main.py              # Entry point, pywebview window setup
|   +-- api.py               # JS-exposed API (pywebview bridge)
|   +-- enfuse_runner.py     # Subprocess wrapper for enfuse
|   +-- align_runner.py      # Subprocess wrapper for align_image_stack
|   +-- image_utils.py       # Thumbnails, EXIF, format detection
|   +-- settings.py          # User preferences persistence
|   +-- presets.py            # Fusion preset management
|   +-- __init__.py
+-- frontend/
|   +-- src/
|   |   +-- App.svelte        # Root component
|   |   +-- lib/
|   |   |   +-- ImagePreview.svelte
|   |   |   +-- ControlPanel.svelte
|   |   |   +-- ThumbnailStrip.svelte
|   |   |   +-- DropZone.svelte
|   |   |   +-- ComparisonSlider.svelte
|   |   |   +-- ProgressBar.svelte
|   |   |   +-- PresetManager.svelte
|   |   +-- stores/
|   |   |   +-- images.js      # Image state management
|   |   |   +-- settings.js    # App settings store
|   |   |   +-- process.js     # Processing state
|   |   +-- styles/
|   |       +-- global.css     # CSS variables, dark/light themes
|   |       +-- tokens.css     # Design tokens
|   +-- index.html
|   +-- vite.config.js
|   +-- package.json
+-- assets/
|   +-- icon.png
|   +-- icon.ico
|   +-- icon.icns
+-- tests/
|   +-- test_enfuse_runner.py
|   +-- test_align_runner.py
|   +-- test_image_utils.py
+-- build/
|   +-- build_mac.spec         # PyInstaller spec for macOS
|   +-- build_win.spec         # PyInstaller spec for Windows
|   +-- build_linux.spec       # PyInstaller spec for Linux
+-- requirements.txt
+-- README.md
+-- LICENSE
+-- PROJECT.md                 # This file
```

---

## Dependencies

### Python
- `pywebview` -- native window shell
- `Pillow` -- image handling, thumbnails
- `rawpy` -- RAW file support (wraps LibRaw)
- `exifread` or `piexif` -- EXIF metadata extraction
- `websockets` (optional, if using WebSocket comms instead of pywebview bridge)

### System (must be installed by user or bundled)
- `enfuse` -- the actual blending engine (part of Hugin/Enblend-Enfuse)
- `align_image_stack` -- image alignment (part of Hugin)

### Frontend (npm)
- `svelte` + `vite` -- build toolchain
- `@sveltejs/vite-plugin-svelte`

### Build
- `pyinstaller` -- packaging

---

## Platform Notes

### macOS
- pywebview uses WebKit (WKWebView)
- Hugin tools installable via Homebrew: `brew install hugin`
- App bundle (.app) via PyInstaller

### Windows
- pywebview uses WebView2 (Edge/Chromium, pre-installed on Windows 10+)
- Hugin tools available via installer or portable zip
- .exe via PyInstaller
- May need to bundle WebView2 bootstrapper for older Windows versions

### Linux
- pywebview uses WebKitGTK
- Hugin tools available via apt/dnf/pacman: `sudo apt install enfuse hugin-tools`
- AppImage or .deb via PyInstaller + fpm

---

## Development Workflow

1. **Frontend dev:** `cd frontend && npm run dev` (Vite dev server with hot reload)
2. **Backend dev:** `cd backend && python main.py --dev` (loads frontend from Vite dev server URL instead of built files)
3. **Production build:** `cd frontend && npm run build` then `pyinstaller build/build_{platform}.spec`

---

## Future Considerations (Not MVP)

- Batch processing (drop multiple bracket sets)
- Focus stacking mode (using align_image_stack + enfuse with contrast-only weights)
- Histogram display for input/output images
- GPU-accelerated preview rendering
- Auto-update mechanism
- Plugin system for custom post-processing (curves, levels)
- Integration with external editors (open result in Lightroom/Affinity/etc.)

---

## Why "Totally Enfused"?

Because "Enfuse GUI" was boring, "Blend-o-Matic" was taken in my head, and every good app name should make you slightly unsure whether it's a pun or a typo.
