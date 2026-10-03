# Totally Enfused — Development Log

## What It Is

A native macOS desktop app that wraps two Hugin CLI tools — `enfuse` and `align_image_stack` — into a proper GUI. Drop bracketed exposures in, get a blended result out. No terminal. No flags. No grief.

The stack: Python backend (pywebview bridge + subprocess runners) with a Svelte 5 + Vite frontend, packaged as a notarized macOS .app via PyInstaller.

---

## What Works

### Core pipeline
- **RAW support** — Fujifilm RAF, Canon CR2/CR3, Nikon NEF, Sony ARW, Olympus ORF, DNG, RW2, PEF, SRW. rawpy decodes to 8-bit TIFF before passing to Hugin.
- **Alignment** — three modes (translation, translation + rotation, full homography). 8×8 control point grid. Auto-crop. Wraps `align_image_stack` found at `/Applications/Hugin/tools_mac/align_image_stack`.
- **Fusion** — exposure, saturation, and contrast weights; hard mask toggle; pyramid levels. Wraps `enfuse`. Parses progress output to drive the progress bar.
- **Output** — TIFF (LZW), JPEG (quality 85), PNG. Output to same directory as input or user-chosen folder.

### UI
- Before/after comparison slider with the first input image on the left and the blend result on the right.
- Thumbnail strip with EV badge on each image. Click to select preview.
- Collapsible right panel: Presets, Alignment, Fusion, Output sections.
- Tool detection warning if enfuse/align_image_stack can't be found (with 1.5s retry for cold-start race).
- "Show in Finder" on the result.
- Settings persistence (window size saved/restored across sessions).

### macOS integration
- **Signed and notarized** — passes Gatekeeper (`spctl --assess` clean). Apple Developer ID: Andrew Hutchinson (PXUGHCDN9B).
- **URL scheme** — `totallyenfused://blend?files=/path/1.raf,/path/2.raf` works from any app. Useful for calling from scripts or photo editors that support custom URL schemes.
- **DMG** — `dist/TotallyEnfused.dmg`, signed, drag-to-Applications layout with icon.
- **Finder Quick Action** — `build/install_quick_action.sh` installs a right-click service that builds the URL and fires the app. Run once after installation.

---

## What Doesn't Work

### "Open With" from Finder / DxO PhotoLab (ongoing)

The macOS error "Totally Enfused cannot open files in the 'Image' format" still appears when opening files via right-click → Open With or from DxO PhotoLab's export dialog.

**Root cause (understood, not fully fixed):**  
When macOS dispatches an `odoc` (open document) Apple Event to a running Cocoa app, it goes through NSApplication's default handler, which routes to NSDocumentController. Because we're not an NSDocument-based app, NSDocumentController fails with that error. Our NSAppleEventManager handler should override this, but pywebview's `webview.start()` re-initialises NSApplication's Apple Event handlers, stomping ours.

**What's been tried:**
1. Registering with NSAppleEventManager before `webview.start()` — overridden by NSApplication init.
2. Re-registering from the `window.events.loaded` callback — should work in theory, runs on the right thread, but the error persists. Either pywebview re-installs the handler after `on_loaded`, or NSDocumentController is somehow involved before our re-registration takes effect.
3. Setting an NSApplication delegate with `application:openFiles:` — pywebview sets its own delegate, ours doesn't stick.
4. Disabling `argv_emulation=True` in the PyInstaller spec — removed the Carbon-level startup handler conflict, but the runtime issue remains.

**Workaround that works:** Use the URL scheme. `totallyenfused://blend?files=...` arrives via `kAEGetURL`, which is a different event class that NSApplication doesn't intercept. The URL handler works reliably for both single and multiple files. The Finder Quick Action uses this path.

**Next angle to try:** Subclass NSApplication itself (via PyObjC) and override `sendEvent:` or install the Apple Event handler at the Carbon/AEManager level rather than through NSAppleEventManager's Objective-C bridge.

---

### Drag and drop opens a file dialog instead of accepting the drop

When files are dragged from Finder onto the app window, the DropZone component falls back to opening a native file picker dialog instead of reading the dropped paths directly.

**Cause:** `file.path` is an Electron-only property. In pywebview's WKWebView, `DataTransfer` files have no `.path` — the standard Web File API gives you a sandboxed `File` object with no filesystem path. Detecting that `.path` is undefined and falling back to the dialog was a pragmatic fix but it's not drag and drop.

**Fix needed:** pywebview exposes a `webview.windows[0].create_file_dialog()` but that's not useful here. The right approach is to handle the drop at the WKWebView/AppKit level — intercept `draggingEntered:` and `performDragOperation:` in a custom NSView subclass, extract the file paths from `NSPasteboard`, and forward them to Python via the existing `_send()` mechanism. This requires a small PyObjC shim attached to pywebview's content view.

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

Credentials live in `build/release.sh` — Apple ID, Team ID, app-specific password, signing identity.

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
