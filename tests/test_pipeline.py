"""
Run:  .venv/bin/python -m pytest tests -q
RAW tests need a sample:  TE_SAMPLE_RAW=/path/to/file.raf
"""
import os
import queue
import subprocess
from pathlib import Path

import pytest

from backend import file_handler, image_utils

SAMPLE_RAW = os.environ.get("TE_SAMPLE_RAW")
needs_raw = pytest.mark.skipif(not SAMPLE_RAW, reason="set TE_SAMPLE_RAW")
needs_exiftool = pytest.mark.skipif(not image_utils.exiftool_cmd(), reason="exiftool not installed")


@pytest.fixture
def tif(tmp_path):
    from PIL import Image
    p = tmp_path / "a.tif"
    Image.new("RGB", (8, 8)).save(p)
    return str(p)


@pytest.fixture
def emitted(monkeypatch):
    q = queue.Queue()
    monkeypatch.setattr(file_handler, "_pending", [])
    monkeypatch.setattr(file_handler, "_window_ready", False)
    file_handler.set_emit(lambda event, payload: q.put((event, payload)))
    return q


def test_scheme_url_files_param():
    url = "totallyenfused://blend?files=/a/b%20c.raf,/d.tif"
    assert file_handler._paths_from_scheme_url(url) == ["/a/b c.raf", "/d.tif"]


def test_scheme_url_repeated_file_param():
    url = "totallyenfused://blend?file=/a.raf&file=/b.raf"
    assert file_handler._paths_from_scheme_url(url) == ["/a.raf", "/b.raf"]


def test_send_queues_until_window_ready(emitted, tif, tmp_path):
    file_handler._send([tif, str(tmp_path / "missing.tif")])
    assert emitted.empty()
    file_handler.drain_pending()
    assert emitted.get(timeout=1) == ("files:open", {"paths": [tif]})


def test_folder_goes_to_batch(emitted, tif, tmp_path):
    file_handler.drain_pending()
    file_handler._send([str(tmp_path), tif])
    assert emitted.get(timeout=1) == ("batch:open", {"paths": [str(tmp_path), tif]})


def test_send_after_ready_emits_off_thread(emitted, tif):
    file_handler.drain_pending()
    file_handler._send([tif])
    assert emitted.get(timeout=1) == ("files:open", {"paths": [tif]})


@needs_raw
def test_raw_converts_to_16bit_srgb(tmp_path):
    import tifffile
    [out] = image_utils.convert_raws_to_tiff([SAMPLE_RAW], str(tmp_path))
    with tifffile.TiffFile(out) as t:
        page = t.pages[0]
        assert page.dtype.name == "uint16"
        assert page.samplesperpixel == 3
        assert 34675 in page.tags  # ICC profile


@needs_raw
@needs_exiftool
def test_metadata_copied_from_raw(tmp_path, tif):
    icc = tmp_path / "sRGB.icc"
    icc.write_bytes(image_utils.srgb_icc_bytes())
    assert image_utils.copy_metadata(SAMPLE_RAW, tif, str(icc))
    tags = subprocess.run(
        image_utils.exiftool_cmd() + ["-s", "-Make", "-Model", "-Orientation",
         "-ProfileDescription", "-Software", tif],
        capture_output=True, text=True,
    ).stdout
    src_make = subprocess.run(
        image_utils.exiftool_cmd() + ["-s3", "-Make", SAMPLE_RAW], capture_output=True, text=True
    ).stdout.strip()
    assert src_make and src_make in tags
    assert "Orientation" not in tags  # pixels are already rotated by rawpy
    assert "sRGB" in tags
    assert "Totally Enfused" in tags


@needs_raw
@needs_exiftool
def test_ev_read_from_raw():
    assert image_utils.get_exif_ev(SAMPLE_RAW) is not None


@needs_raw
def test_reference_frame_keeps_normal_brightness(tmp_path):
    """Fixed brightness should match LibRaw's auto-brighten on the reference frame."""
    import numpy as np
    import rawpy
    import tifffile
    [out] = image_utils.convert_raws_to_tiff([SAMPLE_RAW], str(tmp_path))
    ours = tifffile.imread(out).mean() / 65535
    with rawpy.imread(SAMPLE_RAW) as raw:
        auto = raw.postprocess(use_camera_wb=True, output_bps=16).mean() / 65535
    assert abs(ours - auto) < 0.02


SAMPLE_JXL_DNG = os.environ.get("TE_SAMPLE_JXL_DNG")


@pytest.mark.skipif(not SAMPLE_JXL_DNG, reason="set TE_SAMPLE_JXL_DNG")
def test_unsupported_by_libraw_falls_back_to_core_image(tmp_path):
    """JPEG XL DNG 1.7 (Lightroom) isn't decodable by rawpy's LibRaw build."""
    import tifffile
    [out] = image_utils.convert_raws_to_tiff([SAMPLE_JXL_DNG], str(tmp_path))
    with tifffile.TiffFile(out) as t:
        page = t.pages[0]
        assert page.dtype.name == "uint16"
        assert page.samplesperpixel == 3
    assert image_utils._apple_render(SAMPLE_JXL_DNG, 200) is not None
