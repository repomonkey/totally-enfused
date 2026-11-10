# Running Totally Enfused on an Intel Mac

The download on the Releases page is for Apple Silicon Macs on macOS 27, which doesn't run on Intel hardware (Apple's last release for Intel Macs is macOS 26). The app's code isn't tied to Apple Silicon, though, so you can run it on an Intel Mac by building it yourself. It takes about 15 minutes, and none of the steps needs Homebrew.

> **Status:** these steps have not yet been tested on real Intel hardware. If you try them, please open an issue to say how it went, including your Mac and macOS version.

## What you need

- An Intel Mac running macOS 12 Monterey or later.
- **Apple's command-line tools**, which provide `git`. Run `xcode-select --install` in Terminal, or skip this if `git --version` already works.
- **Python 3.13** from [python.org](https://www.python.org/downloads/macos/). Use 3.13 or 3.12, not 3.14: the RAW library (rawpy) stopped publishing Intel builds after version 0.25.1, which supports Python up to 3.13.
- **Node.js 20 or later** from [nodejs.org](https://nodejs.org/), for building the interface. The LTS installer is fine.
- **Hugin 2019.2.0** from [hugin.sourceforge.io](https://hugin.sourceforge.io/download/). This is Hugin's official Mac build, and it's an Intel build, so it suits these Macs. Drag the `Hugin` folder into Applications. Totally Enfused uses its `enfuse` and `align_image_stack`.
- **ExifTool** (optional, recommended): the macOS package from [exiftool.org](https://exiftool.org/). Without it, blends still work, but results lose their camera and lens metadata, and batch mode groups frames by file date only.

## Run it from source

```bash
git clone https://github.com/repomonkey/totally-enfused.git
cd totally-enfused

python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt "rawpy==0.25.1" pyinstaller

cd frontend && npm install && npm run build && cd ..

./launch.sh
```

The `rawpy==0.25.1` pin is the important part. Without it, pip picks the newest rawpy, which has no Intel build, and tries to compile it from source.

## Build a proper app

Running from source works, but a `.app` in Applications also gets you **Open With** from Finder and photo editors, and the `totallyenfused://` URL scheme. From the project folder:

```bash
TE_MIN_MACOS=$(sw_vers -productVersion) .venv/bin/pyinstaller build/build_mac.spec \
  --distpath dist --workpath build/work --noconfirm
```

Then drag `dist/Totally Enfused.app` into Applications. `TE_MIN_MACOS` marks the app as compatible with your version of macOS; without it, the app claims to need macOS 26 and won't open on older systems.

The app isn't signed with a Developer ID, but macOS opens it without complaint because you built it on the same Mac. Don't use `build/release.sh`: it's the signed, notarised release process for Apple Silicon and needs a Developer ID and the Apple Silicon tool builds.

## The first blend

The first time Totally Enfused runs Hugin's tools, macOS may say it can't verify `enfuse` or `PTBatcherGUI`, because the 2019 Hugin download predates Apple's notarisation requirement. Open **System Settings → Privacy & Security**, scroll to the message about the blocked program and click **Open Anyway**, then run the blend again. You may need to do this once for each tool.

## Differences from the Apple Silicon release

- Alignment and blending use Hugin 2019.2.0's tools rather than the 2025 builds bundled in the release. The results are the same; in a side-by-side test the two versions' output differed by less than 0.01% on average.
- JPEG XL–compressed DNGs (Lightroom's default for some DNG exports) decode through macOS's own RAW engine. JPEG XL support arrived in macOS 14 Sonoma, so on older systems those files may not open. Every other RAW format goes through rawpy and works on any supported macOS.

## Troubleshooting

- **pip prints a long compiler error mentioning LibRaw.** pip is building rawpy from source. Check that you used `python3.13` (or 3.12) and included `"rawpy==0.25.1"`.
- **The app says enfuse or align_image_stack can't be found.** It looks for Hugin in `/Applications/Hugin/`. Make sure the whole `Hugin` folder from the download is there, not just `Hugin.app`.
- **`npm: command not found`.** Install Node.js, then open a new Terminal window.
