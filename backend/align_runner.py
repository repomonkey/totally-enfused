import subprocess
import shutil
import tempfile
import os
from pathlib import Path
from typing import Callable

# Extra optimisation flags per mode.
# -m  = optimise FoV  -d = radial distortion  -i = image centre shift
ALIGN_MODE_ARGS = {
    "translation": [],
    "translation_rotation": [],
    "homography": ["-m", "-d", "-i"],
}


def find_align_image_stack() -> str | None:
    candidates = [
        "align_image_stack",
        "/opt/homebrew/bin/align_image_stack",
        "/usr/local/bin/align_image_stack",
        "/usr/bin/align_image_stack",
        "/Applications/Hugin/tools_mac/align_image_stack",
        "/Applications/Hugin/HuginTools/align_image_stack",
        "/Applications/Hugin/Hugin.app/Contents/MacOS/align_image_stack",
        "/Applications/Hugin/PTBatcherGUI.app/Contents/MacOS/align_image_stack",
    ]
    for c in candidates:
        found = _find_binary(c)
        if found:
            return found
    return None


def _find_binary(name: str) -> str | None:
    """Locate a binary by absolute path or name — works inside PyInstaller bundles."""
    if os.path.isabs(name):
        return name if os.path.isfile(name) and os.access(name, os.X_OK) else None
    return shutil.which(name)


def align(
    input_paths: list[str],
    output_dir: str,
    mode: str = "translation_rotation",
    grid_points: int = 8,
    crop: bool = True,
    progress_callback: Callable[[int, str], None] | None = None,
) -> list[str]:
    """
    Align images using align_image_stack.
    Returns list of aligned output file paths.
    """
    binary = find_align_image_stack()
    if not binary:
        raise RuntimeError(
            "align_image_stack not found. Install Hugin via:\n"
            "  brew install hugin\n"
            "or download from https://hugin.sourceforge.io/"
        )

    ext = Path(input_paths[0]).suffix.lower()
    if ext in {".cr2", ".cr3", ".nef", ".arw", ".orf", ".raf", ".dng", ".rw2"}:
        out_ext = ".tif"
    else:
        out_ext = ext if ext in {".tif", ".tiff"} else ".tif"

    output_prefix = os.path.join(output_dir, "aligned_")
    cmd = [binary]
    cmd += ALIGN_MODE_ARGS.get(mode, [])
    cmd += ["-g", str(grid_points)]   # grid divisions (default 5)
    cmd += ["-c", "8"]                # control points per grid cell
    if crop:
        cmd += ["-C"]
    cmd += ["--use-given-order"]
    cmd += ["-a", output_prefix]
    cmd += input_paths

    if progress_callback:
        progress_callback(0, "Starting alignment...")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_lines = []
    for line in process.stdout:
        output_lines.append(line.strip())
        if progress_callback:
            progress_callback(-1, line.strip())

    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"align_image_stack failed:\n" + "\n".join(output_lines[-10:]))

    # Collect output files
    n = len(input_paths)
    aligned = []
    for i in range(n):
        candidate = f"{output_prefix}{i:04d}{out_ext}"
        if os.path.exists(candidate):
            aligned.append(candidate)

    if not aligned:
        raise RuntimeError("align_image_stack produced no output files")

    if progress_callback:
        progress_callback(100, f"Aligned {len(aligned)} images")

    return aligned
