"""
Routes files from outside the app into the frontend:
  1. sys.argv            — direct CLI launch with file paths
  2. application:openURLs: — Finder 'Open With', double-click, other apps
                            (DxO, Lightroom 'Edit In'), and the
                            totallyenfused://blend?files=... URL scheme
  3. Native drag and drop  — see register_drop_handler()

pywebview's Cocoa AppDelegate doesn't implement application:openURLs:, so
macOS falls back to NSDocumentController, which fails with "cannot open
files in the 'Image' format". We add the method to pywebview's delegate
class with a PyObjC category; NSApplication then routes both launch-time
and runtime opens through it.
"""
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

SUPPORTED_EXT = {
    '.jpg', '.jpeg', '.tif', '.tiff', '.png',
    '.cr2', '.cr3', '.nef', '.arw', '.orf', '.raf',
    '.dng', '.rw2', '.pef', '.srw',
}

_emit = None
_lock = threading.Lock()
_pending: list[tuple[str, list[str]]] = []   # (event, paths) arriving before the window loads
_window_ready = False
_drop_registered = False


def set_emit(fn):
    global _emit
    _emit = fn


def _send(paths: list[str]):
    """
    Route opened/dropped paths to the frontend: files go to the single-set view
    (files:open); anything including a folder goes to batch mode (batch:open).
    Queued until the window has loaded.
    """
    dirs = [p for p in paths if Path(p).is_dir()]
    files = [p for p in paths if Path(p).is_file() and Path(p).suffix.lower() in SUPPORTED_EXT]
    print(f'[totally-enfused] open: {len(files)} file(s), {len(dirs)} folder(s) of {len(paths)}', flush=True)
    if dirs:
        event, payload = 'batch:open', dirs + files
    elif files:
        event, payload = 'files:open', files
    else:
        return
    with _lock:
        if not _window_ready:
            _pending.append((event, payload))
            return
    # Open events arrive on the main thread, and evaluate_js blocks until the
    # main thread runs the script — emitting inline deadlocks the app.
    threading.Thread(target=_emit, args=(event, {'paths': payload}), daemon=True).start()


def drain_pending():
    """Call once the window has loaded: marks it ready and flushes queued opens."""
    global _window_ready, _pending
    with _lock:
        _window_ready = True
        queued, _pending = _pending, []
    for event, paths in queued:
        _emit(event, {'paths': paths})


def get_startup_files() -> list[str]:
    """Image paths passed as direct CLI arguments."""
    return [
        str(Path(a).resolve()) for a in sys.argv[1:]
        if not a.startswith('-') and Path(a).is_file()
        and Path(a).suffix.lower() in SUPPORTED_EXT
    ]


def _paths_from_scheme_url(url: str) -> list[str]:
    """totallyenfused://blend?files=/a.raf,/b.raf  or  ?file=/a.raf&file=/b.raf"""
    params = parse_qs(urlparse(url).query)
    if 'files' in params:
        return [unquote(p) for p in params['files'][0].split(',') if p]
    return [unquote(p) for p in params.get('file', [])]


def install_open_handler():
    """Add application:openURLs: to pywebview's AppDelegate. Call before webview.start()."""
    try:
        import objc
        from webview.platforms.cocoa import BrowserView
    except ImportError:
        return  # not macOS

    class AppDelegate(objc.Category(BrowserView.AppDelegate)):
        def application_openURLs_(self, app, urls):
            paths = []
            for url in urls:
                if url.isFileURL():
                    paths.append(str(url.path()))
                elif url.scheme() == 'totallyenfused':
                    paths.extend(_paths_from_scheme_url(str(url.absoluteString())))
            _send(paths)


def register_drop_handler(window):
    """
    Native drag and drop. WKWebView's File objects carry no filesystem path,
    but pywebview records the paths on the native side and attaches them as
    pywebviewFullPath when a drop listener is registered through its DOM API.
    Call from the window's loaded event.
    """
    global _drop_registered
    if _drop_registered:  # 'loaded' fires again on page reload
        return
    _drop_registered = True
    from webview.dom import DOMEventHandler

    def on_drop(event):
        files = event.get('dataTransfer', {}).get('files', [])
        _send([f['pywebviewFullPath'] for f in files if f.get('pywebviewFullPath')])

    window.dom.document.events.drop += DOMEventHandler(on_drop, prevent_default=True)
