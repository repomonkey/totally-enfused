import subprocess
import os
from pathlib import Path
from typing import Callable

from .tools import find_tool


def find_enfuse() -> str | None:
    return find_tool("enfuse")


def blend(
    input_paths: list[str],
    output_path: str,
    exposure_weight: float = 1.0,
    saturation_weight: float = 0.2,
    contrast_weight: float = 0.0,
    hard_mask: bool = False,
    levels: int = 29,
    jpeg_quality: int = 85,
    exposure_optimum: float = 0.5,
    highlight_protect: float = 0.0,
    progress_callback: Callable[[int, str], None] | None = None,
    on_process: Callable[[subprocess.Popen], None] | None = None,
) -> str:
    """
    Run enfuse to blend input images into output_path.
    Returns the output path on success.
    """
    binary = find_enfuse()
    if not binary:
        raise RuntimeError(
            "enfuse not found. The bundled copy needs macOS 27 or later; on older "
            "systems install Hugin from https://hugin.sourceforge.io/"
        )

    out_path = Path(output_path)
    out_ext = out_path.suffix.lower()

    cmd = [binary]
    cmd += ["--exposure-weight", str(exposure_weight)]
    cmd += ["--saturation-weight", str(saturation_weight)]
    cmd += ["--contrast-weight", str(contrast_weight)]
    cmd += ["--levels", str(levels)]
    # enfuse picks CIELUV for files with an ICC profile (all of ours); at
    # high-contrast edges that leaves black and coloured specks where the
    # pyramid undershoots. CIELAB blends the same but without them.
    cmd += ["--blend-colorspace=CIELAB"]
    # Brightness the exposure weighting favours (0.5 = mid-grey). Higher lifts
    # shadows by preferring brighter frames; lower keeps skies darker.
    cmd += [f"--exposure-optimum={exposure_optimum:g}"]
    if highlight_protect > 0:
        # Zero exposure weight for near-white pixels so a bright frame's
        # blown highlights don't dilute a darker frame's sky.
        cmd += [f"--exposure-cutoff=0%:{100 - highlight_protect:g}%"]
    if hard_mask:
        cmd += ["--hard-mask"]

    if out_ext in {".jpg", ".jpeg"}:
        cmd += [f"--compression={int(jpeg_quality)}"]
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
    if on_process:
        on_process(process)  # lets the caller terminate it on cancel

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
