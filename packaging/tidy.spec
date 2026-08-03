# tidy.spec — PyInstaller spec for the Tidy AppImage binary.
# Build: .venv-build/bin/pyinstaller packaging/tidy.spec (from the repo root)
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())

# Ship the web UI + pixel fonts + everything else inside the tidy package.
datas = collect_data_files("tidy")

hiddenimports = [
    "gi",
    "gi.repository.Gtk",
    "gi.repository.Gdk",
    "gi.repository.GdkPixbuf",
    "gi.repository.GLib",
    "gi.repository.GObject",
    "gi.repository.Gio",
    "gi.repository.Soup",
    "gi.repository.WebKit2",
    "webview",
    "pystray",
    "PIL",
    "apscheduler",
    "textual",
    "rich",
    "fastmcp",
    "tidy.mcp",
    "tidy.gui.main",
    "tidy.gui.tray",
    "tidy.gui.api",
    "tidy.gui.themes",
    "tidy.daemon",
    "tidy.scheduler",
    "tidy.notify",
]
hiddenimports += collect_submodules("tidy")

a = Analysis(
    [os.path.join(SPECPATH, "entry_cli.py")],
    pathex=[ROOT, os.path.join(ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "tkinter", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="tidy",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(exe, a.binaries, a.datas, name="tidy")
