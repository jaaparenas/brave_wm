#!/usr/bin/env bash
# Arranca Brave Workspace Manager desde el repositorio.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$RAIZ/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "No existe el entorno virtual. Ejecuta primero ./setup.sh" >&2
    exit 1
fi

cd "$RAIZ"
exec "$VENV/bin/python" -m brave_workspace_manager "$@"
