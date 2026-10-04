# Totally Enfused

A Mac app for exposure fusion. Drop in a bracketed set and it aligns the frames with `align_image_stack` and blends them with `enfuse`, the Hugin tools behind most free HDR workflows, without going near a terminal.

- **RAW in, 16-bit TIFF out.** Fujifilm, Canon, Nikon, Sony, Olympus, Panasonic, Pentax, Samsung and DNG files, including JPEG XL-compressed DNGs from Lightroom. The result keeps the camera and lens metadata of the frame nearest 0 EV.
- **Batch mode.** Drop a folder and the app finds every bracket in it, using capture time and exposure, then blends them one after another.
- **Works with your editor.** Open With, drag and drop, a Finder Quick Action, and a `totallyenfused://blend?files=…` URL scheme for scripts and other apps.
- **Self-contained.** Native Apple Silicon builds of `enfuse` and `align_image_stack` ship inside the app, so Hugin doesn't need to be installed.

Requires an Apple Silicon Mac. The app runs on macOS 26, and the bundled tools need macOS 27; on 26 the app uses an installed copy of [Hugin](https://hugin.sourceforge.io/) instead. [exiftool](https://exiftool.org/) is optional: without it, blends still work but lose their camera metadata, and batch mode groups frames by file date.

## How it's built

A Python backend runs the pipeline (RAW conversion with rawpy, or Core Image for files LibRaw can't read, then alignment, blending and metadata). The interface is Svelte, displayed in a native window by [pywebview](https://pywebview.flowrl.com/), and PyInstaller packages it all as a `.app`.

## Building from source

```bash
# Python backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pyinstaller pytest

# Frontend
cd frontend && npm install && npm run build && cd ..

# Run from source
./launch.sh
```

The bundled tools are built from the official source releases, since nobody publishes Apple Silicon builds. Install the Homebrew dependencies listed at the top of `build/build_hugin_tools.sh`, then run:

```bash
bash build/build_hugin_tools.sh   # about a minute; output goes to vendor/bundle
```

When run from source, the app uses `vendor/bundle` if it exists and an installed Hugin otherwise.

A signed, notarised release needs an Apple Developer ID. Create `build/release.env` with `SIGN_IDENTITY` and `NOTARY_PROFILE`, store the notarisation password with `xcrun notarytool store-credentials`, then run `bash build/release.sh`. The result is `dist/TotallyEnfused.dmg`.

Tests: `.venv/bin/python -m pytest tests`. The RAW and real-folder tests run only when `TE_SAMPLE_RAW`, `TE_SAMPLE_JXL_DNG` and `TE_SAMPLE_BRACKET_DIR` point at sample files.

## Licence

The Totally Enfused source is MIT-licensed; see [LICENSE](LICENSE). The bundled `enfuse` (enblend-enfuse 4.2) and `align_image_stack` (Hugin 2025.0.1) are GPL programs that the app runs as separate processes. [THIRD_PARTY_NOTICES.md](build/THIRD_PARTY_NOTICES.md) lists their sources, the build-only changes made to them, and the licences of every bundled library. This repository, together with `build/build_hugin_tools.sh`, is how to get their corresponding source.
