#!/usr/bin/env bash
# Removes what install.sh installed. Your data (profile customisation, images)
# is kept unless --purge is given.
set -euo pipefail

APP_ID="brave-workspace-manager"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
INSTALL_DIR="$HOME/.local/lib/$APP_ID"
RUNNING_PATTERN="-m brave_workspace_manager|bin/$APP_ID( |$)"

PURGE=0
for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=1 ;;
        -h|--help)
            echo "Usage: ./uninstall.sh [--purge]"
            echo "  --purge   Also delete your data (profile names, colours, images, settings)"
            exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

RUNNING="$(pgrep -u "$(id -u)" -f -- "$RUNNING_PATTERN" || true)"
if [ -n "$RUNNING" ]; then
    echo "Stopping Brave Workspace Manager"
    # shellcheck disable=SC2086
    kill -TERM $RUNNING 2>/dev/null || true
    sleep 1
fi

remove() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        rm -rf -- "$1"
        echo "Removed $1"
    fi
}

remove "$CONFIG_HOME/autostart/$APP_ID.desktop"
remove "$DATA_HOME/applications/$APP_ID.desktop"
remove "$HOME/.local/bin/$APP_ID"
for size in 32 48 64 128 256; do
    remove "$DATA_HOME/icons/hicolor/${size}x${size}/apps/$APP_ID.png"
done
remove "$INSTALL_DIR"

if [ "$PURGE" = "1" ]; then
    remove "$DATA_HOME/$APP_ID"
    remove "$CONFIG_HOME/$APP_ID"
    remove "$STATE_HOME/$APP_ID"
else
    echo "Your data was kept in $DATA_HOME/$APP_ID (use --purge to delete it)."
fi
echo "Brave Workspace Manager was uninstalled. Brave and its profiles were not touched."
