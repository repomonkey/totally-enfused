#!/usr/bin/env python3
"""Totally Enfused — entry point."""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

if "--selftest" in sys.argv:
    from backend.selftest import run
    sys.exit(run())

import webview
from backend.api import API, set_window, _emit
from backend import settings as settings_mod
from backend.file_handler import (
    get_startup_files, install_open_handler, register_drop_handler,
    drain_pending, set_emit,
)


def get_frontend_url(dev: bool) -> str:
    if dev:
        return "http://localhost:5173"
    # PyInstaller bundles frontend/dist next to the executable
    frozen = getattr(sys, '_MEIPASS', None)
    if frozen:
        dist = Path(frozen) / "frontend" / "dist" / "index.html"
    else:
        dist = ROOT / "frontend" / "dist" / "index.html"
    return str(dist.resolve())


def main():
    dev = "--dev" in sys.argv

    s = settings_mod.load()
    api = API()

    # Wire up the file-open emit function
    set_emit(_emit)

    # Files passed as direct CLI arguments
    startup_files = get_startup_files()

    # Open With / double-click / URL scheme (macOS only, no-op elsewhere)
    install_open_handler()

    width = int(s.get("window_width") or 1280)
    height = int(s.get("window_height") or 800)

    window = webview.create_window(
        title="Totally Enfused",
        url=get_frontend_url(dev),
        js_api=api,
        width=width,
        height=height,
        min_size=(900, 600),
        background_color="#18181A",
    )

    set_window(window)

    def on_loaded():
        """Send startup files to the frontend once the JS bridge is ready."""
        register_drop_handler(window)
        if startup_files:
            _emit('files:open', {'paths': startup_files})
        drain_pending()  # files opened during launch

    def on_closed():
        if window.width and window.height:
            s["window_width"] = int(window.width)
            s["window_height"] = int(window.height)
            settings_mod.save(s)

    window.events.loaded += on_loaded
    window.events.closed += on_closed

    webview.start(
        debug=dev,
        http_server=True,
    )


if __name__ == "__main__":
    main()
