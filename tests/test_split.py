"""Sky / foreground split: the mask and the merge of two blends."""
import numpy as np
import pytest
import tifffile
from PIL import Image

from backend import split

H, W = 200, 300


def test_weight_is_sky_above_and_foreground_below():
    wt = split.foreground_weight(H, W, 0.5, 0.2, 0)
    assert wt[0].max() == 0 and wt[-1].min() == 1
    assert wt[100, 150] == pytest.approx(0.5)
    assert np.all(np.diff(wt[:, 150]) >= 0)            # monotonic down the frame
    assert wt[79, 0] == 0 and wt[121, 0] == 1          # transition is feather × height wide


def test_hard_edge_when_feather_is_zero():
    wt = split.foreground_weight(H, W, 0.25, 0, 0)
    assert set(np.unique(wt)) == {0.0, 1.0}
    assert wt[49, 10] == 0 and wt[50, 10] == 1


def test_tilt_moves_the_line_down_to_the_right():
    wt = split.foreground_weight(H, W, 0.5, 0, 10)
    left = np.argmax(wt[:, 0] > 0.5)
    right = np.argmax(wt[:, -1] > 0.5)
    assert right - left == pytest.approx(W * np.tan(np.radians(10)), abs=2)


def _blend_file(path, value, dtype=np.uint16):
    top = np.iinfo(dtype).max
    a = np.full((H, W, 4), value, dtype)
    a[..., 3] = top
    tifffile.imwrite(path, a, photometric="rgb", extrasamples=["unassalpha"],
                     iccprofile=b"fake-icc", resolution=(300, 300), resolutionunit=2)
    return str(path)


@pytest.mark.parametrize("ext", ["tif", "jpg", "png"])
def test_merge_takes_sky_from_the_top(tmp_path, ext):
    fg = _blend_file(tmp_path / "fg.tif", 60000)
    sky = _blend_file(tmp_path / "sky.tif", 10000)
    out = tmp_path / f"out.{ext}"
    icc = split.merge(fg, sky, str(out), 0.5, 0.2, 0)
    assert icc == b"fake-icc"
    if ext == "tif":
        with tifffile.TiffFile(out) as t:
            px = t.pages[0].asarray()
            assert t.pages[0].compression == 5             # LZW
            assert t.pages[0].tags[34675].value == b"fake-icc"
        assert px[5, 5, 0] == 10000 and px[-5, 5, 0] == 60000 and px[5, 5, 3] == 65535
    else:
        px = np.asarray(Image.open(out))
        scale = 255 / 65535 if px.dtype == np.uint8 else 1
        assert px[5, 5, 0] == pytest.approx(10000 * scale, abs=2)
        assert px[-5, 5, 0] == pytest.approx(60000 * scale, abs=2)


def test_merge_rejects_mismatched_blends(tmp_path):
    fg = _blend_file(tmp_path / "fg.tif", 1)
    small = tmp_path / "sky.tif"
    tifffile.imwrite(small, np.zeros((10, 10, 4), np.uint16), photometric="rgb",
                     extrasamples=["unassalpha"])
    with pytest.raises(RuntimeError, match="differ in size"):
        split.merge(fg, str(small), str(tmp_path / "o.tif"), 0.5, 0.2, 0)
