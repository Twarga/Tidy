#!/usr/bin/env bash
# Tidy — one-command installer
#   bash install.sh                  → desktop laptop (systemd --user)
#   bash install.sh --server         → headless VPS 24/7 (systemd system)
#   bash install.sh --mcp            → also register the MCP server with Claude Desktop
#   bash install.sh --no-service     → install only (no systemd) — handy for containers/tests
#
# Idempotent: safe to re-run; it updates the code, keeps the venv healthy,
# re-links binaries and re-applies the service.
set -euo pipefail

APP="tidy"
REPO_URL="https://github.com/Twarga/Tidy.git"
MODE="desktop"
MCP_REGISTER=0
NO_SERVICE=0

for arg in "$@"; do
  case "$arg" in
    --server)     MODE="server" ;;
    --mcp)        MCP_REGISTER=1 ;;
    --no-service) NO_SERVICE=1 ;;
    -h|--help)
      echo "usage: bash install.sh [--server] [--mcp] [--no-service]"
      exit 0 ;;
    *) echo "✗ unknown argument: $arg" >&2; exit 1 ;;
  esac
done

say() { printf "▸ %s\n" "$1"; }
ok()  { printf "✔ %s\n" "$1"; }

command -v python3 >/dev/null || { echo "✗ python3 required"; exit 1; }
command -v git >/dev/null || { echo "✗ git required"; exit 1; }
if [ "$MODE" == "server" ] && [ "$NO_SERVICE" != "1" ]; then
  command -v sudo >/dev/null || { echo "✗ sudo required for --server"; exit 1; }
fi

say "Installing Tidy ($MODE mode)"
INSTALL_DIR="${TIDY_HOME:-$HOME/.local/share/tidy}"
VENV="$INSTALL_DIR/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
BIN="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR" "$BIN"
cd "$INSTALL_DIR"

# ---- code: clone or update ----
if [ ! -d .git ]; then
  say "cloning Tidy…"
  git clone --depth 1 "$REPO_URL" .
else
  say "updating Tidy…"
  git pull --ff-only --quiet || true   # local edits survive; just try
fi

# ---- venv: GUI needs system PyGObject/webkit, so enable system-site-packages ----
if [ ! -x "$PY" ]; then
  say "creating venv (system-site-packages for PyGObject/webkit)…"
  python3 -m venv --system-site-packages "$VENV"
fi
# canary: if gi (PyGObject) isn't importable the GUI can't launch — rebuild
if ! "$PY" -c "import gi" >/dev/null 2>&1; then
  say "rebuilding venv with system packages (PyGObject missing)…"
  rm -rf "$VENV"
  python3 -m venv --system-site-packages "$VENV"
fi

say "installing dependencies…"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -e "$INSTALL_DIR[gui,tui,mcp,scheduler]"
if ! "$PY" -c "import gi" >/dev/null 2>&1; then
  echo "⚠ PyGObject (gi) not found — desktop GUI needs it: dnf install python3-gobject webkit2gtk4.1 (or apt: gir1.2-webkit2-4.1 python3-gi). CLI/TUI/daemon work fine without it."
fi
ok "dependencies ready"

# ---- binaries ----
ln -sf "$VENV/bin/tidy" "$BIN/tidy"
ln -sf "$VENV/bin/tidy-gui" "$BIN/tidy-gui" 2>/dev/null || true
ln -sf "$VENV/bin/tidy-mcp" "$BIN/tidy-mcp" 2>/dev/null || true
export PATH="$BIN:$PATH"
ok "binaries linked in $BIN"

# ---- MCP auto-register (Claude Desktop) ----
if [ "$MCP_REGISTER" == "1" ]; then
  CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.config/Claude}"
  mkdir -p "$CONFIG_DIR"
  "$PY" - "$CONFIG_DIR/claude_desktop_config.json" "$BIN/tidy-mcp" <<'PYEOF'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
command = sys.argv[2]
cfg = {}
if path.exists():
    try:
        cfg = json.loads(path.read_text())
    except Exception:
        cfg = {}
servers = cfg.setdefault("mcpServers", {})
servers["tidy"] = {"command": command, "args": []}
path.write_text(json.dumps(cfg, indent=2) + "\n")
print("  wrote", path)
PYEOF
  ok "MCP server registered with Claude Desktop (restart Claude to pick it up)"
fi

# ---- systemd service ----
if [ "$NO_SERVICE" != "1" ]; then
  if [ "$MODE" == "server" ]; then
    say "installing system service (root required)…"
    sudo tee /etc/systemd/system/tidy.service >/dev/null <<EOF
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
    sudo systemctl enable tidy
    sudo systemctl restart tidy
    ok "Tidy server running 24/7 → sudo systemctl status tidy"
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
    systemctl --user restart tidy || true
    ok "Tidy running in background → systemctl --user status tidy"
  fi
fi

echo
echo "✔ Done!"
echo "   tidy status          → see your repos"
echo "   tidy-gui             → desktop app"
echo "   tidy tui             → terminal UI"
if [ "$MCP_REGISTER" != "1" ]; then
  echo "   bash install.sh --mcp → enable Claude Desktop integration"
fi
