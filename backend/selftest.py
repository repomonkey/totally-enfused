"""
End-to-end check of the built app: `Totally Enfused --selftest`.

Blends a small synthetic JPEG bracket with a moving square through the full
pipeline (alignment, motion handling, sky split, enfuse, metadata). It catches what unit
tests in the dev environment can't: modules PyInstaller left out and tools the
bundle can't run. release.sh runs it before notarising.
"""
import sys
import tempfile
from pathlib import Path


def run() -> int:
    import numpy as np
    from PIL import Image
    from backend.api import run_pipeline, _pipeline_settings

    with tempfile.TemporaryDirectory(prefix="te-selftest-") as tmp:
        y, x = np.mgrid[0:300, 0:450].astype(np.float32)
        paths = []
        for i, ev in enumerate((-2, 0, 2)):
            lin = 0.05 + 0.12 * (1 + np.sin(x / 13) * np.cos(y / 17)) + 0.1 * x / 450
            lin[100:160, 60 + 120 * i:120 + 120 * i] = 0.5        # moves between frames
            enc = np.clip(lin * 2.0 ** ev, 0, 1) ** (1 / 2.2)
            p = Path(tmp) / f"frame{i}.jpg"
            Image.fromarray((np.dstack([enc] * 3) * 255).astype(np.uint8)).save(p, quality=95)
            paths.append(str(p))

        cfg = _pipeline_settings({"motion_enabled": True, "align_enabled": True,
                                   "split_enabled": True})     # two blends + merge
        stages = []
        out = run_pipeline(paths, str(Path(tmp) / "out.tif"), cfg,
                           lambda stage, pct, msg: stages.append(msg) if msg else None)
        size = Path(out).stat().st_size if Path(out).exists() else 0
        print("\n".join(stages))
        if size == 0:
            print("SELFTEST FAILED: no output", file=sys.stderr)
            return 1
        if not any("Merging sky" in s for s in stages):
            print("SELFTEST FAILED: sky split did not run", file=sys.stderr)
            return 1
        if not any("Finding movement" in s for s in stages):
            print("SELFTEST FAILED: motion handling did not run", file=sys.stderr)
            return 1
        print(f"SELFTEST OK ({size} bytes)")
        return 0
