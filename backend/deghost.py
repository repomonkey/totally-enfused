"""
Motion handling for exposure fusion.

enfuse blends every frame pixel by pixel, so anything that moved between
frames (waves, leaves, birds, people) is averaged into a soft ghost.

Here each aligned frame is compared with a reference frame after matching
their tones. Where a frame differs from the reference, its pixels are replaced
with the reference's pixels re-toned to that frame's exposure, with feathered
edges. Every frame then agrees in the moving areas, so enfuse still blends them
normally: tones match the rest of the image (no seams) and the moving detail
comes from a single moment. A false positive costs little, because the
replacement looks like what that frame would have recorded anyway.

Detection runs at reduced resolution (WORK_PX on the long edge), which is
plenty for regions of motion and keeps memory modest.
"""
import math
from pathlib import Path

import numpy as np

WORK_PX = 1600
MAX_MOVING = 0.6        # beyond this the frames disagree everywhere: alignment, not motion
# XResolution, YResolution, XPosition, YPosition, ResolutionUnit
LAYOUT_TAGS = (282, 283, 286, 287, 296)
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def threshold_for(sensitivity: float) -> float:
    """Difference in stops that counts as motion: 0 → 0.6 (obvious only), 1 → 0.15 (subtle)."""
    return 0.6 - 0.45 * min(max(sensitivity, 0.0), 1.0)


def apply(paths: list[str], reference: int, sensitivity: float, out_dir: str) -> tuple[list[str], float]:
    """
    Write motion-corrected copies of the non-reference frames that differ from it.
    Returns (paths for enfuse, fraction of the image treated as moving).
    Paths are unchanged when no motion is found or the result looks unreliable.
    """
    frames = [_load(p) for p in paths]
    h, w = frames[0]["rgb"].shape[:2]
    if any(f["rgb"].shape[:2] != (h, w) for f in frames):
        return paths, 0.0  # sizes differ (alignment off on mismatched files): nothing to compare
    factor = max(1, math.ceil(max(h, w) / WORK_PX))
    small = [_small_rgb(f, factor) for f in frames]
    lum = [_linear_luminance(s) for s in small]
    valid = [_small_alpha(f, factor) for f in frames]

    ref = lum[reference]
    thr = threshold_for(sensitivity)
    grow = max(2, round(max(ref.shape) / 200))
    masks: dict[int, np.ndarray] = {}
    for i, y in enumerate(lum):
        if i == reference:
            continue
        both = valid[reference] & valid[i]
        ys = _match_tones(y, ref, both)
        # Only compare where both frames hold real detail: not clipped, not lost in noise
        comparable = both & (ref > 0.01) & (ref < 0.92) & (y > 0.004) & (y < 0.95) & (ys < 0.92)
        a = _box_blur(np.log2(ref + 1e-4), 2)
        b = _box_blur(np.log2(ys + 1e-4), 2)
        moving = (np.abs(a - b) > thr) & comparable
        masks[i] = _clean(moving, grow)

    union = np.zeros_like(ref, dtype=bool)
    for m in masks.values():
        union |= m
    fraction = float(union.mean())
    if fraction == 0.0 or fraction > MAX_MOVING:
        return paths, fraction

    out = list(paths)
    for i, m in masks.items():
        if not m.any():
            continue
        static = valid[reference] & valid[i] & ~m
        curves = [_fit_curve(small[reference][..., c], small[i][..., c], static) for c in range(3)]
        if any(c is None for c in curves):
            continue
        weight = np.clip(_box_blur(m.astype(np.float32), grow) * 1.5, 0, 1)   # feathered edges
        full = _upscale(weight, factor, h, w)
        if frames[reference]["alpha"] is not None:
            full[frames[reference]["alpha"] == 0] = 0   # no reference data there to borrow
        out[i] = str(Path(out_dir) / f"motion_{i:03d}.tif")
        _write_replaced(frames[i], frames[reference], curves, full, out[i])
    return out, fraction


# ── image I/O ─────────────────────────────────────────────────────────────

def _load(path: str) -> dict:
    """RGB array, optional alpha, full-scale value, ICC profile and layout tags of a frame."""
    layout = {}
    if Path(path).suffix.lower() in (".tif", ".tiff"):
        import tifffile
        with tifffile.TiffFile(path) as t:
            page = t.pages[0]
            arr = page.asarray()
            icc = page.tags[34675].value if 34675 in page.tags else None
            # Hugin places layers on a shared canvas with these; dropping them shifts the frame
            layout = {code: page.tags[code].value for code in LAYOUT_TAGS if code in page.tags}
    else:
        from PIL import Image
        with Image.open(path) as im:
            icc = im.info.get("icc_profile")
            arr = np.asarray(im.convert("RGBA" if "A" in im.getbands() else "RGB"))
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    maxval = 65535 if arr.dtype == np.uint16 else 255
    alpha = arr[..., 3] if arr.shape[-1] >= 4 else None
    return {"rgb": arr[..., :3], "alpha": alpha, "max": maxval, "icc": icc,
            "dtype": arr.dtype, "layout": layout}


def _write_replaced(frame: dict, ref: dict, curves: list, weight: np.ndarray, path: str):
    """frame with moving pixels blended towards the re-toned reference, by weight (0..1)."""
    import tifffile
    rgb = frame["rgb"].copy()
    sel = weight > 0
    src = ref["rgb"][sel].astype(np.float32) / ref["max"]
    synth = np.stack([np.interp(src[:, c], *curves[c]) for c in range(3)], axis=-1) * frame["max"]
    wsel = weight[sel][:, None]
    rgb[sel] = np.clip(rgb[sel] * (1 - wsel) + synth * wsel + 0.5, 0, frame["max"]).astype(frame["dtype"])

    data = rgb if frame["alpha"] is None else np.dstack([rgb, frame["alpha"]])
    kwargs = {"iccprofile": frame["icc"]} if frame["icc"] else {}
    if frame["alpha"] is not None:
        kwargs["extrasamples"] = ["unassalpha"]
    lay = frame["layout"]
    if 282 in lay and 283 in lay:
        kwargs["resolution"] = (lay[282], lay[283])
        kwargs["resolutionunit"] = lay.get(296, 2)
    extratags = [(code, 5, 1, lay[code], True) for code in (286, 287) if code in lay]   # X/YPosition
    tifffile.imwrite(path, data, photometric="rgb", extratags=extratags, **kwargs)


# ── small-scale analysis ──────────────────────────────────────────────────

def _blocks(a: np.ndarray, f: int) -> np.ndarray:
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    shape = (h // f, f, w // f, f) + a.shape[2:]
    return a[:h, :w].reshape(shape)


def _small_rgb(frame: dict, f: int) -> np.ndarray:
    """Block-averaged RGB, 0..1, still in the file's encoding (gamma)."""
    return _blocks(frame["rgb"], f).mean(axis=(1, 3), dtype=np.float32) / frame["max"]


def _linear_luminance(rgb: np.ndarray) -> np.ndarray:
    return np.power(np.clip(rgb, 0, 1), 2.2) @ LUMA   # roughly linear light


def _small_alpha(frame: dict, f: int) -> np.ndarray:
    if frame["alpha"] is None:
        h, w = frame["rgb"].shape[0] // f, frame["rgb"].shape[1] // f
        return np.ones((h, w), dtype=bool)
    return _blocks(frame["alpha"], f).min(axis=(1, 3)) > 0


def _fit_curve(x: np.ndarray, y: np.ndarray, sel: np.ndarray, bins: int = 64):
    """
    Monotonic curve mapping values x onto y, learned from the selected pixels:
    for each band of x, the median y. Returns (knots_x, knots_y), or None if
    there's too little data. Frames differ by more than an exposure multiplier
    (tone curves, clipping), so the mapping is learned rather than assumed.
    """
    sel = sel & (x > 0.002) & (x < 0.998)
    if sel.sum() < 2000:
        return None
    xs_all, ys_all = x[sel], y[sel]
    edges = np.quantile(xs_all, np.linspace(0, 1, bins + 1))
    band = np.clip(np.searchsorted(edges, xs_all, side="right") - 1, 0, bins - 1)
    xs, vs = [], []
    for b in range(bins):
        m = band == b
        if m.sum() >= 20:
            xs.append(float(np.median(xs_all[m])))
            vs.append(float(np.median(ys_all[m])))
    if len(xs) < 4:
        return None
    vs = list(np.maximum.accumulate(vs))   # brighter in x must stay brighter
    # Beyond the data, keep the ratio seen at the ends rather than clamping:
    # a moving object can be brighter or darker than anything static
    if xs[0] > 0:
        xs, vs = [0.0] + xs, [0.0] + vs
    if xs[-1] < 1:
        xs, vs = xs + [1.0], vs + [min(1.0, max(vs[-1], vs[-1] / xs[-1]))]
    return np.array(xs), np.array(vs)


def _match_tones(y: np.ndarray, ref: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Frame y mapped onto the reference's tones (moving pixels are a minority, medians ignore them)."""
    curve = _fit_curve(y, ref, valid & (ref > 0.002) & (ref < 0.97) & (y < 0.97))
    return y if curve is None else np.interp(y, *curve).astype(np.float32)


def _box_blur(a: np.ndarray, r: int) -> np.ndarray:
    """Mean filter of radius r (separable, edges clamped)."""
    if r <= 0:
        return a
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
        n = a.shape[axis]
        hi = np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(c, range(0, n), axis=axis)
        a = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return a


def _clean(mask: np.ndarray, grow: int) -> np.ndarray:
    """Drop isolated specks (noise), then grow regions so their edges are covered."""
    m = mask.astype(np.float32)
    opened = _box_blur(m, 1) > 0.999          # erode
    opened = _box_blur(opened.astype(np.float32), 1) > 0.001   # dilate back
    return _box_blur(opened.astype(np.float32), grow) > 0.001


def _upscale(a: np.ndarray, f: int, h: int, w: int) -> np.ndarray:
    big = np.repeat(np.repeat(a, f, axis=0), f, axis=1)
    return np.pad(big, ((0, h - big.shape[0]), (0, w - big.shape[1])), mode="edge")
