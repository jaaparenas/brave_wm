#!/usr/bin/env bash
# Development setup: a virtual environment in .venv inside the repository.
# To install the app for daily use, run ./install.sh instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

for arg in "$@"; do
    case "$arg" in
        -h|--help) echo "Usage: ./setup.sh   (development environment; see ./install.sh)"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
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
"$VENV/bin/python" -m pip install pytest ruff

echo
echo "Development environment ready. Run the app with:"
echo "  $ROOT/run.sh"
