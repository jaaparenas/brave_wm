#!/usr/bin/env bash
# Starts Brave Workspace Manager from the repository.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "The virtual environment does not exist. Run ./setup.sh first" >&2
    exit 1
fi

cd "$ROOT"
exec "$VENV/bin/python" -m brave_workspace_manager "$@"
