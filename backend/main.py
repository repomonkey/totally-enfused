#!/usr/bin/env python3
"""Totally Enfused — entry point."""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import webview
from backend.api import API, set_window, _emit
from backend import settings as settings_mod
from backend.file_handler import (
    get_startup_files, register_url_handler, register_open_docs_handler,
    reinstall_odoc_handler, drain_pending, set_emit,
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

    # Collect any files passed as direct CLI arguments (edge-case; main path is odoc)
    startup_files = get_startup_files()

    # Register handlers (macOS only, no-ops elsewhere)
    _url_handler = register_url_handler()            # totallyenfused:// URL scheme
    _open_docs_handler = register_open_docs_handler()  # odoc / 'Open With' / Finder

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
        # Re-register odoc handler now that NSApplication is fully initialised.
        # webview.start() installs NSApplication's default odoc handler (NSDocumentController)
        # which overrides our pre-registered one; doing it here ensures ours wins.
        reinstall_odoc_handler()
        # CLI args (direct launch with file paths)
        if startup_files:
            _emit('files:open', {'paths': startup_files})
        # odoc events that arrived before the window was ready
        drain_pending()

    def on_closed():
        try:
            w = window.gui.get_size(window.uid)
            if w and w[0] and w[1]:
                s["window_width"] = int(w[0])
                s["window_height"] = int(w[1])
                settings_mod.save(s)
        except Exception:
            pass

    window.events.loaded += on_loaded
    window.events.closed += on_closed

    webview.start(
        debug=dev,
        http_server=True,
    )


if __name__ == "__main__":
    main()
