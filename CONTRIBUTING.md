# Como contribuir

Gracias por el interes. El proyecto es pequeno y todas las decisiones tecnicas
estan documentadas, asi que deberia ser facil llegar a la misma conclusion que
el equipo.

## Puesta en marcha

```bash
git clone https://github.com/jaaparenas/brave-workspace-manager.git
cd brave-workspace-manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest pytest-cov ruff
```

## Ejecutar las pruebas

```bash
.venv/bin/python -m pytest -q
```

Las pruebas **no tocan los datos reales de Brave**: construyen un directorio de
datos sintetico en un directorio temporal. Se puede comprobar el efecto de
cambios en la resolucion, el descubrimiento, la persistencia, el launcher y los
procesos sin abrir el navegador.

Para ejecutarlas con cobertura:

```bash
.venv/bin/python -m pytest --cov=brave_workspace_manager --cov-report=term-missing
```

## Estilo del codigo

- Python 3.10+, anotaciones de tipo donde aporten claridad.
- `ruff check` y `ruff format --check` deben pasar sin avisos.
- Los modulos de bajo nivel (`config`, `discovery`, `processes`, `database`,
  `core/*`, `x11/*`) **no importan PySide6**: la interfaz es una capa superior.
- Comentarios solo cuando el codigo no se explica por si mismo; en particular,
  hay que explicar *por que* se hace algo cuando Chromium o X11 obracon de
  forma contraintuitiva.
- Los textos de la interfaz estan en español.

## Reglas que no se negocian

1. **Nunca** se escribe en el directorio de datos de Brave (`Local State`,
   bases de datos de los perfiles, etc.). Solo lectura.
2. **Nunca** se tocan cookies, contrasenas, historial ni URLs.
3. **Nunca** se intercepta trafico HTTPS.
4. Los perfiles se abren con su directorio nativo
   (`--profile-directory=<carpeta>`), sin inventar instancias paralelas.

## Como enviar un cambio

1. Crea una rama: `git checkout -b feature/mi-cambio`.
2. Anade o ajusta pruebas para el comportamiento nuevo.
3. Ejecuta `pytest` y `ruff`.
4. Abre un *pull request* describiendo **que** cambia y **por que**.
5. Si el cambio afecta a la asociacion de ventanas con perfiles, explica que
   evidencia has obtenido en tu sistema (sesion, version de Brave, numero de
   perfiles abiertos). Esa parte es la mas delicada del proyecto y las
   afirmaciones sin evidencia no se pueden revisar.

## Reportar errores

Usa la plantilla de `.github/ISSUE_TEMPLATE/bug_report.yml`. Es muy util
incluir la salida de la terminal de la aplicacion y el backend activo (aparece
en la barra de estado: `x11`, `wmctrl` o `none`).

## Alcance de las contribuciones

Areas donde las gracias son bienvenidas:

- Compatibilidad con otros gestores de ventanas de X11 y con Wayland.
- Mejoras en la asociacion ventana-perfil (por ejemplo, seguir el cambio de
  foco del usuario para aprender asignaciones).
- Previsualizacion y organizacion de ventanas multiples por perfil.
- Traduccion de la interfaz a otros idiomas.

Consulta `docs/ARCHITECTURE.md` para el detalle tecnico y `docs/SPECIFICATION.md`
para los requisitos originales.
