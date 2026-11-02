#!/usr/bin/env bash
# Instalacion de Brave Workspace Manager en un entorno virtual local.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$RAIZ/.venv"
BIN_DIR="${HOME}/.local/bin"

usage() {
    cat <<'EOF'
Uso: ./setup.sh [--desktop]

  --desktop   Instala tambien la entrada de menu (fichero .desktop)
EOF
}

INSTALAR_DESKTOP=0
for arg in "$@"; do
    case "$arg" in
        --desktop) INSTALAR_DESKTOP=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Opcion desconocida: $arg" >&2; usage; exit 2 ;;
    esac
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: no se encuentra python3 en el PATH." >&2
    exit 1
fi

VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Python detectado: $VERSION"
else
    echo "ERROR: se necesita Python 3.10 o superior (se ha detectado $VERSION)." >&2
    exit 1
fi

if [ ! -d "$VENV" ]; then
    echo "Creando el entorno virtual en $VENV"
    python3 -m venv "$VENV"
fi

echo "Instalando dependencias"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -r "$RAIZ/requirements.txt"

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/brave-workspace-manager" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" -m brave_workspace_manager "\$@"
EOF
chmod +x "$BIN_DIR/brave-workspace-manager"
echo "Lanzador instalado en $BIN_DIR/brave-workspace-manager"

if [ "$INSTALAR_DESKTOP" = "1" ]; then
    DESTINO="${XDG_CONFIG_HOME:-$HOME/.config}/applications/brave-workspace-manager.desktop"
    mkdir -p "$(dirname "$DESTINO")"
    sed "s|@PYTHON@|$VENV/bin/python|g" \
        "$RAIZ/packaging/brave-workspace-manager.desktop" > "$DESTINO"
    chmod +x "$DESTINO"
    echo "Entrada de menu instalada en $DESTINO"
fi

echo
echo "Instalacion completada. Arranca la aplicacion con:"
echo "  $RAIZ/run.sh"
