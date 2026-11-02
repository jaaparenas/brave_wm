# Functional and technical specification (SRS)

> The original requirements document the application was built from. It was
> written in Spanish; this is an English translation that keeps its content
> unchanged. Section 15 shows
> how each requirement maps to the current implementation.

| | |
|---|---|
| Initial platform | Linux Mint + Cinnamon |
| Target browser | Brave Browser (native profiles) |
| Proposed technology | Python 3 + PySide6 + SQLite |
| Version / date | 1.0 · November 2026 |

## 1. Product vision

Build a desktop application for Linux Mint Cinnamon that manages multiple native Brave profiles from a unified visual interface. Each profile represents an independent context (client, project or personal use). The user can see all their profiles, know which ones are open, and switch between them quickly.
The experience should resemble a window with tabs along the top — Profile 1, Profile 2, Profile 3 — even though internally native, independent Brave windows are used.

## 2. Goals and principles

Keep Brave as the main browser; do not replace it or embed it in another application.
Preserve the native isolation of each profile: cookies, sessions, storage, extensions and authentication.
Allow switching profiles with a click or a keyboard shortcut, without closing or restarting windows.
Show the profiles and the state of their windows from a central interface.
Avoid directly modifying the databases and internal files of Brave's profiles.

## 3. Functional scope

### 3.1 Main interface

The interface will have three areas:
Top profile bar: visual tabs with name, colour, icon, activity indicator and number of windows/tabs when that information is available.
Content area: shows the windows of the selected profile and, in later phases, its individual tabs.
Administration area: create/open profiles, rename, change colour and icon, reorder and configure shortcuts.

### 3.2 Behaviour when switching profiles

The user selects a profile in the top bar or uses a shortcut.
The application identifies the existing windows associated with that profile.
It activates and restores the corresponding window, bringing it to the foreground.
The windows of other profiles stay open and their sessions are not modified.
If the profile has no open windows, the application can open it using its native folder.

### 3.3 Profile management

The application must discover the existing profiles in the usual location:
`~/.config/BraveSoftware/Brave-Browser/`
It must inspect, non-destructively, the Local State file and the profile folders, for example Default, Profile 1 and Profile 2. Display names and metadata must be obtained safely; it must not assume that the folder name matches the name shown in Brave.
The application's own configuration will store the profile identifier, folder, custom name, colour, icon, order and preferences. SQLite is recommended so that the model can evolve.

## 4. Window and tab management

Identifying windows is the main technical risk. It must not depend only on the title, because the title changes while browsing.
List Brave's windows and obtain their identifier from the window manager.
Relate window, PID and browser process to the corresponding profile.
Detect new, closed, minimised and active windows.
Activate, restore and minimise windows through mechanisms supported by the desktop environment.
Investigate how to reliably obtain the profile folder from Chromium's arguments/processes and how to associate it with each window.
Do not promise full reading of individual tabs in the MVP: Chromium offers no general public API for an external application to reliably list all tabs and their URLs.

## 5. Integration with Linux Mint Cinnamon

The first version will prioritise Cinnamon on X11, where external window management is more accessible.
Evaluate EWMH/X11 to list and activate windows.
Evaluate wmctrl and xdotool as auxiliary tools for the first proof of concept; prefer maintainable APIs or libraries where possible.
Use /proc to inspect processes and arguments, handling permissions and processes that disappear during the query.
Support global shortcuts, autostart and, optionally, a tray icon.
Design the integration layer so that Wayland can be added later; do not assume the same techniques will work there.

## 6. Proposed architecture

| Component | Candidate technology | Responsibility |
|---|---|---|
| Desktop interface | Python + PySide6 | Profile bar, windows panel, preferences and user events. |
| Application logic | Python 3 | Discovery, process/window association, actions and state synchronisation. |
| Persistence | SQLite | Names, colours, order, preferences and own metadata. |
| Window integration | X11/EWMH; evaluation of wmctrl | List, activate, restore and observe windows. |
| Process integration | /proc + subprocess | Inspect processes and open profiles with the appropriate arguments. |

## 7. Initial data model

### Profile

`id`, `directory_name`, `display_name`, `color`, `icon`, `sort_order`, `is_favorite`

### Window

`window_id`, `process_id`, `profile_id`, `title`, `is_active`, `is_minimized`, `last_seen`

### Tab (later phase)

`tab_id` (if obtainable), `window_id`, `title`, `url`, `is_active`
Window and tab information is dynamic state; it must not be confused with the persistent profile configuration.

## 8. Security and privacy

Do not copy, exchange or synchronise cookies between profiles.
Do not store passwords or tokens.
Do not modify Brave's internal databases or the Local State file.
Do not intercept HTTPS traffic or inspect page content.
Do not share data folders between profiles.
Treat URLs as potentially sensitive information; allow hiding them in the interface.
Open existing profiles using their native folder, without creating concurrent processes that could corrupt the same profile.

## 9. Proposed keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl + Alt + 1…9 | Activate the assigned profile |
| Ctrl + Alt + Tab | Next profile |
| Ctrl + Alt + Shift + Tab | Previous profile |
| Ctrl + Alt + B | Show/hide the administrator |

Shortcuts must be configurable, and conflicts with existing Cinnamon or application shortcuts must be detected.

## 10. Delivery plan

### Phase 0 — Technical proof of concept

Detect two native Brave profiles.
Open both profiles and keep them active at the same time.
List their windows and reliably associate them with the correct profile.
Switch between windows without restarting Brave.
Validate the behaviour on the user's actual Linux Mint/Cinnamon version.

### Phase 1 — MVP

Automatic profile discovery.
Visual profile bar with name, colour and icon.
Detection and grouping of windows by profile.
Window activation by click and global shortcuts.
Opening existing profiles and persisting preferences.
Optional autostart.

### Phase 2 — Advanced organisation

View of individual windows and tabs when technically feasible.
Previews, search and sorting.
Multiple windows per profile and multi-monitor support.
Deeper integration with Cinnamon.

### Phase 3 — Extensions

Evaluation of Wayland compatibility.
Favourite and temporary profiles.
Automatic rules and virtual desktop management.
Global tab search and optional statistics.

## 11. MVP acceptance criteria

Detects the existing native Brave profiles without modifying them.
Shows all discovered profiles in a single interface.
Correctly identifies the windows of each profile in repeated tests.
Allows switching profiles by click and keyboard.
Does not restart Brave when switching between profiles that are already open.
Does not lose sessions, cookies or tabs during the switch.
Keeps working after logging out of and back into Linux.
Correctly handles closed profiles, new windows and processes that end unexpectedly.

## 12. Risks and pending decisions

| Risk / decision | Handling |
|---|---|
| Window-profile association | High risk. Must be validated in the proof of concept; titles are not reliable identifiers. |
| Tab enumeration | Potential limitation. Do not assume a public, stable API exists to read all of Brave's tabs. |
| X11 versus Wayland | The first version prioritises X11; Wayland imposes restrictions on window control. |
| Multiple windows per profile | Define how they are presented and which one is activated when the profile is selected. |
| Opening profiles | Avoid launching concurrent instances over the same profile folder. |

## 13. Design principle

The application must feel like a natural extension of the Brave workflow, not like another browser. The interface unifies administration and context switching, but sessions remain isolated in Brave's native profiles and windows. The priority is to preserve security, stability, performance and ease of use.

## 14. Recommended first development task

Before building the full interface, implement a proof of concept in Python that detects two profiles, identifies their processes and windows, and reliably activates each window. Document the results on the user's specific Linux Mint Cinnamon version. If this test does not demonstrate a stable association, revise the architecture before going further.

## 15. Mapping to the implementation

| Section | Where it is implemented |
|---|---|
| 1, 3.1 — Unified interface | `brave_workspace_manager/ui/main_window.py`. The "top profile bar" is implemented as a responsive gallery of cards (`ui/profile_gallery.py`, `ui/profile_tab.py`) showing name, colour, icon or custom image, open status and number of windows and tabs. The content area is folded into the cards (window actions and a per-window menu) plus the Unassigned windows card (`ui/unassigned_card.py`). The administration area (`ui/admin_panel.py`) is always visible in the left column, under the summary. |
| 2 — Do not modify Brave | All access to Brave's data is read-only (`discovery.py`, `processes.py`). Custom images are copied into the app's own data folder. |
| 3.2 — Switching profiles | `core/controller.py::activate_profile` (activates the known window or opens the profile with its native folder). |
| 3.3 — Discovery and persistence | `discovery.py` + `database.py` (SQLite in `~/.local/share/brave-workspace-manager/workspace.db`, with automatic column migrations). |
| 3.1, 3.3 — Reordering | Drag and drop in the gallery (`controller.reorder_profiles`) and move up/down in the admin panel; the order is persisted. |
| 4 — Windows | `x11/backend.py` (EWMH with python-xlib) and `x11/wmctrl_backend.py` as fallback. Activate, minimise/restore, maximise/restore and polite close (`WM_DELETE_WINDOW` / `wmctrl -c`). |
| 4, 12 — Window-profile association | `core/resolver.py` with the five rules documented in the README; unresolved windows can be assigned by hand or saved as a virtual profile. |
| 4, Phase 2 — Tabs | Tab titles and counts per window through AT-SPI (`a11y_helper.py`, `tabs.py`). URLs are deliberately not read. |
| 5 — Cinnamon integration | `x11/grab.py` (keyboard grabs), `core/autostart.py`, `ui/tray.py` (optional tray icon). |
| 6 — Architecture | `docs/ARCHITECTURE.md` |
| 7 — Data model | `models.py` and the tables in `database.py`. `Profile` adds `custom_image` and `is_virtual`; `Window` is dynamic state and is not persisted, only learned assignments are. |
| 8 — Security | `docs/ARCHITECTURE.md` (section "Security model"). |
| 9 — Shortcuts | `ui/admin_panel.py` (configuration) and `x11/grab.py` (global grabs). `Ctrl+Alt+1…9`, `Ctrl+Alt+Tab` and `Ctrl+Alt+Shift+Tab` are implemented. `Ctrl+Alt+B` (show/hide the administrator) was dropped in 1.1.0 because the administration panel is always visible. |
| 10 — Delivery | Phase 0 completed as a proof of concept; Phase 1 implemented. From Phase 2, tab titles and handling of multiple windows per profile are implemented; from Phase 3, favourite profiles. |
| 11 — MVP acceptance | Covered as a whole; grouping windows by profile works with rules 1, 2, 3 and 4 and exposes the unresolvable case on the Unassigned windows card. |
| 14 — Proof of concept | Validated on Linux Mint 22.3 / Cinnamon with two simultaneous profiles; results in `docs/ARCHITECTURE.md`. |
| — Internationalisation (not in the original SRS) | `i18n.py` and `locales/*.json`; English and Spanish. |
