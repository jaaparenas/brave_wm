#!/usr/bin/env bash
# Installs Brave Workspace Manager for the current user, without sudo.
#
# The application is copied into its own virtual environment, so it keeps
# working if this folder is moved or deleted. Running the script again
# upgrades the installation in place.
set -euo pipefail

APP_ID="brave-workspace-manager"
APP_NAME="Brave Workspace Manager"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
INSTALL_DIR="$HOME/.local/lib/$APP_ID"
VENV="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/$APP_ID"
DESKTOP_FILE="$DATA_HOME/applications/$APP_ID.desktop"
ICON_DIR="$DATA_HOME/icons/hicolor"
RUNNING_PATTERN="-m brave_workspace_manager|bin/$APP_ID( |$)"

AUTOSTART=1
START=1

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

Installs Brave Workspace Manager for the current user and starts it.

  --no-autostart   Do not start the app automatically when you log in
  --no-start       Do not start (or restart) the app after installing
  -h, --help       Show this help

To remove it, run ./uninstall.sh
EOF
}

for arg in "$@"; do
    case "$arg" in
        --no-autostart) AUTOSTART=0 ;;
        --no-start) START=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
    esac
done

step() { printf '\n==> %s\n' "$1"; }
warn() { printf 'WARNING: %s\n' "$1" >&2; }

# ------------------------------------------------------------------ checks

step "Checking the system"
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found. Install it with: sudo apt install python3" >&2
    exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "ERROR: Python 3.10 or newer is required." >&2
    exit 1
fi
if ! python3 -c 'import ensurepip, venv' >/dev/null 2>&1; then
    echo "ERROR: the Python venv module is missing. Install it with:" >&2
    echo "  sudo apt install python3-venv" >&2
    exit 1
fi
echo "Python $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])') found"

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    warn "this is a Wayland session; window control needs X11 (Cinnamon on Xorg)."
fi
if ! /usr/bin/python3 -c 'import gi; gi.require_version("Atspi", "2.0")' >/dev/null 2>&1; then
    warn "AT-SPI for Python is missing, so tab counts will not be shown. Install it with:"
    warn "  sudo apt install python3-gi gir1.2-atspi-2.0"
fi
command -v busctl >/dev/null 2>&1 ||
    warn "busctl not found: tabs of a Brave started outside the app may not be listed."
command -v wmctrl >/dev/null 2>&1 ||
    echo "Note: wmctrl is optional (fallback window backend): sudo apt install wmctrl"

# ------------------------------------------------------------- application

step "Installing the application in $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet "$ROOT"
# A reinstall keeps the version number: force the new code in, keep the dependencies.
"$VENV/bin/python" -m pip install --quiet --force-reinstall --no-deps "$ROOT"
VERSION="$("$VENV/bin/python" -c 'from brave_workspace_manager.config import APP_VERSION; print(APP_VERSION)')"
echo "$APP_NAME $VERSION installed"

step "Creating the command $LAUNCHER"
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/$APP_ID" "\$@"
EOF
chmod +x "$LAUNCHER"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "Note: $BIN_DIR is not in your PATH yet; it will be after you log in again." ;;
esac

step "Installing the icon and the menu entry"
QT_QPA_PLATFORM=offscreen "$VENV/bin/python" - "$ICON_DIR" "$APP_ID" <<'EOF'
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from brave_workspace_manager.ui import icons

app = QApplication([])
base, name = Path(sys.argv[1]), sys.argv[2]
for size in (32, 48, 64, 128, 256):
    target = base / f"{size}x{size}" / "apps" / f"{name}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    icons.app_pixmap(size).save(str(target))
EOF
mkdir -p "$(dirname "$DESKTOP_FILE")"
sed -e "s|^Exec=.*|Exec=$LAUNCHER|" -e "s|^TryExec=.*|TryExec=$LAUNCHER|" \
    "$ROOT/packaging/$APP_ID.desktop" > "$DESKTOP_FILE"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname "$DESKTOP_FILE")" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t "$ICON_DIR" >/dev/null 2>&1 || true
fi

if [ "$AUTOSTART" = "1" ]; then
    step "Starting it automatically when you log in (hidden in the tray)"
    BRAVE_WORKSPACE_MANAGER_CMD="$LAUNCHER" "$VENV/bin/python" -c \
        'from brave_workspace_manager.core import autostart; autostart.enable()'
    echo "Autostart entry: $CONFIG_HOME/autostart/$APP_ID.desktop"
fi

# ------------------------------------------------------------------- start

if [ "$START" = "1" ]; then
    step "Starting $APP_NAME"
    RUNNING="$(pgrep -u "$(id -u)" -f -- "$RUNNING_PATTERN" || true)"
    if [ -n "$RUNNING" ]; then
        echo "Stopping the copy that is running"
        # shellcheck disable=SC2086
        kill -TERM $RUNNING 2>/dev/null || true
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            pgrep -u "$(id -u)" -f -- "$RUNNING_PATTERN" >/dev/null || break
            sleep 0.5
        done
    fi
    if [ -n "${DISPLAY:-}" ]; then
        nohup "$LAUNCHER" >/dev/null 2>&1 &
        disown || true
        echo "Started: look for its icon in the system tray."
    else
        echo "No graphical session detected; start it later with: $APP_ID"
    fi
fi

printf '\nDone. %s %s is installed.\n' "$APP_NAME" "$VERSION"
echo "  Open it from the menu, from the tray icon, or by running: $APP_ID"
echo "  Remove it with: $ROOT/uninstall.sh"
