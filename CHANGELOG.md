# Changelog

Todas las novedades de este proyecto se anotan aqui.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y el
proyecto usa [versionado semantico](https://semver.org/lang/es/).

## [1.0.0] — 2026-11-02

### Añadido

- Descubrimiento no destructivo de los perfiles nativos de Brave a partir de
  `Local State` y de las carpetas del directorio de datos, con el nombre
  visible, el avatar y el estado abierto/cerrado de cada perfil.
- Barra de perfiles con color, icono, avatar, marca de favorito y orden
  personalizable, con persistencia en SQLite.
- Panel de ventanas con activacion, minimizacion, restauracion y asignacion
  manual, y seccion independiente para las ventanas que Chromium no permite
  identificar.
- Resolucion ventana-perfil en cinco reglas (asignacion aprendida, perfil
  unico abierto, coincidencia de titulo, eliminacion y sin asignar) con
  confianza visible.
- Panel de administrador: tabla de perfiles, personalizacion (nombre, color,
  icono, favorito), orden, ajustes y edicion de atajos.
- Atajos globales `Ctrl+Alt+1`…`9`, `Ctrl+Alt+Tab`, `Ctrl+Alt+Shift+Tab` y
  `Ctrl+Alt+B`, con deteccion de conflictos y copia local de respaldo.
- Icono en la bandeja del sistema e inicio automatico mediante fichero
  `.desktop` de XDG.
- Backends de ventanas intercambiables: EWMH con `python-xlib`, alternativa con
  `wmctrl` y modo degradado sin soporte de ventanas.
- Modo de linea de comandos: `--version`, `--minimized` y `--user-data-dir`.
- Instancia unica mediante `QLockFile`.
- Recuento de las pestanas abiertas de cada ventana y de cada perfil, leidas
  del arbol de accesibilidad del navegador (AT-SPI) en un proceso aparte, con
  la lista de titulos desplegable y la pestana activa marcada. El lanzador
  abre los perfiles con `--force-renderer-accessibility`, sin el cual Chromium
  no publica su barra de pestanas; si el navegador ya estaba en marcha, la
  aplicacion avisa de que solo se ve la pestana activa.
- Ajuste **Listar las pestanas abiertas** para desactivar la lectura y el flag
  del navegador.
- 96 pruebas automaticas que no acceden a los datos reales del navegador.
- Publicacion en GitHub con licencia MIT, empaquetado `pyproject.toml`,
  instaladores, servicio de systemd de usuario e integracion continua.

### Cambiado

- La barra horizontal de perfiles se sustituye por una **galeria**: las fichas
  se reparten en columnas que dependen del ancho de la ventana, el conjunto
  queda centrado y el perfil activo se resalta con un borde de acento.
- El resumen de los perfiles pasa a ser un panel fijo a la izquierda que
  permanece siempre visible con el total de perfiles, los abiertos, los
  cerrados, los favoritos, las ventanas de Brave detectadas, las ventanas sin
  asignar y el perfil activo.
- Cada ficha muestra el avatar, el nombre, el estado y la marca de favorito en
  vertical, con el color del perfil en la parte superior.

### Seguridad

- Ninguna escritura en los datos internos de Brave.
- Sin acceso a cookies, contrasenas, historial, URLs ni trafico HTTPS.
- La creacion y el renombrado de perfiles se delegan en el gestor nativo de
  Brave.
- De la barra de pestanas solo se lee el titulo de cada pestaña, en memoria:
  no se guarda en disco ni se envia a ninguna parte, y no se leen URLs,
  cookies ni historial.

### Corregido

- Los atajos globales ya se reservan de verdad en el servidor X: se usa la
  firma correcta de `grab_key` con manejador de error por peticion, y el
  hilo de captura lee los eventos con `next_event()` en lugar de tratar
  `pending_events()` como una lista.
- Los atajos se registran despues de arrancar la aplicacion, de modo que ya
  funcionan aunque el panel de administrador se abra mas tarde.
- La ventana de la propia aplicacion ya no aparece en el panel de ventanas de
  Brave: se filtra por PID propio y por clase `brave-browser`.
- Si la aplicacion termina de forma abrupta, el fichero de instancia se
  recupera solo cuando el proceso que lo creo ya no existe.
- Las fichas de la galeria ya no se quedan ocultas cuando la lista de
  perfiles se actualiza con la ventana ya visible.
