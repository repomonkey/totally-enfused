"""
Batch mode: find the image files in folders/selections and group them into
bracket sets.

Grouping, frames sorted by capture time:
  - a pause longer than `gap_s` after the previous frame's exposure ends
    starts a new set
  - so does a repeated exposure level (the next bracket has begun). The
    level comes from aperture/shutter/ISO, so it works on cameras that don't
    record bracket offsets in ExposureCompensation; EC is the fallback
  - sets never span folders
  - `size` overrides the exposure rule with a fixed frame count per set
Sets of one frame are reported separately as singles. Earlier results
(tagged Software=Totally Enfused) are ignored.
"""
import json
import math
import os
import subprocess
from datetime import datetime
from pathlib import Path

from .file_handler import SUPPORTED_EXT
from .image_utils import find_exiftool

DEFAULT_GAP_S = 4.0


def collect_files(paths: list[str]) -> list[str]:
    """Expand folders recursively (skipping hidden ones) and keep supported image files."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                out += [os.path.join(root, n) for n in sorted(names)
                        if not n.startswith('.') and Path(n).suffix.lower() in SUPPORTED_EXT]
        elif os.path.isfile(p) and Path(p).suffix.lower() in SUPPORTED_EXT:
            out.append(p)
    return list(dict.fromkeys(out))  # dedupe, keep order


def read_frames(paths: list[str]) -> list[dict]:
    """Capture metadata for each file via one exiftool call; mtime fallback."""
    meta = {}
    exiftool = find_exiftool()
    if exiftool and paths:
        try:
            res = subprocess.run(
                [exiftool, "-json", "-n", "-fast2", "-charset", "filename=utf8",
                 "-DateTimeOriginal", "-SubSecTimeOriginal", "-ExposureTime",
                 "-FNumber", "-ISO", "-ExposureCompensation", "-Software", "-@", "-"],
                input="\n".join(paths), capture_output=True, text=True, timeout=300,
            )
            for row in json.loads(res.stdout or "[]"):
                meta[row.get("SourceFile")] = row
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass

    frames = []
    for p in paths:
        m = meta.get(p, {})
        if str(m.get("Software", "")).startswith("Totally Enfused"):
            continue  # a previous result sitting next to its inputs
        frames.append({
            "path": p,
            "time": _capture_time(m) or os.path.getmtime(p),
            "exposure": _num(m.get("ExposureTime")) or 0.0,
            "ev": _num(m.get("ExposureCompensation")),
            "level": _exposure_level(m),
        })
    return frames


def group_brackets(frames: list[dict], gap_s: float = DEFAULT_GAP_S,
                   size: int | None = None) -> tuple[list[list[dict]], list[dict]]:
    """Returns (sets with 2+ frames, single frames)."""
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for f in sorted(frames, key=lambda f: (f["time"], Path(f["path"]).name)):
        if cur:
            prev = cur[-1]
            new = (f["time"] - (prev["time"] + prev["exposure"]) > gap_s
                   or Path(f["path"]).parent != Path(prev["path"]).parent)
            if size:
                new = new or len(cur) >= size
            else:
                new = new or _repeats_level(f, cur)
            if new:
                groups.append(cur)
                cur = []
        cur.append(f)
    if cur:
        groups.append(cur)
    sets = [g for g in groups if len(g) >= 2]
    singles = [g[0] for g in groups if len(g) == 1]
    return sets, singles


def scan(paths: list[str], size: int | None = None) -> dict:
    files = collect_files(paths)
    sets, singles = group_brackets(read_frames(files), size=size)
    return {
        "sets": [{"paths": [f["path"] for f in s], "evs": [f["ev"] for f in s]} for s in sets],
        "singles": [f["path"] for f in singles],
    }


# ── helpers ──────────────────────────────────────────────────────────────

def _repeats_level(f: dict, cur: list[dict]) -> bool:
    key = "level" if f["level"] is not None and all(c["level"] is not None for c in cur) else "ev"
    if f[key] is None:
        return False
    return any(c[key] is not None and abs(c[key] - f[key]) < 0.1 for c in cur)


def _exposure_level(m: dict) -> float | None:
    """Exposure in stops (EV100) from aperture, shutter and ISO."""
    n, t, iso = _num(m.get("FNumber")), _num(m.get("ExposureTime")), _num(m.get("ISO"))
    if not (n and t and iso):
        return None
    return math.log2(n * n / t) - math.log2(iso / 100)


def _capture_time(m: dict) -> float | None:
    raw = m.get("DateTimeOriginal")
    if not isinstance(raw, str):
        return None
    try:
        t = datetime.strptime(raw[:19], "%Y:%m:%d %H:%M:%S").timestamp()
    except ValueError:
        return None
    sub = str(m.get("SubSecTimeOriginal") or "").strip()
    return t + (float(f"0.{sub}") if sub.isdigit() else 0.0)


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
