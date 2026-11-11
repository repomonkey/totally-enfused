"""Motion handling on synthetic brackets with a known moving object."""
import numpy as np
import pytest
import tifffile

from backend import deghost
from backend.api import unique_path

H, W = 400, 600
EVS = (-2, 0, 2)
REF = 1                      # the 0 EV frame


def scene(square_x: int) -> np.ndarray:
    """Linear-light scene: smooth texture plus a bright square at square_x."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    lin = 0.05 + 0.12 * (1 + np.sin(x / 23) * np.cos(y / 31)) + 0.1 * x / W
    lin[150:230, square_x:square_x + 80] = 0.5
    return np.repeat(lin[..., None], 3, axis=-1)


def write_bracket(tmp_path, square_xs, layout=True) -> list[str]:
    paths = []
    for ev, sx in zip(EVS, square_xs):
        enc = np.clip(scene(sx) * 2.0 ** ev, 0, 1) ** (1 / 2.2)
        rgba = np.dstack([(enc * 65535).astype(np.uint16), np.full((H, W), 65535, np.uint16)])
        p = tmp_path / f"f{ev:+d}.tif"
        tags = [(286, 5, 1, (0, 1), True), (287, 5, 1, (1, 15), True)] if layout else []
        tifffile.imwrite(p, rgba, photometric="rgb", extrasamples=["unassalpha"],
                         resolution=(150, 150), resolutionunit=2, extratags=tags)
        paths.append(str(p))
    return paths


def test_static_bracket_is_left_alone(tmp_path):
    paths = write_bracket(tmp_path, [250, 250, 250])
    out, moving = deghost.apply(paths, REF, 0.5, str(tmp_path))
    assert out == paths and moving == 0.0


def test_moving_square_is_replaced_from_reference(tmp_path):
    paths = write_bracket(tmp_path, [100, 250, 400])    # the square moves across the frames
    out, moving = deghost.apply(paths, REF, 0.5, str(tmp_path))
    assert out[REF] == paths[REF]
    assert out[0] != paths[0] and out[2] != paths[2]
    assert 0 < moving < 0.5

    before = tifffile.imread(paths[0])[..., :3].astype(np.float32)
    after = tifffile.imread(out[0])[..., :3].astype(np.float32)
    ref_square = (slice(170, 210), slice(270, 310))      # where the reference has the square
    old_square = (slice(170, 210), slice(120, 160))      # where frame 0 had it
    # Frame 0 now shows the square where the reference has it, at frame 0's exposure,
    # and background where it used to be
    true_square = (0.5 * 2.0 ** EVS[0]) ** (1 / 2.2) * 65535
    assert after[ref_square].mean() == pytest.approx(true_square, rel=0.05)
    assert after[old_square].mean() < before[old_square].mean() * 0.8
    # Far from any motion nothing changes
    static = (slice(10, 60), slice(10, 60))
    assert np.array_equal(after[static], before[static])


def test_canvas_position_tags_survive(tmp_path):
    # align_image_stack places layers on a canvas with X/YPosition; losing them shifts the frame
    paths = write_bracket(tmp_path, [100, 250, 400])
    out, _ = deghost.apply(paths, REF, 0.5, str(tmp_path))
    with tifffile.TiffFile(out[0]) as t:
        tags = t.pages[0].tags
        assert tags[287].value == (1, 15)
        assert tags[282].value == (150, 1)
        assert t.pages[0].shape == (H, W, 4)


def test_misaligned_frames_are_not_treated_as_motion(tmp_path):
    paths = write_bracket(tmp_path, [250, 250, 250])
    shifted = tifffile.imread(paths[0])
    tifffile.imwrite(paths[0], np.roll(shifted, 37, axis=(0, 1)), photometric="rgb",
                     extrasamples=["unassalpha"])
    out, moving = deghost.apply(paths, REF, 1.0, str(tmp_path))
    assert moving > deghost.MAX_MOVING
    assert out == paths


@pytest.mark.parametrize("sens,expected", [(0.0, 0.6), (1.0, 0.15)])
def test_sensitivity_range(sens, expected):
    assert deghost.threshold_for(sens) == pytest.approx(expected)


def test_unique_path_numbers_instead_of_overwriting(tmp_path):
    p = tmp_path / "set_enfused.tif"
    assert unique_path(str(p)) == str(p)
    p.write_bytes(b"x")
    assert unique_path(str(p)) == str(tmp_path / "set_enfused_01.tif")
    (tmp_path / "set_enfused_01.tif").write_bytes(b"x")
    assert unique_path(str(p)) == str(tmp_path / "set_enfused_02.tif")
