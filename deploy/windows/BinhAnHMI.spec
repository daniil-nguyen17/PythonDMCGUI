# -*- mode: python ; coding: utf-8 -*-
#
# BinhAnHMI PyInstaller spec — onedir bundle for Windows
#
# Run from repo root:
#   python -m PyInstaller deploy/windows/BinhAnHMI.spec --clean --noconfirm
#
# Output: dist/BinhAnHMI/BinhAnHMI.exe

import pathlib

from kivy_deps import sdl2, glew, angle
from kivy.tools.packaging.pyinstaller_hooks import hookspath, runtime_hooks, get_deps_minimal

# Repo root is two directories above this spec file.
# All source paths are resolved relative to the repo root so the spec works
# regardless of the current working directory when PyInstaller is invoked.
REPO_ROOT = pathlib.Path(SPECPATH).parent.parent
SRC = REPO_ROOT / 'src'
VENDOR_DIR = REPO_ROOT / 'deploy' / 'windows' / 'vendor'

# get_deps_minimal returns {'hiddenimports': [...], 'excludes': [...], 'binaries': [...]}.
# We must merge our app-specific values to avoid duplicate keyword arg errors.
_kivy_deps = get_deps_minimal(window='sdl2')

_app_hiddenimports = [
    'win32timezone',                        # kivy FileChooser dep
    'pkg_resources.py2_compat',
    'dmccodegui.screens.flat_grind',
    'dmccodegui.screens.serration',
    'dmccodegui.screens.convex',
]

_app_binaries = [
    (str(VENDOR_DIR / 'dll' / 'x64' / 'gclib.dll'),               'dll/x64'),
    (str(VENDOR_DIR / 'dll' / 'x64' / 'gclibo.dll'),              'dll/x64'),
    (str(VENDOR_DIR / 'dll' / 'x64' / 'libcrypto-1_1-x64.dll'),  'dll/x64'),
    (str(VENDOR_DIR / 'dll' / 'x64' / 'libssl-1_1-x64.dll'),     'dll/x64'),
]

_app_excludes = ['dmccodegui.screens.diagnostics']

_analysis_kwargs = dict(_kivy_deps)
_analysis_kwargs['hiddenimports'] = _analysis_kwargs.get('hiddenimports', []) + _app_hiddenimports
_analysis_kwargs['binaries']      = _analysis_kwargs.get('binaries', [])      + _app_binaries
_analysis_kwargs['excludes']      = _analysis_kwargs.get('excludes', [])      + _app_excludes

a = Analysis(
    [str(SRC / 'dmccodegui' / '__main__.py')],
    pathex=[str(SRC)],
    datas=[
        # KV files — root UI level (diagnostics.kv is excluded from KV_FILES in
        # main.py so including it in the bundle is harmless)
        (str(SRC / 'dmccodegui' / 'ui' / '*.kv'),             'dmccodegui/ui'),
        # Machine-type sub-directories
        (str(SRC / 'dmccodegui' / 'ui' / 'flat_grind' / '*.kv'), 'dmccodegui/ui/flat_grind'),
        (str(SRC / 'dmccodegui' / 'ui' / 'serration' / '*.kv'),  'dmccodegui/ui/serration'),
        (str(SRC / 'dmccodegui' / 'ui' / 'convex' / '*.kv'),     'dmccodegui/ui/convex'),
        # Image assets
        (str(SRC / 'dmccodegui' / 'assets' / 'images' / '*'),    'dmccodegui/assets/images'),
        # Noto Sans fonts — only the 4 used variants
        (str(SRC / 'dmccodegui' / 'assets' / 'fonts' / 'Noto_Sans' / 'static' / 'NotoSans-Regular.ttf'),
             'dmccodegui/assets/fonts/Noto_Sans/static'),
        (str(SRC / 'dmccodegui' / 'assets' / 'fonts' / 'Noto_Sans' / 'static' / 'NotoSans-Bold.ttf'),
             'dmccodegui/assets/fonts/Noto_Sans/static'),
        (str(SRC / 'dmccodegui' / 'assets' / 'fonts' / 'Noto_Sans' / 'static' / 'NotoSans-Italic.ttf'),
             'dmccodegui/assets/fonts/Noto_Sans/static'),
        (str(SRC / 'dmccodegui' / 'assets' / 'fonts' / 'Noto_Sans' / 'static' / 'NotoSans-BoldItalic.ttf'),
             'dmccodegui/assets/fonts/Noto_Sans/static'),
    ],
    hookspath=hookspath(),
    runtime_hooks=runtime_hooks(),
    **_analysis_kwargs,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BinhAnHMI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    icon=str(REPO_ROOT / 'deploy' / 'windows' / 'BinhAnHMI.ico'),
    version=str(REPO_ROOT / 'deploy' / 'windows' / 'version_file.txt'),
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins + angle.dep_bins)],
    strip=False,
    upx=False,
    name='BinhAnHMI',
)
