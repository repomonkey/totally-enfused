# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Totally Enfused — macOS
Run from the project root:
    pyinstaller build/build_mac.spec
"""

from pathlib import Path
import os
import sys

ROOT = Path(SPECPATH).parent

block_cipher = None

a = Analysis(
    [str(ROOT / 'backend' / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'frontend' / 'dist'), 'frontend/dist'),
    ],
    hiddenimports=[
        # pywebview
        'webview',
        'webview.platforms.cocoa',
        'webview.http',
        'bottle',
        'proxy_tools',
        # imaging
        'PIL',
        'PIL.Image',
        'PIL.TiffImagePlugin',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'rawpy',
        'piexif',
        # tifffile loads these lazily by name, so PyInstaller misses them:
        # LZW/PackBits/predictors (align_image_stack writes LZW TIFFs), deflate, JPEG
        'imagecodecs._shared_cython',   # imported by every codec module
        'imagecodecs._imcd',
        'imagecodecs._zlib',
        'imagecodecs._deflate',
        'imagecodecs._jpeg8',
        'backend.selftest',
        # pyobjc (macOS)
        'AppKit',
        'Foundation',
        'objc',
        'WebKit',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy.distutils'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Totally Enfused',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # UPX breaks some pyobjc binaries
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,  # disabled — our odoc handler covers both startup and runtime opens
    target_arch=None,      # set to 'arm64' or 'x86_64' for single-arch builds
    codesign_identity=None,
    entitlements_file=str(ROOT / 'build' / 'entitlements.plist'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Totally Enfused',
)

app = BUNDLE(
    coll,
    name='Totally Enfused.app',
    icon=str(ROOT / 'assets' / 'icon.icns'),
    bundle_identifier='com.andyhutchinson.totally-enfused',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': '© 2026 Andy Hutchinson',
        'CFBundleDisplayName': 'Totally Enfused',
        'CFBundleShortVersionString': '1.1.1',
        'CFBundleVersion': '3',
        # Releases: macOS 26 (the bundled Homebrew Python needs it). Local builds,
        # e.g. on Intel (see INTEL.md), set TE_MIN_MACOS to the build machine's version.
        'LSMinimumSystemVersion': os.environ.get('TE_MIN_MACOS', '26.0'),
        'LSApplicationCategoryType': 'public.app-category.photography',

        # URL scheme: totallyenfused://blend?files=...
        'CFBundleURLTypes': [{
            'CFBundleURLName': 'com.andyhutchinson.totally-enfused',
            'CFBundleURLSchemes': ['totallyenfused'],
        }],

        # 'Open With' for common image types
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Image',
            'CFBundleTypeRole': 'Viewer',
            'LSHandlerRank': 'Alternate',
            'LSItemContentTypes': [
                'public.jpeg',
                'public.tiff',
                'public.png',
                'public.camera-raw-image',
                'com.canon.cr2-raw-image',
                'com.canon.cr3-raw-image',
                'com.nikon.nef-raw-image',
                'com.sony.arw-raw-image',
                'com.fuji.raw-image',
                'com.olympus.orf-raw-image',
                'com.adobe.raw-image',
            ],
        }],
    },
)
