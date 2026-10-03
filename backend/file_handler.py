"""
Handles file opens from three sources:
  1. sys.argv  — direct CLI args (not argv_emulation; that's disabled)
  2. odoc      — Apple Event fired by Finder / 'Open With' / double-click
  3. URL scheme — totallyenfused://blend?files=/path/1.raf,/path/2.raf,...
"""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

SUPPORTED_EXT = {
    '.jpg', '.jpeg', '.tif', '.tiff', '.png',
    '.cr2', '.cr3', '.nef', '.arw', '.orf', '.raf',
    '.dng', '.rw2', '.pef', '.srw',
}

_emit = None          # set via set_emit() before registering handlers
_url_handler = None   # keep NSObject reference alive (URL scheme)
_docs_handler = None  # keep NSObject reference alive (odoc)

# Pre-ready queue: odoc events that arrive before the window is loaded
_pending: list[str] = []
_window_ready = False


def set_emit(fn):
    global _emit
    _emit = fn


def _send(paths: list[str]):
    """Filter paths and either emit immediately or queue for later."""
    global _pending
    valid = [p for p in paths if Path(p).exists() and Path(p).suffix.lower() in SUPPORTED_EXT]
    if not valid:
        return
    if _emit and _window_ready:
        _emit('files:open', {'paths': valid})
    else:
        _pending.extend(valid)


def drain_pending():
    """
    Called from main.py once the window's 'loaded' event fires.
    Marks the window as ready and flushes any queued paths.
    """
    global _window_ready, _pending
    _window_ready = True
    if _pending and _emit:
        _emit('files:open', {'paths': list(_pending)})
        _pending = []


def get_startup_files() -> list[str]:
    """Return valid image paths passed as direct CLI arguments (not via Apple Events)."""
    files = []
    for arg in sys.argv[1:]:
        if arg.startswith('-'):
            continue
        p = Path(arg)
        if p.exists() and p.suffix.lower() in SUPPORTED_EXT:
            files.append(str(p.resolve()))
    return files


def _extract_paths_from_desc(desc) -> list[str]:
    """
    Extract file paths from an NSAppleEventDescriptor.
    Handles both AEDescList (multiple files) and a single descriptor.
    """
    from Foundation import NSURL
    typeFileURL = 0x6675726C  # 'furl'
    paths = []

    count = desc.numberOfItems()
    if count > 0:
        # AEDescList — iterate items (1-indexed)
        for i in range(1, count + 1):
            item = desc.descriptorAtIndex_(i)
            coerced = item.coerceToDescriptorType_(typeFileURL)
            if coerced:
                url = NSURL.URLWithString_(coerced.stringValue())
                if url and url.isFileURL():
                    paths.append(str(url.path()))
    else:
        # Single descriptor — coerce directly
        coerced = desc.coerceToDescriptorType_(typeFileURL)
        if coerced:
            url = NSURL.URLWithString_(coerced.stringValue())
            if url and url.isFileURL():
                paths.append(str(url.path()))

    return paths


def register_url_handler():
    """
    Register the totallyenfused:// URL scheme handler via NSAppleEventManager.
    Must be called before webview.start() so the run loop picks it up.
    Returns the handler object (caller must keep a reference to prevent GC).
    """
    global _url_handler
    try:
        from AppKit import NSAppleEventManager
        from Foundation import NSObject

        # kInternetEventClass / kAEGetURL — both are 'GURL' = 0x4755524c
        kGURL = 0x4755524c
        keyDirectObject = 0x2d2d2d2d  # '----'

        class _URLHandler(NSObject):
            def handleGetURL_withReplyEvent_(self, event, reply):
                try:
                    url_str = event.paramDescriptorForKeyword_(keyDirectObject).stringValue()
                    parsed = urlparse(url_str)
                    params = parse_qs(parsed.query)

                    paths = []
                    if 'files' in params:
                        paths = [unquote(p) for p in params['files'][0].split(',') if p]
                    elif 'file' in params:
                        paths = [unquote(p) for p in params['file']]

                    _send(paths)
                except Exception as e:
                    print(f'[totally-enfused url handler] {e}')

        _url_handler = _URLHandler.alloc().init()
        NSAppleEventManager.sharedAppleEventManager() \
            .setEventHandler_andSelector_forEventClass_andEventID_(
                _url_handler,
                'handleGetURL:withReplyEvent:',
                kGURL, kGURL,
            )
        print('[totally-enfused] URL scheme handler registered')
        return _url_handler
    except ImportError:
        # Not macOS / pyobjc unavailable (e.g. dev in browser)
        return None


def register_open_docs_handler():
    """
    Register an odoc (open-document) Apple Event handler AND an NSApplication
    delegate method — covering all paths macOS uses to ask us to open files:

      • Finder 'Open With'
      • Double-click on a file associated with our app
      • Any app calling NSWorkspace openFile:withApplication:

    Without argv_emulation=True in the spec, this handler also handles the
    files passed at launch (they arrive as an odoc event on the first run-loop
    tick, before the window finishes loading; drain_pending() sends them later).
    """
    global _docs_handler
    try:
        from AppKit import NSAppleEventManager, NSApplication
        from Foundation import NSObject

        kCoreEventClass  = 0x61657674  # 'aevt'
        kAEOpenDocuments = 0x6F646F63  # 'odoc'
        keyDirectObject  = 0x2D2D2D2D  # '----'

        class _OpenDocsHandler(NSObject):
            def handleOpenDocs_withReplyEvent_(self, event, reply):
                try:
                    desc = event.paramDescriptorForKeyword_(keyDirectObject)
                    if desc:
                        paths = _extract_paths_from_desc(desc)
                        print(f'[totally-enfused odoc] got {len(paths)} path(s): {paths}')
                        _send(paths)
                except Exception as e:
                    print(f'[totally-enfused odoc handler] {e}')

            # Cocoa delegate path — NSWorkspace / Finder also calls this
            def application_openFiles_(self, app, filenames):
                try:
                    paths = list(filenames)
                    print(f'[totally-enfused openFiles:] {paths}')
                    _send(paths)
                except Exception as e:
                    print(f'[totally-enfused openFiles: error] {e}')

        _docs_handler = _OpenDocsHandler.alloc().init()

        # 1. NSAppleEventManager (handles Apple Events from any source)
        NSAppleEventManager.sharedAppleEventManager() \
            .setEventHandler_andSelector_forEventClass_andEventID_(
                _docs_handler,
                'handleOpenDocs:withReplyEvent:',
                kCoreEventClass,
                kAEOpenDocuments,
            )

        # 2. NSApplication delegate (Cocoa's own path for file opens)
        #    Only set if no delegate is already in place.
        app = NSApplication.sharedApplication()
        if app.delegate() is None:
            app.setDelegate_(_docs_handler)

        print('[totally-enfused] Open-document handler registered (initial)')
        return _docs_handler
    except ImportError:
        return None


def reinstall_odoc_handler():
    """
    Re-register the odoc handler AFTER webview.start() has finished initialising
    NSApplication (which installs its own default odoc handler via NSDocumentController,
    overriding ours). Call this from the window's 'loaded' event so it sticks.
    """
    global _docs_handler
    if _docs_handler is None:
        return
    try:
        from AppKit import NSAppleEventManager, NSApplication
        kCoreEventClass  = 0x61657674  # 'aevt'
        kAEOpenDocuments = 0x6F646F63  # 'odoc'

        NSAppleEventManager.sharedAppleEventManager() \
            .setEventHandler_andSelector_forEventClass_andEventID_(
                _docs_handler,
                'handleOpenDocs:withReplyEvent:',
                kCoreEventClass,
                kAEOpenDocuments,
            )

        # Also try to inject our file-open method into the live delegate
        app = NSApplication.sharedApplication()
        delegate = app.delegate()
        if delegate is not None and delegate is not _docs_handler:
            # Wrap: forward application:openFiles: to our handler
            try:
                import objc
                orig_cls = type(delegate)
                if not hasattr(orig_cls, '_te_patched'):
                    def _te_openFiles(self, sender, filenames):
                        try:
                            _send(list(filenames))
                        except Exception as e:
                            print(f'[totally-enfused openFiles patch] {e}')
                    objc.classAddMethod(
                        orig_cls,
                        b'application:openFiles:',
                        _te_openFiles,
                    )
                    orig_cls._te_patched = True
                    print('[totally-enfused] openFiles: injected into existing delegate')
            except Exception as e:
                print(f'[totally-enfused] delegate patch skipped: {e}')

        print('[totally-enfused] odoc handler reinstalled post-startup', flush=True)
    except Exception as e:
        print(f'[totally-enfused] reinstall_odoc_handler error: {e}', flush=True)
