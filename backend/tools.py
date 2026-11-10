"""
Locate enfuse, align_image_stack and exiftool.

Search order:
  1. Bundled with the app: Totally Enfused.app/Contents/Helpers/
  2. Development build:    <repo>/vendor/bundle/Helpers/  (build/build_hugin_tools.sh)
  3. Installed copies:     PATH, Homebrew/MacPorts, Hugin.app
ExifTool follows the same order from Contents/Resources/exiftool (see exiftool_cmd).

Each candidate is launched once and only used if it starts: the bundled
build targets macOS 27, so on older systems dyld refuses to load it and the
search falls through to an installed Hugin.
"""
import functools
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SYSTEM_CANDIDATES = {
    "enfuse": [
        "/opt/homebrew/bin/enfuse",
        "/usr/local/bin/enfuse",
        "/opt/local/bin/enfuse",
        "/usr/bin/enfuse",
        "/Applications/Hugin/tools_mac/enfuse",
        "/Applications/Hugin/HuginTools/enfuse",
        "/Applications/Hugin/PTBatcherGUI.app/Contents/MacOS/enfuse",
        "/Applications/Hugin/HuginStitchProject.app/Contents/MacOS/enfuse",
    ],
    "align_image_stack": [
        "/opt/homebrew/bin/align_image_stack",
        "/usr/local/bin/align_image_stack",
        "/opt/local/bin/align_image_stack",
        "/usr/bin/align_image_stack",
        "/Applications/Hugin/tools_mac/align_image_stack",
        "/Applications/Hugin/HuginTools/align_image_stack",
        "/Applications/Hugin/Hugin.app/Contents/MacOS/align_image_stack",
        "/Applications/Hugin/PTBatcherGUI.app/Contents/MacOS/align_image_stack",
    ],
}


def _bundled_dirs() -> list[Path]:
    dirs = []
    if getattr(sys, "frozen", False):
        # .../Totally Enfused.app/Contents/MacOS/Totally Enfused -> Contents/Helpers
        dirs.append(Path(sys.executable).resolve().parent.parent / "Helpers")
    dirs.append(ROOT / "vendor" / "bundle" / "Helpers")
    return dirs


def _runs(path: str) -> bool:
    """True if the binary starts; a dyld load failure kills it with a signal."""
    try:
        proc = subprocess.run([path, "--help"], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode >= 0


@functools.cache
def find_tool(name: str) -> str | None:
    candidates = [str(d / name) for d in _bundled_dirs()]
    if which := shutil.which(name):
        candidates.append(which)
    candidates += SYSTEM_CANDIDATES.get(name, [])
    for c in dict.fromkeys(candidates):
        if os.path.isfile(c) and os.access(c, os.X_OK) and _runs(c):
            return c
    return None


def is_bundled(path: str | None) -> bool:
    return bool(path) and any(Path(path).parent == d for d in _bundled_dirs())


def _bundled_exiftool_dirs() -> list[Path]:
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).resolve().parent.parent / "Resources" / "exiftool")
    dirs.append(ROOT / "vendor" / "bundle" / "exiftool")
    return dirs


@functools.cache
def exiftool_cmd() -> list[str] | None:
    """
    Command prefix for ExifTool. The bundled copy (build/bundle_exiftool.py) is a
    Perl script run with macOS's /usr/bin/perl; installed copies are the fallback.
    """
    candidates = []
    if os.access("/usr/bin/perl", os.X_OK):
        candidates += [["/usr/bin/perl", str(d / "exiftool")]
                       for d in _bundled_exiftool_dirs() if (d / "exiftool").is_file()]
    for p in ("/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool",
              "/opt/local/bin/exiftool", shutil.which("exiftool")):
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            candidates.append([p])
    for cmd in candidates:
        try:
            if subprocess.run(cmd + ["-ver"], capture_output=True, timeout=15).returncode == 0:
                return cmd
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None
