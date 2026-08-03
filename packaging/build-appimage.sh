#!/usr/bin/env bash
# build-appimage.sh — package Tidy into a portable AppImage.
#
#   .venv-build  (created if missing) hosts PyInstaller + the app extras.
#   PyInstaller → one binary (CLI/TUI/GUI/MCP) → AppDir → appimagetool.
#
# Requires: python3, git; internet for appimagetool first run.
# Output:   $ROOT/tidy-<version>-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NAME="tidy"
BUILD_VENV="$ROOT/.venv-build"
PY="$BUILD_VENV/bin/python"
VERSION="$("$PY" -c "from tidy import __version__; print(__version__)")"
OUT="$ROOT/${NAME}-${VERSION}-x86_64.AppImage"
DIST="$ROOT/dist-appimage"
APP_DIR="$ROOT/AppDir"
TOOLS="$ROOT/packaging/.tools"
APPIMAGE_TOOL="$TOOLS/appimagetool.AppImage"

say() { printf "▸ %s\n" "$1"; }
ok()  { printf "✔ %s\n" "$1"; }

# ---- 1) build venv ----
if [ ! -x "$PY" ]; then
  say "creating build venv (system-site-packages for PyGObject)…"
  python3 -m venv --system-site-packages "$BUILD_VENV"
  "$PY" -m pip install --quiet --upgrade pip
fi
"$PY" -m pip install --quiet -e "$ROOT[gui,tui,mcp,scheduler]" pyinstaller

# ---- 2. appimagetool ----
if [ ! -x "$APPIMAGE_TOOL" ]; then
  say "downloading appimagetool…"
  mkdir -p "$TOOLS"
  curl -fL -o "$APPIMAGE_TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$APPIMAGE_TOOL"
fi

# ---- 3. PyInstaller ----
say "building with PyInstaller…"
rm -rf "$DIST" "$ROOT/build-appimage"
"$PY" -m PyInstaller packaging/tidy.spec --noconfirm --clean \
  --distpath "$DIST" --workpath "$ROOT/build-appimage"

# ---- 4. assemble AppDir ----
say "assembling AppDir…"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"/{usr/bin,usr/lib/girepository-1.0,usr/share/applications,usr/share/icons/hicolor/256x256/apps}
cp -r "$DIST/$NAME" "$APP_DIR/usr/bin/tidy"

# bundle the GTK/WebKit typelibs so gi resolves the GUI stack from the AppDir
for t in /usr/lib*/girepository-1.0/*.typelib; do
  cp "$t" "$APP_DIR/usr/lib/girepository-1.0/"
done

# pixel-folder icon
"$PY" - "$APP_DIR/usr/share/icons/hicolor/256x256/apps/tidy.png" <<'PYEOF'
import sys
from PIL import Image, ImageDraw
path = sys.argv[1]
s = 256
img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# body (blocky)
d.rectangle([24, 76, s - 24, s - 32], fill=(19, 39, 22, 255), outline=(46, 212, 138, 255), width=10)
# folder tab
d.polygon([(24, 76), (104, 76), (128, 108), (s - 24, 108), (s - 24, 76), (s - 24, 76)], fill=(46, 212, 138, 255))
d.rectangle([s - 76, 76, s - 24, 108], fill=(46, 212, 138, 255))
# two white "files"
d.rectangle([70, 122, 118, 200], fill=(246, 242, 255, 255))
d.rectangle([134, 122, 182, 200], fill=(246, 242, 255, 255))
img.save(path)
PYEOF

# AppRun
cat > "$APP_DIR/AppRun" <<EOF
#!/bin/sh
# Tidy AppImage launcher
SELF=\$(readlink -f "\$0")
APPDIR=\$(dirname "\$SELF")
export GI_TYPELIB_PATH="\$APPDIR/usr/lib/girepository-1.0\${GI_TYPELIB_PATH:+:}\$GI_TYPELIB_PATH"
export LD_LIBRARY_PATH="\$APPDIR/usr/lib\${LD_LIBRARY_PATH:+:}\$LD_LIBRARY_PATH"
exec "\$APPDIR/usr/bin/tidy/tidy" "\$@"
EOF
chmod +x "$APP_DIR/AppRun"

cat > "$APP_DIR/tidy.desktop" <<EOF
[Desktop Entry]
Name=Tidy
Comment=Pixel backup & sync
Exec=tidy gui
Icon=tidy
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=false
EOF
cp "$APP_DIR/tidy.desktop" "$APP_DIR/usr/share/applications/"
cp "$APP_DIR/usr/share/icons/hicolor/256x256/apps/tidy.png" "$APP_DIR/tidy.png"

# ---- 5. appimagetool ----
say "packaging AppImage…"
cd "$APP_DIR"
# FUSE-less run if the tool can't self-mount
export APPIMAGE_EXTRACT_AND_RUN=1
"$APPIMAGE_TOOL" "$APP_DIR" "$OUT" >/dev/null
chmod +x "$OUT"
cd "$ROOT"

ok "built $OUT"
echo
echo "  verify:  ./$OUT --version"
echo "  see GUI: ./$OUT gui   (needs system webkit2gtk on the host)"