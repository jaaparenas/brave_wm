#!/usr/bin/env bash
# Installs Brave Workspace Manager in a local virtual environment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
BIN_DIR="${HOME}/.local/bin"

usage() {
    cat <<'EOF'
Usage: ./setup.sh [--desktop]

  --desktop   Also install the menu entry (.desktop file)
EOF
}

INSTALL_DESKTOP=0
for arg in "$@"; do
    case "$arg" in
        --desktop) INSTALL_DESKTOP=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
    esac
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found in the PATH." >&2
    exit 1
fi

VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Python found: $VERSION"
else
    echo "ERROR: Python 3.10 or newer is required (found $VERSION)." >&2
    exit 1
fi

if [ ! -d "$VENV" ]; then
    echo "Creating the virtual environment in $VENV"
    python3 -m venv "$VENV"
fi

echo "Installing dependencies"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/brave-workspace-manager" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" -m brave_workspace_manager "\$@"
EOF
chmod +x "$BIN_DIR/brave-workspace-manager"
echo "Launcher installed in $BIN_DIR/brave-workspace-manager"

if [ "$INSTALL_DESKTOP" = "1" ]; then
    TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/applications/brave-workspace-manager.desktop"
    mkdir -p "$(dirname "$TARGET")"
    sed "s|@PYTHON@|$VENV/bin/python|g" \
        "$ROOT/packaging/brave-workspace-manager.desktop" > "$TARGET"
    chmod +x "$TARGET"
    echo "Menu entry installed in $TARGET"
fi

echo
echo "Installation complete. Start the application with:"
echo "  $ROOT/run.sh"
