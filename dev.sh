#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  dev.sh — Tidy dev launcher
#  Boots the venv, installs extras, checks your session, and lets
#  you fire up the GUI, TUI, 24/7 daemon, or a raw shell.
#  Usage:   ./dev.sh            → pretty menu
#           ./dev.sh gui        → straight to desktop GUI
#           ./dev.sh tui serve status … → any tidy subcommand
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
TIDYBIN="$VENV/bin/tidy"

# ── palette ────────────────────────────────────────────────────
RESET=$'\033[0m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
GREEN=$'\033[38;5;47m'
PINK=$'\033[38;5;207m'
CYAN=$'\033[38;5;14m'
YELLOW=$'\033[38;5;11m'
RED=$'\033[38;5;196m'
DIMGRAY=$'\033[38;5;244m'

cursor_off() { printf '\033[?25l'; }
cursor_on()  { printf '\033[?25h'; }
trap cursor_on EXIT
cursor_off

step() { printf "${CYAN}  ›${RESET} ${BOLD}%s${RESET}\n" "$1"; }
ok()   { printf "${GREEN}  ✔ ${RESET}%s\n" "$1"; }
warn() { printf "${YELLOW}  ⚠ ${RESET}%s\n" "$1" >&2; }
fail() { printf "${RED}  ✗ %s${RESET}\n" "$1" >&2; }

# ── spinner while a process runs ───────────────────────────────
spinner() {
  local pid=$1
  local spin="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r  ${PINK}%s${RESET} working…" "${spin:i:1}"
    i=$(( (i+1) % ${#spin} ))
    sleep 0.07
  done
  printf "\r\033[K"
}

# prettify a long-running command (hide scroll, show spinner)
run_pretty() {
  printf "${DIMGRAY}  %s${RESET}\n" "$1"
  shift
  "$@" &
  spinner $!
  wait $!
}

# ───────────────────────────────────────────────────────────────
banner() {
  printf "\n"
  printf "  ${PINK}${BOLD}▓▓${RESET} ${CYAN}${BOLD}T I D Y${RESET} ${PINK}${BOLD}▓▓${RESET}   ${DIMGRAY}pixel backup · sync${RESET}\n"
  printf "  ${DIMGRAY}▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▜${RESET}\n"
  printf "  ${DIMGRAY}▌${RESET}  ${DIM}desktop GUI · TUI · 24/7 daemon · MCP · CLI${RESET} ${DIMGRAY}▐${RESET}\n"
  printf "  ${DIMGRAY}▙▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▟${RESET}\n\n"
}

# ───────────────────────────────────────────────────────────────
env_check() {
  step "checking environment"
  if [ ! -x "$PY" ]; then
    printf "  ${DIMGRAY}  no venv yet — creating (system-site-packages so PyGObject/webkit are visible)…${RESET}\n"
    python3 -m venv --system-site-packages "$VENV"
    ok "venv created"
  fi
  if ! "$PY" -c "import tidy" >/dev/null 2>&1; then
    run_pretty "installing Tidy editable (+ gui, tui, daemon, dev tools)…" \
      "$PIP" install --quiet -e "$ROOT[dev,gui,tui,mcp,scheduler]"
    ok "installed"
  fi
}

# can the desktop GUI run here? (display + pywebview + PyGObject)
gui_ok() {
  GUI_OK=1
  "$PY" -c "import webview" 2>/dev/null || GUI_OK=0
  "$PY" -c "import gi" 2>/dev/null || GUI_OK=0
  { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; } || GUI_OK=0
}

# ───────────────────────────────────────────────────────────────
run_gui() {
  if [ "$GUI_OK" != "1" ]; then
    warn "no display or pywebview/PyGObject missing — desktop GUI can't start here."
    return 1
  fi
  step "launching ${PINK}desktop GUI${RESET}"
  "$PY" -m tidy.gui.main
}

run_tui() {
  step "starting ${PINK}terminal TUI${RESET}"
  "$PY" -m tidy.tui
}

run_daemon() {
  step "starting ${GREEN}24/7 daemon${RESET} (Ctrl-C to stop)"
  "$TIDYBIN" serve
}

shell_drop() {
  step "dropping into a ${GREEN}venv${RESET} shell with tidy on PATH"
  printf "${DIMGRAY}    try: tidy status · tidy add ~/repo --at 18:00 · tidy gui${RESET}\n"
  if [ -f "$VENV/bin/activate" ]; then
    # shellcheck disable=SC1091
    . "$VENV/bin/activate"
  else
    PATH="$VENV/bin:$PATH" bash
  fi
}

status_quick() {
  step "running ${CYAN}tidy status${RESET}"
  "$TIDYBIN" status || true
}

menu() {
  printf "\n"
  printf "  ${CYAN}1${RESET}) ${BOLD}Desktop GUI${RESET}        ${DIMGRAY}pywebview pixel window + tray${RESET}\n"
  printf "  ${CYAN}2${RESET}) ${BOLD}Terminal TUI${RESET}       ${DIMGRAY}full-screen terminal UI${RESET}\n"
  printf "  ${CYAN}3${RESET}) ${BOLD}24/7 Daemon${RESET}        ${DIMGRAY}tidy serve (APScheduler)${RESET}\n"
  printf "  ${CYAN}4${RESET}) ${BOLD}Shell drop${RESET}         ${DIMGRAY}activate venv + tidy on PATH${RESET}\n"
  printf "  ${CYAN}5${RESET}) ${BOLD}Status${RESET}             ${DIMGRAY}quick repo/schedule overview${RESET}\n"
  printf "  ${RED}0${RESET}) ${BOLD}Quit${RESET}\n"
  printf "\n  ${DIM}session:${RESET} %s\n" "$([ "$GUI_OK" = 1 ] && printf "${GREEN}GUI-ready${RESET}" || printf "${YELLOW}headless (GUI off)${RESET}")"
  printf "\n  ${DIM}// pick ›${RESET} "
  read -r ch
  case "$ch" in
    1) run_gui ;;
    2) run_tui ;;
    3) run_daemon ;;
    4) shell_drop ;;
    5) status_quick ;;
    0|q|Q) exit 0 ;;
    *) warn "not a choice" ;;
  esac
}

# ───────────────────────────────────────────────────────────────
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,7p' "$0"
  exit 0
fi

banner
env_check
gui_ok

if [ "$#" -ge 1 ]; then
  case "$1" in
    gui)            run_gui ;;
    tui)            run_tui ;;
    serve|daemon)   run_daemon ;;
    shell)          shell_drop ;;
    *)              step "running ${GREEN}tidy $*${RESET}"
                    "$TIDYBIN" "$@" ;;
  esac
else
  while true; do
    menu
    printf "\n  ${DIM}returned to launcher — pick another mode, or q to exit.${RESET}\n"
  done
fi
