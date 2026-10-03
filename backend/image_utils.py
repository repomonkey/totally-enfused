import base64
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".tif", ".tiff", ".png",
    ".cr2", ".cr3", ".nef", ".arw", ".orf", ".raf",
    ".dng", ".rw2", ".pef", ".srw",
}

RAW_EXTENSIONS = {
    ".cr2", ".cr3", ".nef", ".arw", ".orf", ".raf",
    ".dng", ".rw2", ".pef", ".srw",
}

THUMBNAIL_SIZE = (200, 150)


def is_supported(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def is_raw(path: str) -> bool:
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def get_thumbnail_b64(path: str) -> str:
    """Return a base64-encoded JPEG thumbnail for display in the UI."""
    if not PIL_AVAILABLE:
        return _placeholder_b64()

    try:
        if is_raw(path):
            return _thumbnail_from_raw(path)
        img = Image.open(path)
        img = _auto_orient(img)
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        return _image_to_b64(img)
    except Exception:
        return _placeholder_b64()


def get_preview_b64(path: str, max_size: tuple = (1200, 900)) -> str:
    """Return a larger base64-encoded preview for the comparison view."""
    if not PIL_AVAILABLE:
        return _placeholder_b64()
    try:
        if is_raw(path):
            return _preview_from_raw(path, max_size)
        img = Image.open(path)
        img = _auto_orient(img)
        img.thumbnail(max_size, Image.LANCZOS)
        return _image_to_b64(img)
    except Exception:
        return _placeholder_b64()


def get_exif_ev(path: str) -> float | None:
    """Return the exposure compensation from EXIF, or None if unavailable."""
    if PIEXIF_AVAILABLE and not is_raw(path):
        try:
            exif = piexif.load(path).get("Exif", {})
            exp_bias = exif.get(piexif.ExifIFD.ExposureBiasValue)
            if exp_bias:
                num, den = exp_bias
                return num / den if den else None
        except Exception:
            pass
    # piexif can't parse RAW containers (RAF, CR3, ...); exiftool can
    exiftool = find_exiftool()
    if exiftool:
        try:
            out = subprocess.run(
                [exiftool, "-n", "-s3", "-ExposureCompensation", path],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            return float(out) if out else None
        except (ValueError, subprocess.SubprocessError):
            pass
    return None


def reference_exposure(paths: list[str]) -> str:
    """The input closest to 0 EV, falling back to the middle frame."""
    evs = [(abs(ev), i) for i, p in enumerate(paths)
           if (ev := get_exif_ev(p)) is not None]
    return paths[min(evs)[1]] if evs else paths[len(paths) // 2]


def _auto_bright_factor(path: str) -> float:
    """The linear scale LibRaw's auto-brighten would apply to this frame."""
    import numpy as np
    import rawpy
    kw = dict(use_camera_wb=True, half_size=True, gamma=(1, 1), output_bps=16)
    with rawpy.imread(path) as raw:
        auto = raw.postprocess(no_auto_bright=False, **kw)
    with rawpy.imread(path) as raw:
        fixed = raw.postprocess(no_auto_bright=True, **kw)
    usable = (fixed > 0) & (auto < 65535)  # ratio is distorted where either side clips
    if not usable.any():
        return 1.0
    return float(np.median(auto[usable]) / np.median(fixed[usable]))


def find_exiftool() -> str | None:
    for c in ("/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool", "/opt/local/bin/exiftool"):
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return shutil.which("exiftool")


def srgb_icc_bytes() -> bytes:
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def copy_metadata(source: str, dest: str, icc_path: str | None = None) -> bool:
    """
    Copy EXIF/XMP from an original exposure onto the blended output so
    editors see camera, lens and capture data. Optionally embed an ICC profile.
    Returns False if exiftool isn't available or the copy failed.
    """
    exiftool = find_exiftool()
    if not exiftool:
        return False
    cmd = [exiftool, "-q", "-q", "-overwrite_original",
           "-TagsFromFile", source, "-exif:all", "-xmp:all",
           "-Software=Totally Enfused"]
    if is_raw(source):
        # rawpy has already rotated the pixels; copying Orientation would rotate twice
        cmd.append("--Orientation")
    if icc_path:
        cmd.append(f"-ICC_Profile<={icc_path}")
    cmd.append(dest)
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0
    except subprocess.SubprocessError:
        return False


def get_image_info(path: str) -> dict:
    """Return basic info about an image: dimensions, format, EV."""
    info = {"path": path, "name": Path(path).name, "ev": None, "width": None, "height": None, "format": Path(path).suffix.lower()}
    if PIL_AVAILABLE:
        try:
            with Image.open(path) as img:
                info["width"], info["height"] = img.size
        except Exception:
            pass
    info["ev"] = get_exif_ev(path)
    return info


def _auto_orient(img):
    try:
        exif = img._getexif()
        if not exif:
            return img
        orientation_key = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None)
        if orientation_key and orientation_key in exif:
            orientation = exif[orientation_key]
            rotations = {3: 180, 6: 270, 8: 90}
            if orientation in rotations:
                img = img.rotate(rotations[orientation], expand=True)
    except Exception:
        pass
    return img


def _thumbnail_from_raw(path: str) -> str:
    try:
        import rawpy
        with rawpy.imread(path) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                from io import BytesIO
                img = Image.open(BytesIO(thumb.data))
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                return _image_to_b64(img)
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                img = Image.fromarray(thumb.data)
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                return _image_to_b64(img)
    except Exception:
        pass
    return _placeholder_b64()


def _preview_from_raw(path: str, max_size: tuple) -> str:
    try:
        import rawpy
        with rawpy.imread(path) as raw:
            rgb = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=False)
            img = Image.fromarray(rgb)
            img.thumbnail(max_size, Image.LANCZOS)
            return _image_to_b64(img)
    except Exception:
        pass
    return _placeholder_b64()


def _image_to_b64(img: "Image.Image") -> str:
    from io import BytesIO
    buf = BytesIO()
    rgb = img.convert("RGB")
    rgb.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _placeholder_b64() -> str:
    """Return a tiny grey placeholder PNG as base64."""
    w, h = 200, 150
    png_data = _create_solid_png(w, h, (40, 40, 42))
    return base64.b64encode(png_data).decode()


def needs_raw_conversion(paths: list[str]) -> bool:
    return any(is_raw(p) for p in paths)


def convert_raws_to_tiff(
    paths: list[str],
    output_dir: str,
    progress_callback: Callable[[int, str], None] | None = None,
) -> list[str]:
    """
    Convert any RAW files in paths to 16-bit sRGB TIFF.
    Non-RAW files are returned as-is.
    Returns a list of paths in the same order (mix of original + converted).

    LibRaw's auto-brighten would scale each frame independently, pulling the
    brackets toward each other and leaving enfuse little to work with. Instead
    one factor is measured on the reference (nearest 0 EV) frame and applied
    to every frame, so normal brightness is kept and the bracket spread survives.
    """
    import rawpy
    import tifffile

    icc = srgb_icc_bytes()
    raws = [p for p in paths if is_raw(p)]
    bright = _auto_bright_factor(reference_exposure(raws)) if raws else 1.0
    results = []
    total = len(paths)
    for i, path in enumerate(paths):
        if not is_raw(path):
            results.append(path)
            continue
        # Index prefix keeps same-named files from different folders apart
        out_path = os.path.join(output_dir, f"{i:03d}_{Path(path).stem}.tif")
        if progress_callback:
            progress_callback(int(i / total * 100), f"Converting {Path(path).name}…")
        try:
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=True,
                    bright=bright,
                    output_bps=16,
                    output_color=rawpy.ColorSpace.sRGB,
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                )
            # Uncompressed: these are temp files and libtiff in Hugin reads them fastest
            tifffile.imwrite(out_path, rgb, photometric="rgb", iccprofile=icc)
            results.append(out_path)
        except Exception as e:
            raise RuntimeError(f"Failed to convert {Path(path).name}: {e}") from e
    if progress_callback:
        progress_callback(100, "RAW conversion complete")
    return results


def _create_solid_png(width: int, height: int, color: tuple) -> bytes:
    r, g, b = color
    raw = bytes([0] + [r, g, b] * width) * height
    def chunk(name: bytes, data: bytes) -> bytes:
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend
