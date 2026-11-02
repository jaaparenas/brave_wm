# Arquitectura

Documento de diseño de **Brave Workspace Manager**: que hace cada modulo, como
se relacionan entre si y, sobre todo, por que la asociacion entre ventanas y
perfiles funciona como funciona.

## 1. Panorama general

```
                     ┌──────────────────────────────┐
                     │          interfaz             │
                     │  ui/main_window.py           │
                     │  ui/profile_tab.py           │
                     │  ui/window_panel.py          │
                     │  ui/admin_panel.py           │
                     │  ui/tray.py  ui/icons.py     │
                     └───────────────┬──────────────┘
                                     │ señales Qt
                     ┌───────────────▼──────────────┐
                     │  core/controller.py          │
                     │  (estado y acciones)         │
                     └───┬────────────┬──────────┬───┘
                         │            │          │
        ┌────────────────▼──┐  ┌──────▼──────┐  ┌▼───────────────┐
        │ discovery.py       │  │ processes.py │  │ core/resolver.py│
        │ perfiles nativos   │  │ /proc, fds   │  │ ventana→perfil  │
        └────────────────────┘  └──────┬──────┘  └────────────────┘
                                        │
                     ┌──────────────────▼──────────────────┐
                     │  x11/  (backend.py, wmctrl, grab)   │
                     │  base.py (protocolo comun)           │
                     └─────────────────────────────────────┘

        ┌────────────────────┐        ┌────────────────────────┐
        │ database.py        │        │ core/launcher.py       │
        │ SQLite propio      │        │ Brave --profile-directory │
        └────────────────────┘        └────────────────────────┘
```

El controlador (`core/controller.py`) es el unico que conoce el estado
completo. La interfaz solo lee ese estado y llama a sus acciones; los modulos
de bajo nivel (descubrimiento, procesos, resolucion, backends) no conocen
PySide6 y se pueden probar de forma aislada.

## 2. Ciclo de actualizacion

Un temporizador de Qt (2 s por defecto, configurable) dispara `refresh()`:

1. `discovery.discover_profiles()` lee `Local State` y las carpetas de perfil;
   devuelve nombre visible, avatar y orden.
2. Se fusiona con la configuracion guardada en SQLite (`_merge_profiles`): lo
   que el usuario haya personalizado manda, lo demas se crea con valores por
   defecto.
3. `processes.scan_brave_processes()` recorre `/proc` y clasifica los procesos
   de Brave por tipo (`browser`, `renderer`, `gpu-process`, ...).
4. `processes.profile_dirs_in_use()` determina que perfiles estan **abiertos**
   leyendo los descriptores de fichero abiertos por el proceso del navegador.
5. `backend.list_windows()` enumera las ventanas de Brave via EWMH.
6. `_learn_from_launch()` incorpora las asignaciones aprendidas en los
   ultimos segundos.
7. `resolver.resolve()` asocia cada ventana con un perfil y fija el metodo y
   la confianza.
8. Se emiten `profilesChanged` y `windowsChanged` y la interfaz se redibuja.

## 3. El problema de la asociacion ventana-perfil

Es el punto mas delicate de la especificacion (apartado 4 del SRS) y se ha
estudiado empiricamente sobre Linux Mint 22.3 / Cinnamon antes de escribir
nada de codigo. Los resultados:

| Hipotesis | Resultado |
|---|---|
| El PID de la ventana identifica el perfil | **Falso.** Todas las ventanas de todos los perfiles de un mismo `user-data-dir` comparten un unico proceso del navegador, asi que `_NET_WM_PID` es identico para todas. |
| Alguna propiedad X11 indica el perfil | **Falso.** Se revisaron `_NET_WM_*`, `WM_CLASS`, `WM_CLIENT_MACHINE`, `WM_WINDOW_ROLE` y similares: ninguna contiene el directorio ni el nombre del perfil. |
| Los argumentos de `/proc/<pid>/cmdline` identifican el perfil | **Parcial.** El proceso del navegador conserva `--profile-directory`, pero es el mismo para todas las ventanas, y Chromium **reescribe el titulo** de sus procesos secundarios, de modo que `cmdline` llega como una unica cadena con espacios. |
| `brave --profile-directory=X` enfoca la ventana existente | **Falso.** Chromium abre una **ventana nueva** en ese perfil, aunque el perfil ya estuviera abierto. Por eso la app activa la ventana que ya conoce y solo lanza cuando no hay ninguna. |
| Los ficheros abiertos por el proceso revelan los perfiles activos | **Verdadero.** El proceso del navegador mantiene descriptores dentro de `<user-data-dir>/<Perfil>/`. Es la senal fiable que se usa. |
| `_NET_WM_USER_TIME` permite saber cual es la ventana reciente | **Descartado.** Es tiempo del servidor X, no tiempo Unix; no es comparable con marcas de tiempo del sistema. |

### Cascada de reglas

`core/resolver.py` aplica las reglas en orden y la primera que encaja fija el
metodo y la confianza:

| # | Metodo | Confianza | Condicion |
|---|---|---|---|
| 1 | `LEARNED` | 1.0 | La ventana (id + PID) tiene una asignacion guardada en SQLite. |
| 2 | `MANUAL` | 1.0 | El usuario la asigno a mano; nunca se degrada. |
| 3 | `SINGLE_PROFILE` | 0.9 | Solo hay un perfil abierto: todas las ventanas de Brave le pertenecen. |
| 4 | `TITLE` | 0.6 | El nombre del perfil aparece como palabra completa en el titulo. |
| 5 | `ELIMINATION` | 0.5 | Queda una sola ventana sin asignar y un solo perfil abierto sin ventanas. |
| 6 | `NONE` | 0.0 | No se puede resolver: la ventana aparece en «Ventanas sin asignar». |

La regla 4 usa una expresion regular con limites de palabra
(`(?<![\w])nombre(?![\w])`) para que `Work` no case con `WorkX`.

### Aprendizaje

- **Por lanzamiento**: al abrir un perfil desde la app se guarda el conjunto de
  ventanas anteriores; la ventana nueva que aparezca (preferentemente la que
  queda activa) se asocia al perfil lanzado y se guarda con metodo `learned`.
  La ventana queda marcada durante 20 s (`LAUNCH_LEARNING_SECONDS`).
- **Manual**: el desplegable de cada tarjeta sin asignar, o el boton «Tomar la
  ventana activa», guardan la asignacion con metodo `manual`.

Las asignaciones se indexan por `(window_id, browser_pid)`, de modo que
reaparecen al volver a abrir el mismo perfil en una sesion posterior.

## 4. Backends de ventanas

`x11/base.py` define el protocolo `WindowBackend` y `x11/__init__.py` elige la
implementacion disponible:

| Backend | Cuando se usa | Notas |
|---|---|---|
| `X11Backend` | Sesion X11 con `python-xlib` instalado | Preferido: no depende de binarios externos. Usa `_NET_CLIENT_LIST`, `_NET_WM_PID`, `_NET_WM_NAME`, `WM_CLASS` y `_NET_WM_STATE`. |
| `WmctrlBackend` | X11 sin python-xlib o con fallo del anterior | Envuelve `wmctrl -lp -x`. |
| `NullBackend` | Wayland o sin soporte | La app sigue funcionando: descubre perfiles y los abre, pero no enumera ventanas. |

Las acciones de activar y minimizar se hacen con `ClientMessage` de EWMH
(`_NET_ACTIVE_WINDOW` y `_NET_WM_STATE`), que es lo que espera Muffin/Cinnamon.

## 5. Atajos globales

`x11/grab.py` monta un hilo con capturas pasivas de teclado (`grab_key`) sobre
la ventana raiz de X11. Si la combinacion ya esta ocupada por otra aplicacion,
el servidor responde `BadAccess`; la app lo detecta, lo comunica por el estado
y deja ese atajo desactivado en lugar de fallar. Los atajos que funcionan con
la ventana enfocada se registran ademas como `QShortcut` locales, de modo que
siguen siendo utilizables aunque la captura global falle.

## 6. Persistencia

SQLite en `~/.local/share/brave-workspace-manager/workspace.db`:

| Tabla | Contenido |
|---|---|
| `profiles` | `id`, `directory_name`, `display_name`, `color`, `icon`, `sort_order`, `is_favorite`, marcas de tiempo. |
| `window_assignments` | `window_id`, `browser_pid`, `profile_id`, `title`, `method`, marca de tiempo. Clave primaria compuesta `(window_id, browser_pid)`. |
| `settings` | Preferencias de la aplicacion en pares clave/valor (intervalo de refresco, atajos, bandeja, inicio automatico). |

El acceso es seguro entre hilos (`RLock` + `check_same_thread=False`) porque
el hilo de capturas de teclado tambien consulta ajustes.

## 7. Modelo de seguridad

- **Solo lectura** sobre el directorio de datos de Brave. No se escribe nunca
  en `Local State` ni en las bases de datos de los perfiles.
- No se leen cookies, contrasenas, tokens, historial ni URLs.
- No se intercepta trafico ni se instalan certificados.
- Crear o renombrar perfiles se delega en el gestor nativo de Brave
  (`brave://settings/manageProfile`); la app solo guarda el **nombre visible**
  en su propia base de datos, no en la de Brave.
- Los perfiles se abren siempre con su directorio nativo, evitando instancias
  concurrentes sobre el mismo perfil.
- La aplicacion no necesita privilegios especiales: todo vive en el `$HOME` del
  usuario.

## 8. Interfaz

- `ui/theme.py` define la paleta oscura y la hoja de estilos completa.
- `ui/icons.py` dibuja los iconos de forma procedural (16 glifos) y genera el
  avatar de cada perfil a partir de su icono de Brave o de sus iniciales, de
  modo que el repositorio no necesita recursos binarios.
- `ui/main_window.py` monta la ventana principal: cabecera, barra de perfiles
  (`QScrollArea`), divisor entre el panel de ventanas y el de administracion,
  y la barra de estado con el backend activo.
- `ui/admin_panel.py` contiene la tabla de perfiles, el formulario de
  personalizacion, la tabla de atajos y los ajustes.
- `ui/tray.py` ofrece el icono de bandeja con acceso rapido a los perfiles.

## 9. Modo degradado y fallos previstos

| Situacion | Comportamiento |
|---|---|
| Sesion Wayland | Backend `none`: se listan y abren perfiles, sin gestion de ventanas. |
| `python-xlib` ausente | Backend `wmctrl` si existe el binario; si no, `none`. |
| `wmctrl` y `python-xlib` ausentes | La app arranca igualmente y lo indica en la barra de estado. |
| Brave no instalado | Se listan los perfiles existentes; el boton «Abrir perfil» avisa de que falta el ejecutable. |
| Proceso de Brave que desaparece durante el recorrido | Se ignora sin abortar el refresco. |
| Atajo global en conflicto | Se desactiva ese atajo y se avisa; el resto sigue funcionando. |

## 10. Limitaciones conocidas y trabajo futuro

- La agrupacion exacta de ventanas por perfil no es posible cuando varios
  perfiles estan abiertos y ninguno se ha lanzado desde la app: en ese caso
  las ventanas quedan en «Ventanas sin asignar» hasta que se resuelven a mano
  o se vuelven a lanzar desde la aplicacion.
- No se enumeran las pestañas individuales de Brave: Chromium no ofrece una
  API publica estable para ello (apartado 4 del SRS).
- No hay soporte de Wayland mas alla del modo degradado.
- El panel de administracion es funcional pero basico; el arbol de perfiles y
  la previsualizacion de pestañas quedan para fases posteriores.
