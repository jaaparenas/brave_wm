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
- 42 pruebas automaticas que no acceden a los datos reales del navegador.
- Publicacion en GitHub con licencia MIT, empaquetado `pyproject.toml`,
  instaladores, servicio de systemd de usuario e integracion continua.

### Seguridad

- Ninguna escritura en los datos internos de Brave.
- Sin acceso a cookies, contrasenas, historial, URLs ni trafico HTTPS.
- La creacion y el renombrado de perfiles se delegan en el gestor nativo de
  Brave.
