# Brave Workspace Manager

![Linux Mint](https://img.shields.io/badge/sistema-Linux%20Mint%20%2F%20Cinnamon-c70000)
![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)

Administrador de **perfiles nativos de Brave** para Linux Mint / Cinnamon.

Orquesta los perfiles que ya tienes en Brave (los que aparecen en
`brave://settings/manageProfile`) desde una unica ventana: galeria de perfiles,
panel de ventanas, atajos globales, bandeja del sistema y personalizacion
(nombre visible, color, icono y favorito) **sin modificar jamas los datos
internos de Brave**.

![Captura de la ventana principal](docs/images/ventana-principal.png)

---

## Indice

- [Que hace](#que-hace)
- [Requisitos](#requisitos)
- [Instalacion](#instalacion)
- [Uso](#uso)
- [Como se asocia cada ventana con su perfil](#como-se-asociada-cada-ventana-con-su-perfil)
- [Como se cuentan las pestanas abiertas](#como-se-cuentan-las-pestanas-abiertas)
- [Atajos de teclado](#atajos-de-teclado)
- [Reglas de seguridad](#reglas-de-seguridad)
- [Donde guarda los datos](#donde-guarda-los-datos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Desarrollo y pruebas](#desarrollo-y-pruebas)
- [Licencia](#licencia)

---

## Que hace

- **Descubre** los perfiles nativos de Brave leyendo `Local State` y las carpetas
  del directorio de datos. Solo lectura: nunca escribe en ellos.
- **Muestra una galeria de perfiles** que se reorganiza sola segun el tamano de
  la ventana, con el estado de cada uno (abierto o cerrado), su avatar y su
  color, y un resumen fijo a la izquierda con los contadores.
- **Activa un perfil** con un clic: trae al frente su ventana si la conoce, o
  la abre en su directorio nativo (`--profile-directory=Default`) si no.
- **Gestiona las ventanas** de Brave: activar, minimizar, restaurar y asignar
  manualmente una ventana a un perfil.
- **Cuenta las pestanas abiertas** de cada ventana y de cada perfil, y muestra
  cuales son y cual esta en primer plano.
- **Aprende** la correspondencia ventana-perfil con el uso, de modo que las
  asignaciones se repiten cada vez que se lanzan los perfiles desde la app.
- **Personaliza** cada perfil con un nombre visible, color, icono y marca de
  favorito.
- **Atajos globales** (`Ctrl+Alt+1`…`9`, `Ctrl+Alt+Tab`, `Ctrl+Alt+B`) y
  bandeja del sistema con acceso rapido.
- **Instalable** como aplicacion de escritorio (`packaging/*.desktop`),
  servicio de systemd de usuario y script de arranque automatico.

## Requisitos

| Requisito | Detalle |
|---|---|
| Sistema | Linux con sesion **X11** (probado en Linux Mint 22.3 / Cinnamon) |
| Navegador | Brave instalado (`brave-browser` en el `PATH` o `/opt/brave.com/brave/brave`) |
| Python | 3.10 o superior |
| Dependencias | `PySide6` (interfaz) y `python-xlib` (protocolo X11, sin dependencias del sistema) |
| Opcional | `python3-gi` (PyGObject) para leer las pestanas por AT-SPI; sin el, la app funciona igual pero solo muestra la pestana activa |

> En Wayland la gestion de ventanas no es posible de forma fiable, por lo que la
> aplicacion funciona en modo degradado: descubre perfiles y los abre, pero no
> puede enumerar ni activar ventanas. La barra de estado indica el backend
> activo (`x11`, `wmctrl` o `none`).

## Instalacion

```bash
git clone https://github.com/jaaparenas/brave-workspace-manager.git
cd brave-workspace-manager
./setup.sh
```

`setup.sh` crea un entorno virtual en `.venv`, instala las dependencias y
genera el lanzador `brave-workspace-manager` en `~/.local/bin`.

Instalacion manual, si prefieres no usar el script:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m brave_workspace_manager
```

## Uso

```bash
./run.sh                       # lanza la aplicacion
brave-workspace-manager        # si la instalaste con setup.sh
brave-workspace-manager --minimized          # arranca en la bandeja
brave-workspace-manager --user-data-dir /ruta/alternativa   # otro directorio de datos
brave-workspace-manager --version
```

La ventana principal tiene cuatro zonas:

1. **Galeria de perfiles**: las fichas se reacomodan solas al cambiar el ancho
   de la ventana y el conjunto queda centrado. Un clic selecciona el perfil,
   doble clic lo abre y el menu contextual da acceso a las acciones rapidas.
   A la izquierda, el **resumen** permanece siempre visible con el numero de
   perfiles, los abiertos, los favoritos, las ventanas de Brave detectadas, las
   pestanas abiertas y el perfil activo.
2. **Panel de ventanas**: las ventanas de Brave asociadas al perfil
   seleccionado, con acciones de activar, minimizar y restaurar, y el numero de
   pestanas de cada una.
3. **Ventanas sin asignar**: las ventanas que Chromium no permite identificar
   de forma automatica; se pueden asignar a mano con el desplegable o con el
   boton **Tomar la ventana activa**.
4. **Administrador** (`Ctrl+Alt+B`): tabla de perfiles, personalizacion,
   atajos y ajustes (intervalo de actualizacion, bandeja, inicio automatico).

## Como se asocia cada ventana con su perfil

Este es el punto tecnico mas delicado del proyecto, asi que conviene explicarlo
con honestidad.

**Chromium no expone que perfil pertenece a cada ventana.** No hay propiedad
X11, ni variable de entorno, ni fichero en disco que lo indique: todas las
ventanas de todos los perfiles de un mismo `user-data-dir` comparten un unico
proceso del navegador, de modo que el PID de una ventana no identifica su
perfil. La aplicacion no lo inventa: usa una cascada de reglas, de la mas
fiable a la menos, y **dice con que confianza resolvio cada caso**.

| Orden | Regla | Confianza | Como funciona |
|---|---|---|---|
| 1 | Asignacion aprendida | 100 % | Se guarda en la base de datos local cuando la app lanza un perfil o cuando el usuario asigna una ventana a mano. |
| 2 | Perfil unico abierto | 90 % | Si solo hay un perfil abierto, todas las ventanas de Brave son suyas. |
| 3 | Titulo de la ventana | 60 % | Si el nombre del perfil aparece como palabra completa en el titulo (`Work · Panel de control`). |
| 4 | Eliminacion | 50 % | Si queda una sola ventana sin asignar y un solo perfil abierto sin ventanas, ambos se corresponden. |
| 5 | Sin asignar | 0 % | Se muestra en el apartado **Ventanas sin asignar** para que la resuelvas tu. |

Los perfiles **abiertos** si se detectan de forma fiable: el proceso del
navegador mantiene ficheros abiertos dentro de la carpeta del perfil, y se
inspeccionan sus descriptores (`/proc/<pid>/fd`).

Las asignaciones aprendidas se conservan por PID de navegador y por
identificador de ventana, de modo que se reutilizan en sesiones posteriores.

## Como se cuentan las pestanas abiertas

Chromium no expone por X11/EWMH quantas pestanas tiene una ventana: por ese
protocolo solo se ve el titulo de la ventana, que es el de la pestana activa.
La unica via local que no toca los datos del navegador es el **arbol de
accesibilidad** (AT-SPI), el mismo que usa un lector de pantalla.

- La aplicacion ejecuta `brave_workspace_manager/a11y_helper.py` en un proceso
  aparte (el entorno virtual puede no tener PyGObject) y recibe un JSON con las
  ventanas y sus pestanas.
- Chromium solo publica su interfaz, y con ella la barra de pestanas, cuando se
  abre con `--force-renderer-accessibility`. Por eso el lanzador anade ese flag a
  los perfiles que abre la aplicacion. Si Brave ya estaba en marcha, hay que
  cerrarlo del todo y volver a abrir un perfil desde la app; mientras tanto la
  ventana avisa de que solo se ve la pestana activa.
- Cada ventana de Brave muestra un boton con el numero de pestanas; al
  desplegarlo aparece la lista de titulos, con la pestana activa marcada.
- El resumen de la izquierda cuenta las pestanas abiertas de todos los perfiles.

Solo se leen los **titulos** de las pestanas, y solo en memoria: no se guardan
en disco ni se envian a ninguna parte. La opcion **Listar las pestanas
abiertas** del panel de administrador desactiva la lectura y deja de anadir el
flag al navegador.

## Atajos de teclado

| Atajo | Accion |
|---|---|
| `Ctrl+Alt+1` … `Ctrl+Alt+9` | Activar el perfil N |
| `Ctrl+Alt+Tab` | Perfil siguiente |
| `Ctrl+Alt+Shift+Tab` | Perfil anterior |
| `Ctrl+Alt+B` | Mostrar u ocultar el administrador |

Todos son configurables en el panel de administrador. Los atajos globales se
registran mediante capturas pasivas de teclado en la ventana raiz de X11; si
otra aplicacion ya usa la combinacion, la aplicacion avisa y desactiva ese
atajo en lugar de fallar.

## Reglas de seguridad

La aplicacion **solo lee** el directorio de datos de Brave:

- No modifica `Local State` ni ninguna base de datos interna de los perfiles.
- No copia, lee ni descifra cookies, contraseñas, historial o sesiones.
- No intercepta trafico HTTPS ni instala certificados.
- No modifica la configuracion de Brave; crear perfiles se delega en el gestor
  de perfiles nativo (`brave://settings/manageProfile`).
- Todo lo que la aplicacion guarda (preferencias de la app, asignaciones
  aprendidas) vive en `~/.local/share/brave-workspace-manager/`.

Lo unico que se lee fuera de ese directorio son los **titulos de las pestanas**
que el navegador publica por AT-SPI cuando se abre con el modo de
accesibilidad activado. No se leen URLs, ni cookies, ni el historial, y esos
titulos no se guardan en ningun sitio.

## Donde guarda los datos

| Que | Donde |
|---|---|
| Base de datos local (SQLite) | `~/.local/share/brave-workspace-manager/workspace.db` |
| Registro | `~/.local/state/brave-workspace-manager/` |
| Configuracion | `~/.config/brave-workspace-manager/` |
| Inicio automatico | `~/.config/autostart/brave-workspace-manager.desktop` |

Todo lo anterior se puede borrar sin tocar los datos de Brave.

## Estructura del proyecto

```
brave_workspace_manager/
├── config.py            rutas, deteccion del escritorio, binarios de Brave
├── models.py            perfiles, ventanas y metodos de asociacion
├── discovery.py         lectura de Local State y carpetas de perfil
├── processes.py         inspeccion de /proc y perfiles abiertos
├── database.py          persistencia SQLite
├── a11y_helper.py       lectura de pestanas por AT-SPI (script autonomo)
├── tabs.py              cliente del ayudante y emparejamiento con las ventanas
├── core/
│   ├── controller.py    estado de la aplicacion y acciones
│   ├── resolver.py      cascada de reglas ventana -> perfil
│   ├── launcher.py      apertura de perfiles con el directorio nativo
│   └── autostart.py     fichero .desktop de inicio automatico
├── x11/
│   ├── backend.py       protocolo EWMH con python-xlib
│   ├── wmctrl_backend.py  alternativa mediante la CLI de wmctrl
│   ├── grab.py          capturas de teclado para atajos globales
│   └── base.py          interfaz comun de backends
└── ui/                  interfaz PySide6 (galeria, paneles, bandeja, tema)
```

Mas detalle en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) y la especificacion
original en [docs/SPECIFICATION.md](docs/SPECIFICATION.md).

## Desarrollo y pruebas

```bash
.venv/bin/python -m pytest -q        # 95 pruebas, sin necesidad de navegador abierto
.venv/bin/python -m pytest --cov     # con cobertura
```

Las pruebas no tocan los datos reales de Brave: construyen un directorio de
datos sintetico en un temporal.

Generar las capturas de la documentacion:

```bash
.venv/bin/python tools/screenshot.py
```

## Licencia

MIT. Consulta [LICENSE](LICENSE).
