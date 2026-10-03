import subprocess
import shutil
import os
from pathlib import Path
from typing import Callable


def find_enfuse() -> str | None:
    candidates = [
        "enfuse",
        "/opt/homebrew/bin/enfuse",
        "/usr/local/bin/enfuse",
        "/usr/bin/enfuse",
        "/Applications/Hugin/tools_mac/enfuse",
        "/Applications/Hugin/HuginTools/enfuse",
        "/Applications/Hugin/PTBatcherGUI.app/Contents/MacOS/enfuse",
        "/Applications/Hugin/HuginStitchProject.app/Contents/MacOS/enfuse",
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


def blend(
    input_paths: list[str],
    output_path: str,
    exposure_weight: float = 1.0,
    saturation_weight: float = 0.2,
    contrast_weight: float = 0.0,
    hard_mask: bool = False,
    levels: int = 29,
    progress_callback: Callable[[int, str], None] | None = None,
) -> str:
    """
    Run enfuse to blend input images into output_path.
    Returns the output path on success.
    """
    binary = find_enfuse()
    if not binary:
        raise RuntimeError(
            "enfuse not found. Install via:\n"
            "  brew install enblend-enfuse\n"
            "or download Hugin from https://hugin.sourceforge.io/"
        )

    out_path = Path(output_path)
    out_ext = out_path.suffix.lower()

    cmd = [binary]
    cmd += ["--exposure-weight", str(exposure_weight)]
    cmd += ["--saturation-weight", str(saturation_weight)]
    cmd += ["--contrast-weight", str(contrast_weight)]
    cmd += ["--levels", str(levels)]
    if hard_mask:
        cmd += ["--hard-mask"]

    if out_ext in {".jpg", ".jpeg"}:
        cmd += ["--compression=85"]
    elif out_ext in {".tif", ".tiff"}:
        cmd += ["--compression=lzw"]

    cmd += ["-o", str(output_path)]
    cmd += input_paths

    if progress_callback:
        progress_callback(0, "Starting enfuse...")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_lines = []
    total_steps = None
    current_step = 0

    for line in process.stdout:
        stripped = line.strip()
        output_lines.append(stripped)

        # Parse enfuse progress lines like "fusing image: 1/5"
        if "fusing image" in stripped.lower():
            parts = stripped.split(":")
            if len(parts) > 1:
                fraction = parts[-1].strip()
                if "/" in fraction:
                    try:
                        cur, total = fraction.split("/")
                        current_step = int(cur.strip())
                        total_steps = int(total.strip())
                        pct = int(current_step / total_steps * 90)
                        if progress_callback:
                            progress_callback(pct, stripped)
                    except ValueError:
                        pass
        elif progress_callback:
            progress_callback(-1, stripped)

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"enfuse failed:\n" + "\n".join(output_lines[-10:]))

    if not os.path.exists(output_path):
        raise RuntimeError(f"enfuse did not produce output file: {output_path}")

    if progress_callback:
        progress_callback(100, f"Done: {Path(output_path).name}")

    return output_path
