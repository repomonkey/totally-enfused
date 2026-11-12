# Totally Enfused

A Mac app for exposure fusion. Drop in a bracketed set and it aligns the frames with `align_image_stack` and blends them with `enfuse`, the Hugin tools behind most free HDR workflows, without going near a terminal.

- **RAW in, 16-bit TIFF out.** Fujifilm, Canon, Nikon, Sony, Olympus, Panasonic, Pentax, Samsung and DNG files, including JPEG XL-compressed DNGs from Lightroom. The result keeps the camera and lens metadata of the frame nearest 0 EV.
- **Sharp moving water.** Optional motion handling takes waves, clouds, leaves and birds from one reference frame, so they stay crisp instead of blending into a ghostly blur.
- **Separate sky and foreground.** Drag a line across the preview and the sky gets its own blend, weighted towards the darker frames for deeper sunset colour, while the foreground is lifted as usual. The two meet in a feathered transition, like a graduated filter.
- **Batch mode.** Drop a folder and the app finds every bracket in it, using capture time and exposure, then blends them one after another.
- **Works with your editor.** Open With, drag and drop, a Finder Quick Action, and a `totallyenfused://blend?files=…` URL scheme for scripts and other apps.
- **Self-contained.** Native Apple Silicon builds of `enfuse` and `align_image_stack` ship inside the app, along with ExifTool, so there's nothing else to install.

## Download

Get the latest `.dmg` from [Releases](https://github.com/repomonkey/totally-enfused/releases/latest), open it and drag Totally Enfused to Applications. The app is signed and notarised by Apple, so it opens without security warnings.

Requires an Apple Silicon Mac running macOS 27 or later. Everything it needs is inside the app, including `enfuse`, `align_image_stack` and [ExifTool](https://exiftool.org/). The app also launches on macOS 26, where the bundled Hugin tools can't load, so you would need [Hugin](https://hugin.sourceforge.io/) installed separately.

**Intel Macs:** there's no download, because macOS 27 doesn't run on Intel hardware, but you can build and run the app yourself. See [INTEL.md](INTEL.md).

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
bash build/build_hugin_tools.sh             # about a minute; output goes to vendor/bundle
.venv/bin/python build/bundle_exiftool.py vendor/bundle   # needs: brew install exiftool
```

When run from source, the app uses `vendor/bundle` if it exists and an installed Hugin otherwise.

A signed, notarised release needs an Apple Developer ID. Create `build/release.env` with `SIGN_IDENTITY` and `NOTARY_PROFILE`, store the notarisation password with `xcrun notarytool store-credentials`, then run `bash build/release.sh`. The result is `dist/TotallyEnfused-<version>.dmg`.

Tests: `.venv/bin/python -m pytest tests`. The RAW and real-folder tests run only when `TE_SAMPLE_RAW`, `TE_SAMPLE_JXL_DNG` and `TE_SAMPLE_BRACKET_DIR` point at sample files.

## Licence

The Totally Enfused source is MIT-licensed; see [LICENSE](LICENSE). The bundled `enfuse` (enblend-enfuse 4.2) and `align_image_stack` (Hugin 2025.0.1) are GPL programs, and ExifTool is under Perl's licence terms; the app runs all three as separate processes. [THIRD_PARTY_NOTICES.md](build/THIRD_PARTY_NOTICES.md) lists their sources, the build-only changes made to them, and the licences of every bundled library. This repository, together with `build/build_hugin_tools.sh`, is how to get their corresponding source.
