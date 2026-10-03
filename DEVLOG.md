# Totally Enfused — Development Log

## What It Is

A native macOS desktop app that wraps two Hugin CLI tools — `enfuse` and `align_image_stack` — into a proper GUI. Drop bracketed exposures in, get a blended result out. No terminal. No flags. No grief.

The stack: Python backend (pywebview bridge + subprocess runners) with a Svelte 5 + Vite frontend, packaged as a notarized macOS .app via PyInstaller.

---

## What Works

### Core pipeline
- **RAW support** — Fujifilm RAF, Canon CR2/CR3, Nikon NEF, Sony ARW, Olympus ORF, DNG, RW2, PEF, SRW. rawpy decodes to 16-bit sRGB TIFF before passing to Hugin. One brightness factor (LibRaw's auto-brighten, measured on the frame nearest 0 EV) is applied to every frame, so the bracket spread survives conversion.
- **Metadata** — EXIF and XMP are copied from the frame nearest 0 EV onto the output with exiftool, so editors see camera, lens and capture data. RAW-sourced outputs get an embedded sRGB profile. EV is read from RAW files through exiftool.
- **Alignment** — three modes (translation, translation + rotation, full homography). 8×8 control point grid. Auto-crop. Wraps `align_image_stack` found at `/Applications/Hugin/tools_mac/align_image_stack`.
- **Fusion** — exposure, saturation, and contrast weights; hard mask toggle; pyramid levels. Wraps `enfuse`. Parses progress output to drive the progress bar.
- **Output** — TIFF (LZW), JPEG (quality 85), PNG. Output to same directory as input or user-chosen folder.

### UI
- Before/after comparison slider with the first input image on the left and the blend result on the right.
- Thumbnail strip with EV badge on each image. Click to select preview.
- Collapsible right panel: Presets, Alignment, Fusion, Output sections.
- Tool detection warning if enfuse/align_image_stack can't be found.
- "Show in Finder" on the result.
- Settings persistence (window size saved/restored across sessions).

### macOS integration
- **Signed and notarized** — passes Gatekeeper (`spctl --assess` clean). Apple Developer ID: Andrew Hutchinson (PXUGHCDN9B).
- **Open With / double-click / other apps** — handled by `application:openURLs:`, added to pywebview's app delegate with a PyObjC category. Works at launch and while the app is running, for one file or many.
- **URL scheme** — `totallyenfused://blend?files=/path/1.raf,/path/2.raf` arrives through the same delegate method.
- **Drag and drop** — drop files anywhere in the window. Paths come from pywebview's native drop hook (`pywebviewFullPath`), not the browser File API.
- **DMG** — `dist/TotallyEnfused.dmg`, signed, drag-to-Applications layout with icon.
- **Finder Quick Action** — `build/install_quick_action.sh` installs a right-click service that builds the URL and fires the app. Run once after installation.

---

## Fixed (October 2026)

### "Open With" error

"Totally Enfused cannot open files in the 'Image' format" came from NSDocumentController. pywebview's `AppDelegate` (in `webview/platforms/cocoa.py`) implements no file-open method, so NSApplication fell back to the document system, which has no document class for us. Registering Apple Event handlers fought that fallback and lost. The fix adds `application:openURLs:` to pywebview's delegate class through `objc.Category` in `backend/file_handler.py`.

A second bug sat underneath it. Open events arrive on the main thread, and pywebview's `evaluate_js` blocks until the main thread runs the script, so emitting `files:open` inline deadlocked the app after the first open. Emits now go through a worker thread.

### Drag and drop

WKWebView's `File` objects carry no filesystem path, so the old drop zone opened a file dialog instead. pywebview records the paths natively when a drop listener is registered through its DOM API (`window.dom.document.events.drop`), and `register_drop_handler()` uses that.

---

## Known Minor Issues

- **Output filename accumulates `_openWith`** if files opened via the URL scheme are re-opened via the URL scheme again — the `_openWith` suffix comes from DxO's export naming and gets baked into the output name. Cosmetic; doesn't affect the result.
- **Gatekeeper shows "rejected" during the release build's verify step** — this is expected; `spctl --assess` fails before the notarization ticket is stapled. The build script continues correctly and staples before creating the DMG.

---

## Build & Release

```bash
# Full notarized release (run from project root)
bash build/release.sh
# Output: dist/TotallyEnfused.dmg

# Install Finder Quick Action (run once after installing the .app)
bash build/install_quick_action.sh
```

Credentials live in `build/release.env` (gitignored): Apple ID, Team ID, app-specific password, signing identity. Moving them into the keychain with `xcrun notarytool store-credentials` would be safer still.

Tests: `TE_SAMPLE_RAW=/path/to/file.raf .venv/bin/python -m pytest tests -q`

---

## Stack Versions

| Component | Version |
|---|---|
| Python | 3.14.3 |
| pywebview | 6.2.1 |
| PyInstaller | 6.20.0 |
| Svelte | 5.x |
| Vite | 6.x |
| rawpy | latest |
| Pillow | latest |

Hugin tools: `/Applications/Hugin/tools_mac/` (symlinks to the actual binaries inside the Hugin .app bundles). x86_64 binaries running under Rosetta 2 on Apple Silicon — works fine.
