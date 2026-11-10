"""Bracket grouping. Real-folder test: TE_SAMPLE_BRACKET_DIR=/folder/with/one/bracket"""
import os

import pytest

from backend.batch import group_brackets, scan


def frame(name, t, exposure=0.01, level=None, ev=None):
    return {"path": f"/x/{name}", "time": t, "exposure": exposure, "level": level, "ev": ev}


def names(groups):
    return [[f["path"].rsplit("/", 1)[1] for f in g] for g in groups]


def test_back_to_back_brackets_split_on_repeated_exposure():
    frames = [frame("a1", 0, level=10), frame("a2", 0.2, level=8), frame("a3", 0.4, level=12),
              frame("b1", 0.6, level=10), frame("b2", 0.8, level=8), frame("b3", 1.0, level=12)]
    sets, singles = group_brackets(frames)
    assert names(sets) == [["a1", "a2", "a3"], ["b1", "b2", "b3"]]
    assert singles == []


def test_long_exposures_within_a_bracket_stay_together():
    # 1s, 3.7s, 15s frames: start times are far apart but the gap after each exposure is small
    frames = [frame("f1", 0, 1, level=5), frame("f2", 1.5, 3.7, level=3), frame("f3", 5.5, 15, level=1)]
    sets, _ = group_brackets(frames)
    assert names(sets) == [["f1", "f2", "f3"]]


def test_pause_starts_new_set_and_lone_frames_are_singles():
    frames = [frame("a1", 0, level=10), frame("a2", 0.3, level=8),
              frame("solo", 30, level=10),
              frame("c1", 60, level=10), frame("c2", 60.3, level=8)]
    sets, singles = group_brackets(frames)
    assert names(sets) == [["a1", "a2"], ["c1", "c2"]]
    assert [f["path"] for f in singles] == ["/x/solo"]


def test_fixed_size_when_camera_records_no_exposure_info():
    frames = [frame(f"f{i}", i * 0.2) for i in range(6)]
    assert names(group_brackets(frames)[0]) == [[f"f{i}" for i in range(6)]]
    assert names(group_brackets(frames, size=3)[0]) == [["f0", "f1", "f2"], ["f3", "f4", "f5"]]


def test_falls_back_to_exposure_compensation():
    frames = [frame("a1", 0, ev=0), frame("a2", 0.2, ev=-2), frame("b1", 0.4, ev=0), frame("b2", 0.6, ev=-2)]
    assert names(group_brackets(frames)[0]) == [["a1", "a2"], ["b1", "b2"]]


@pytest.mark.skipif(not os.environ.get("TE_SAMPLE_BRACKET_DIR"), reason="set TE_SAMPLE_BRACKET_DIR")
def test_scan_real_folder_finds_one_bracket():
    result = scan([os.environ["TE_SAMPLE_BRACKET_DIR"]])
    assert len(result["sets"]) == 1
    assert len(result["sets"][0]["paths"]) >= 2


def test_sets_never_span_folders():
    frames = [frame("a1", 0, level=10), frame("a2", 0.2, level=8)]
    other = {**frame("b1", 0.4, level=12), "path": "/y/b1"}
    sets, singles = group_brackets(frames + [other])
    assert names(sets) == [["a1", "a2"]]
    assert [f["path"] for f in singles] == ["/y/b1"]


def test_collect_files_recurses_and_skips_hidden(tmp_path):
    from backend.batch import collect_files
    (tmp_path / "sub").mkdir()
    (tmp_path / ".hidden").mkdir()
    for p in ["a.raf", "notes.txt", "sub/b.dng", ".hidden/c.raf", "sub/.d.raf"]:
        (tmp_path / p).write_bytes(b"")
    assert [p.split(str(tmp_path))[1] for p in collect_files([str(tmp_path)])] == ["/a.raf", "/sub/b.dng"]


@pytest.mark.skipif(not __import__("backend.tools", fromlist=["x"]).exiftool_cmd(),
                    reason="exiftool not installed")
def test_previous_results_are_ignored(tmp_path):
    from PIL import Image
    from backend import image_utils
    from backend.batch import read_frames
    src, out = tmp_path / "a.tif", tmp_path / "a_enfused.tif"
    Image.new("RGB", (8, 8)).save(src)
    Image.new("RGB", (8, 8)).save(out)
    image_utils.copy_metadata(str(src), str(out))
    assert [f["path"] for f in read_frames([str(src), str(out)])] == [str(src)]
