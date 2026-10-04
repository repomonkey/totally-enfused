import os
import stat

from backend import tools


def _script(path, body):
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def test_runs_rejects_binary_killed_at_launch(tmp_path):
    # dyld refusing a library built for a newer macOS aborts the process with a signal
    assert not tools._runs(_script(tmp_path / "broken", "kill -ABRT $$"))


def test_runs_accepts_nonzero_exit(tmp_path):
    # align_image_stack --help exits 1 but is perfectly usable
    assert tools._runs(_script(tmp_path / "ok", "exit 1"))


def test_falls_through_to_a_working_candidate(tmp_path, monkeypatch):
    bundled = tmp_path / "Helpers"
    bundled.mkdir()
    _script(bundled / "enfuse", "kill -ABRT $$")
    good = _script(tmp_path / "enfuse", "exit 0")
    monkeypatch.setattr(tools, "_bundled_dirs", lambda: [bundled])
    monkeypatch.setitem(tools.SYSTEM_CANDIDATES, "enfuse", [good])
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)
    tools.find_tool.cache_clear()
    try:
        assert tools.find_tool("enfuse") == good
    finally:
        tools.find_tool.cache_clear()


def test_prefers_bundled(tmp_path, monkeypatch):
    bundled = tmp_path / "Helpers"
    bundled.mkdir()
    mine = _script(bundled / "enfuse", "exit 0")
    monkeypatch.setattr(tools, "_bundled_dirs", lambda: [bundled])
    monkeypatch.setitem(tools.SYSTEM_CANDIDATES, "enfuse", [_script(tmp_path / "other", "exit 0")])
    tools.find_tool.cache_clear()
    try:
        assert tools.find_tool("enfuse") == mine
        assert tools.is_bundled(mine)
    finally:
        tools.find_tool.cache_clear()
