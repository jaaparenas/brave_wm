# Especificación funcional y técnica (SRS)

> Documento original de requisitos que da origen a la aplicación. Se conserva
> sin cambios en su contenido; la sección 15 recoge cómo se ha traducido a la
> implementación actual.

| Plataforma inicial | Linux Mint + Cinnamon |
| Navegador objetivo | Brave Browser (perfiles nativos) |
| Tecnología propuesta | Python 3 + PySide6 + SQLite |
| Versión / fecha | 1.0 · Noviembre de 2026 |

## 1. Visión del producto

Desarrollar una aplicación de escritorio para Linux Mint Cinnamon que permita administrar múltiples perfiles nativos de Brave desde una interfaz visual unificada. Cada perfil representa un contexto independiente (cliente, proyecto o uso personal). El usuario podrá ver todos sus perfiles, saber cuáles están abiertos y cambiar entre ellos rápidamente.
La experiencia debe parecerse a una ventana con pestañas superiores —Perfil 1, Perfil 2, Perfil 3— aunque internamente se utilicen ventanas nativas e independientes de Brave.

## 2. Objetivos y principios

Conservar Brave como navegador principal; no reemplazarlo ni incrustarlo en otra aplicación.
Mantener el aislamiento nativo de cada perfil: cookies, sesiones, almacenamiento, extensiones y autenticación.
Permitir cambiar de perfil con un clic o atajo de teclado, sin cerrar ni reiniciar las ventanas.
Mostrar los perfiles y el estado de sus ventanas desde una interfaz central.
Evitar modificar directamente bases de datos y archivos internos de los perfiles de Brave.

## 3. Alcance funcional

### 3.1 Interfaz principal

La interfaz tendrá tres áreas:
Barra superior de perfiles: pestañas visuales con nombre, color, icono, indicador de actividad y cantidad de ventanas/pestañas cuando esa información esté disponible.
Área de contenido: muestra las ventanas del perfil seleccionado y, en fases posteriores, sus pestañas individuales.
Área de administración: crear/abrir perfiles, renombrar, cambiar color e icono, ordenar y configurar atajos.

### 3.2 Comportamiento al cambiar de perfil

El usuario selecciona un perfil en la barra superior o utiliza un atajo.
La aplicación identifica las ventanas existentes asociadas a ese perfil.
Activa y restaura la ventana correspondiente, llevándola al primer plano.
Las ventanas de otros perfiles permanecen abiertas y sus sesiones no se modifican.
Si el perfil no tiene ventanas abiertas, la aplicación puede abrirlo usando su directorio nativo.

### 3.3 Gestión de perfiles

La aplicación debe descubrir los perfiles existentes en la ubicación habitual:
`~/.config/BraveSoftware/Brave-Browser/`
Debe inspeccionar de forma no destructiva el archivo Local State y los directorios de perfil, por ejemplo Default, Profile 1 y Profile 2. Los nombres visibles y metadatos deben obtenerse de forma segura; no se debe asumir que el nombre de carpeta coincide con el nombre mostrado en Brave.
La configuración propia de la aplicación almacenará el identificador del perfil, directorio, nombre personalizado, color, icono, orden y preferencias. Se recomienda SQLite para permitir evolución del modelo.

## 4. Administración de ventanas y pestañas

La identificación de ventanas es el principal riesgo técnico. No debe depender únicamente del título, porque cambia con la navegación.
Enumerar ventanas de Brave y obtener su identificador del gestor de ventanas.
Relacionar ventana, PID y proceso de navegador con el perfil correspondiente.
Detectar ventanas nuevas, cerradas, minimizadas y activas.
Activar, restaurar y minimizar ventanas mediante mecanismos soportados por el entorno de escritorio.
Investigar cómo obtener de forma fiable el directorio de perfil desde los argumentos/procesos de Chromium y cómo asociarlo con cada ventana.
No prometer lectura completa de pestañas individuales en el MVP: Chromium no ofrece una API pública general para que una aplicación externa enumere todas las pestañas y sus URLs de forma fiable.

## 5. Integración con Linux Mint Cinnamon

La primera versión priorizará Cinnamon bajo X11, donde la administración externa de ventanas es más accesible.
Evaluar EWMH/X11 para enumerar y activar ventanas.
Evaluar wmctrl y xdotool como herramientas auxiliares de la primera prueba de concepto; preferir APIs o bibliotecas mantenibles cuando sea posible.
Usar /proc para inspección de procesos y argumentos, con manejo de permisos y procesos que desaparecen durante la consulta.
Soportar atajos globales, inicio automático y, opcionalmente, icono de bandeja.
Diseñar la capa de integración para que Wayland pueda añadirse posteriormente; no asumir que las mismas técnicas funcionarán allí.

## 6. Arquitectura propuesta

| Componente | Tecnología candidata | Responsabilidad |
| Interfaz de escritorio | Python + PySide6 | Barra de perfiles, panel de ventanas, preferencias y eventos de usuario. |
| Lógica de aplicación | Python 3 | Descubrimiento, asociación de procesos/ventanas, acciones y sincronización del estado. |
| Persistencia | SQLite | Nombres, colores, orden, preferencias y metadatos propios. |
| Integración de ventanas | X11/EWMH; evaluación de wmctrl | Enumerar, activar, restaurar y observar ventanas. |
| Integración de procesos | /proc + subprocess | Inspeccionar procesos y abrir perfiles con argumentos apropiados. |

## 7. Modelo de datos inicial

### Profile

`id`, `directory_name`, `display_name`, `color`, `icon`, `sort_order`, `is_favorite`

### Window

`window_id`, `process_id`, `profile_id`, `title`, `is_active`, `is_minimized`, `last_seen`

### Tab (fase posterior)

`tab_id` (si es obtenible), `window_id`, `title`, `url`, `is_active`
La información de ventanas y pestañas es estado dinámico; no debe confundirse con la configuración persistente de perfiles.

## 8. Seguridad y privacidad

No copiar, intercambiar ni sincronizar cookies entre perfiles.
No almacenar contraseñas ni tokens.
No modificar bases de datos internas de Brave ni el archivo Local State.
No interceptar tráfico HTTPS ni inspeccionar contenido de páginas.
No compartir directorios de datos entre perfiles.
Tratar las URLs como información potencialmente sensible; permitir ocultarlas en la interfaz.
Abrir perfiles existentes usando su directorio nativo, sin crear procesos concurrentes que corrompan el mismo perfil.

## 9. Atajos de teclado propuestos

| Atajo | Acción |
|---|---|
| Ctrl + Alt + 1…9 | Activar el perfil asignado |
| Ctrl + Alt + Tab | Siguiente perfil |
| Ctrl + Alt + Shift + Tab | Perfil anterior |
| Ctrl + Alt + B | Mostrar/ocultar el administrador |

Los atajos deben ser configurables y deben detectarse conflictos con atajos existentes de Cinnamon u otras aplicaciones.

## 10. Plan de entregas

### Fase 0 — Prueba de concepto técnica

Detectar dos perfiles nativos de Brave.
Abrir ambos perfiles y mantenerlos simultáneamente activos.
Enumerar sus ventanas y asociarlas de forma fiable al perfil correcto.
Cambiar entre ventanas sin reiniciar Brave.
Validar el comportamiento en la versión real de Linux Mint/Cinnamon del usuario.

### Fase 1 — MVP

Descubrimiento automático de perfiles.
Barra visual de perfiles con nombre, color e icono.
Detección y agrupación de ventanas por perfil.
Activación de ventanas por clic y atajos globales.
Apertura de perfiles existentes y persistencia de preferencias.
Inicio automático opcional.

### Fase 2 — Organización avanzada

Vista de ventanas y pestañas individuales cuando sea técnicamente viable.
Previsualizaciones, búsqueda y ordenamiento.
Múltiples ventanas por perfil y soporte de varios monitores.
Integración más profunda con Cinnamon.

### Fase 3 — Extensiones

Evaluación de compatibilidad con Wayland.
Perfiles favoritos y temporales.
Reglas automáticas y gestión de escritorios virtuales.
Búsqueda global de pestañas y estadísticas opcionales.

## 11. Criterios de aceptación del MVP

Detecta los perfiles nativos existentes de Brave sin modificarlos.
Muestra todos los perfiles descubiertos en una única interfaz.
Identifica correctamente las ventanas de cada perfil en pruebas repetidas.
Permite cambiar de perfil mediante clic y teclado.
No reinicia Brave al alternar entre perfiles que ya están abiertos.
No pierde sesiones, cookies ni pestañas durante el cambio.
Sigue funcionando después de cerrar y volver a iniciar sesión en Linux.
Maneja correctamente perfiles cerrados, ventanas nuevas y procesos que terminan inesperadamente.

## 12. Riesgos y decisiones pendientes

| Riesgo / decisión | Tratamiento |
|---|---|
| Asociación ventana-perfil | Riesgo alto. Debe validarse en la prueba de concepto; los títulos no son identificadores fiables. |
| Enumeración de pestañas | Limitación potencial. No asumir que existe una API pública y estable para leer todas las pestañas de Brave. |
| X11 frente a Wayland | La primera versión prioriza X11; Wayland impone restricciones de control de ventanas. |
| Múltiples ventanas por perfil | Debe definirse cómo se presenta y cuál se activa al seleccionar el perfil. |
| Apertura de perfiles | Debe evitarse lanzar instancias concurrentes sobre el mismo directorio de perfil. |

## 13. Principio de diseño

La aplicación debe sentirse como una extensión natural del flujo de trabajo de Brave, no como otro navegador. La interfaz unifica la administración y el cambio de contexto, pero las sesiones permanecen aisladas en los perfiles y ventanas nativos de Brave. La prioridad es preservar seguridad, estabilidad, rendimiento y facilidad de uso.

## 14. Primera tarea de desarrollo recomendada

Antes de construir la interfaz completa, implementar una prueba de concepto en Python que detecte dos perfiles, identifique sus procesos y ventanas, y permita activar cada ventana de forma fiable. Documentar los resultados en la versión concreta de Linux Mint Cinnamon del usuario. Si esta prueba no demuestra una asociación estable, revisar la arquitectura antes de avanzar.

## 15. Correspondencia con la implementación

| Apartado | Dónde está resuelto |
|---|---|
| 1, 3.1 — Interfaz unificada | `brave_workspace_manager/ui/main_window.py`, `ui/profile_tab.py`, `ui/window_panel.py` |
| 2 — No modificar Brave | Todo el acceso a datos de Brave es de solo lectura (`discovery.py`, `processes.py`) |
| 3.2 — Cambio de perfil | `core/controller.py::activate_profile` (activa la ventana conocida o abre el perfil con su directorio nativo) |
| 3.3 — Descubrimiento y persistencia | `discovery.py` + `database.py` (SQLite en `~/.local/share/brave-workspace-manager/workspace.db`) |
| 4 — Ventanas | `x11/backend.py` (EWMH con python-xlib) y `x11/wmctrl_backend.py` como alternativa |
| 4, 12 — Asociación ventana-perfil | `core/resolver.py` con las cinco reglas documentadas en el README |
| 5 — Integración Cinnamon | `x11/grab.py` (capturas de teclado), `core/autostart.py`, `ui/tray.py` |
| 6 — Arquitectura | `docs/ARCHITECTURE.md` |
| 7 — Modelo de datos | `models.py` y las tablas de `database.py` |
| 8 — Seguridad | `docs/ARCHITECTURE.md` (apartado «Modelo de seguridad») |
| 9 — Atajos | `ui/admin_panel.py` (configuración) y `x11/grab.py` (capturas globales) |
| 10 — Entregas | Fase 0 completada como prueba de concepto; Fase 1 implementada en esta versión |
| 11 — Aceptación del MVP | Cubierto en conjunto; la agrupación de ventanas por perfil funciona con las reglas 1, 2, 3 y 4 y expone el caso no resoluble en «Ventanas sin asignar» |
| 14 — Prueba de concepto | Validada sobre Linux Mint 22.3 / Cinnamon con dos perfiles simultáneos; resultados en `docs/ARCHITECTURE.md` |
