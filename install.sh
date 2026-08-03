#!/usr/bin/env bash
# Tidy — one-command installer
#   bash install.sh            → desktop laptop (systemd --user)
#   bash install.sh --server   → headless VPS 24/7 (systemd system)
set -euo pipefail

APP="tidy"
REPO_URL="https://github.com/Twarga/Tidy.git"
MODE="desktop"
[[ "${1:-}" == "--server" ]] && MODE="server"

echo "▸ Installing Tidy ($MODE mode)"
command -v python3 >/dev/null || { echo "✗ python3 required"; exit 1; }
command -v git >/dev/null || { echo "✗ git required"; exit 1; }

INSTALL_DIR="${TIDY_HOME:-$HOME/.local/share/tidy}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# clone or update
if [ ! -d .git ]; then
  git clone --depth 1 "$REPO_URL" . || true
else
  git pull --ff-only || true
fi

# venv + deps
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e "$INSTALL_DIR[gui,tui,mcp,scheduler]"

# link binaries
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
ln -sf "$INSTALL_DIR/.venv/bin/tidy" "$BIN/tidy"
ln -sf "$INSTALL_DIR/.venv/bin/tidy-gui" "$BIN/tidy-gui" 2>/dev/null || true
ln -sf "$INSTALL_DIR/.venv/bin/tidy-mcp" "$BIN/tidy-mcp" 2>/dev/null || true
export PATH="$BIN:$PATH"

# systemd service
if [ "$MODE" == "server" ]; then
  UNIT_DIR="/etc/systemd/system"
  echo "▸ installing system service (root required)"
  sudo tee "$UNIT_DIR/tidy.service" >/dev/null <<EOF
[Unit]
Description=Tidy backup & sync daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$BIN/tidy serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now tidy
  echo "✔ Tidy server running 24/7 (sudo systemctl status tidy)"
else
  UNIT_DIR="$HOME/.config/systemd/user"
  mkdir -p "$UNIT_DIR"
  cat > "$UNIT_DIR/tidy.service" <<EOF
[Unit]
Description=Tidy backup & sync daemon

[Service]
Type=simple
ExecStart=$BIN/tidy serve
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable tidy
  systemctl --user start tidy || true
  echo "✔ Tidy running in background (systemctl --user status tidy)"
fi

echo "✔ Done. Try:  tidy status   |   tidy-gui"
