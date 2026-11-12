"""
Sky / foreground split: two enfuse blends with different settings, merged
along a feathered line like a graduated filter.

The line is given in image fractions so it can be drawn on the preview:
`position` is its height at the horizontal centre (0 = top, 1 = bottom),
`feather` the width of the transition as a fraction of image height, and
`tilt` its angle in degrees (positive runs down to the right).
"""
import math
from pathlib import Path

import numpy as np


def foreground_weight(h: int, w: int, position: float, feather: float, tilt: float) -> np.ndarray:
    """h×w float32 weight: 0 = all sky blend, 1 = all foreground blend."""
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]
    line = position * h + (x - w / 2) * math.tan(math.radians(tilt))
    d = y - line
    if feather <= 0:
        return (d >= 0).astype(np.float32)
    t = np.clip(d / (feather * h) + 0.5, 0, 1)
    return t * t * (3 - 2 * t)                  # smoothstep: no visible edges at either end


def merge(foreground: str, sky: str, out_path: str, position: float, feather: float,
          tilt: float, jpeg_quality: int = 85) -> bytes | None:
    """
    Merge two enfuse TIFF outputs into out_path (.tif, .jpg or .png).
    Returns the ICC profile enfuse embedded, for the caller to re-embed
    where the output writer can't.
    """
    import tifffile

    with tifffile.TiffFile(foreground) as t:
        page = t.pages[0]
        fg = page.asarray()
        icc = page.tags[34675].value if 34675 in page.tags else None
        res = page.tags[282].value if 282 in page.tags else None
    sk = tifffile.imread(sky)
    if fg.shape != sk.shape:
        raise RuntimeError(f"Sky and foreground blends differ in size: {fg.shape} vs {sk.shape}")

    h, w = fg.shape[:2]
    wt = foreground_weight(h, w, position, feather, tilt)[..., None]
    out = fg.astype(np.float32) * wt + sk.astype(np.float32) * (1 - wt)
    if fg.shape[-1] == 4:
        out[..., 3] = np.minimum(fg[..., 3], sk[..., 3])   # valid only where both blends are
    out = np.clip(np.rint(out), 0, np.iinfo(fg.dtype).max).astype(fg.dtype)

    ext = Path(out_path).suffix.lower()
    if ext in (".tif", ".tiff"):
        kwargs = {"extrasamples": ["unassalpha"]} if out.shape[-1] == 4 else {}
        if res:
            kwargs.update(resolution=(res[0] / res[1], res[0] / res[1]), resolutionunit=2)
        tifffile.imwrite(out_path, out, photometric="rgb", compression="lzw",
                         iccprofile=icc, **kwargs)
    elif ext in (".jpg", ".jpeg"):
        from PIL import Image
        rgb = out[..., :3]
        if rgb.dtype == np.uint16:
            rgb = (rgb.astype(np.uint32) * 255 // 65535).astype(np.uint8)
        Image.fromarray(rgb).save(out_path, quality=int(jpeg_quality), icc_profile=icc)
    elif ext == ".png":
        import imagecodecs
        Path(out_path).write_bytes(imagecodecs.png_encode(out))
    else:
        raise RuntimeError(f"Unsupported output format: {ext}")
    return icc
