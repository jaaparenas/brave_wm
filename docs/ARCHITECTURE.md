# Architecture

Design document for **Brave Workspace Manager**: what each module does, how
they relate to each other and, above all, why matching windows to profiles
works the way it does.

## 1. Overview

```
                     ┌──────────────────────────────┐
                     │          interface           │
                     │  ui/main_window.py           │
                     │  ui/profile_gallery.py       │
                     │  ui/profile_tab.py           │
                     │  ui/unassigned_card.py       │
                     │  ui/admin_panel.py           │
                     │  ui/tray.py  ui/icons.py     │
                     └───────────────┬──────────────┘
                                     │ Qt signals
                     ┌───────────────▼──────────────┐
                     │  core/controller.py          │
                     │  (state and actions)         │
                     └───┬────────────┬──────────┬──┘
                         │            │          │
        ┌────────────────▼──┐  ┌──────▼──────┐  ┌▼────────────────┐
        │ discovery.py      │  │ processes.py│  │ core/resolver.py│
        │ native profiles   │  │ /proc, fds  │  │ window→profile  │
        └───────────────────┘  └──────┬──────┘  └─────────────────┘
                                      │
                     ┌────────────────▼────────────────────┐
                     │  x11/  (backend.py, wmctrl, grab)   │
                     │  base.py (common protocol)          │
                     └─────────────────────────────────────┘

        ┌────────────────────┐        ┌───────────────────────────┐
        │ database.py        │        │ core/launcher.py          │
        │ own SQLite         │        │ Brave --profile-directory │
        └────────────────────┘        └───────────────────────────┘

        ┌────────────────────┐        ┌────────────────────────┐
        │ tabs.py            │        │ a11y_helper.py         │
        │ client + matching  │        │ AT-SPI reader (JSON)   │
        └────────────────────┘        └────────────────────────┘

        ┌────────────────────────────────────────────┐
        │ i18n.py + locales/*.json (translations)    │
        └────────────────────────────────────────────┘
```

The controller (`core/controller.py`) is the only component that knows the
whole state. The interface only reads that state and calls its actions; the
low-level modules (discovery, processes, resolution, backends, translations)
do not know about PySide6 and can be tested in isolation.

## 2. Refresh cycle

A Qt timer (2 s by default, configurable) triggers `refresh()`:

1. `discovery.discover_profiles()` reads `Local State` and the profile
   folders; it returns display name, avatar and order.
2. The result is merged with the configuration saved in SQLite
   (`_merge_profiles`): whatever the user customised wins, the rest is created
   with default values. Virtual profiles (section 8) are kept even though
   Brave does not report them.
3. `processes.scan_brave_processes()` walks `/proc` and classifies Brave's
   processes by type (`browser`, `renderer`, `gpu-process`, ...).
4. `processes.profile_dirs_in_use()` determines which profiles are **open**
   by reading the file descriptors held by the browser process.
5. `backend.list_windows()` lists Brave's windows through EWMH.
6. `_learn_from_launch()` incorporates the assignments learned in the last
   few seconds.
7. `resolver.resolve()` matches each window with a profile and sets the
   method and confidence.
8. `profilesChanged` and `windowsChanged` are emitted and the interface
   redraws.

## 3. The window-to-profile matching problem

This is the most delicate point of the specification (section 4 of the SRS)
and it was studied empirically on Linux Mint 22.3 / Cinnamon before writing
any code. The findings:

| Hypothesis | Result |
|---|---|
| The window PID identifies the profile | **False.** All windows of all profiles in the same `user-data-dir` share a single browser process, so `_NET_WM_PID` is identical for all of them. |
| Some X11 property indicates the profile | **False.** `_NET_WM_*`, `WM_CLASS`, `WM_CLIENT_MACHINE`, `WM_WINDOW_ROLE` and similar were checked: none contains the profile folder or name. |
| The arguments in `/proc/<pid>/cmdline` identify the profile | **Partial.** The browser process keeps `--profile-directory`, but it is the same for every window, and Chromium **rewrites the title** of its child processes, so `cmdline` arrives as a single space-separated string. |
| `brave --profile-directory=X` focuses the existing window | **False.** Chromium opens a **new window** in that profile, even if it was already open. That is why the app activates the window it already knows and only launches when there is none. |
| The files held open by the process reveal the active profiles | **True.** The browser process keeps descriptors inside `<user-data-dir>/<Profile>/`. This is the reliable signal used. |
| `_NET_WM_USER_TIME` tells which window is the most recent | **Discarded.** It is X server time, not Unix time; it cannot be compared with system timestamps. |

### Rule cascade

`core/resolver.py` applies the rules in order and the first one that matches
sets the method and confidence:

| # | Method | Confidence | Condition |
|---|---|---|---|
| 1 | `LEARNED` | 1.0 | The window (id + PID) has an assignment saved in SQLite. |
| 2 | `MANUAL` | 1.0 | The user assigned it by hand; it is never downgraded. |
| 3 | `SINGLE_PROFILE` | 0.9 | Only one profile is open: every Brave window belongs to it. |
| 4 | `TITLE` | 0.6 | The profile name appears as a whole word in the title. |
| 5 | `ELIMINATION` | 0.5 | Exactly one window is unassigned and exactly one open profile has no windows. |
| 6 | `NONE` | 0.0 | Cannot be resolved: the window goes to the **Unassigned windows** card. |

Rule 4 uses a regular expression with word boundaries
(`(?<![\w])name(?![\w])`) so that `Work` does not match `WorkX`.

### Learning

- **On launch**: when a profile is opened from the app, the set of existing
  windows is recorded; the new window that appears (preferably the one that
  becomes active) is matched with the launched profile and saved with method
  `learned`. The window stays marked for 20 s (`LAUNCH_LEARNING_SECONDS`).
- **Manual**: the **Assign to profile…** drop-down of the Unassigned windows
  card, the **Take the active window** entry of a card's context menu, and
  **Save as new profile** save the assignment with method `manual`.

Assignments are indexed by `(window_id, browser_pid)`, so they reappear when
the same profile is opened again in a later session.

## 4. Reading open tabs

Chromium does not expose the number of tabs of a window through X11/EWMH:
that protocol only provides the window title, which is the title of the
active tab. The only local route that does not touch the browser's data is
the **accessibility tree** (AT-SPI), the same one screen readers consume.

The flow has three pieces:

| Piece | File | What it does |
|---|---|---|
| Reader | `a11y_helper.py` | Standalone script (does not import the package) that walks the AT-SPI desktop, finds Brave's windows and returns JSON with their tabs. |
| Client | `tabs.py` | Runs the reader in a subprocess, trying the virtual environment's interpreter first and then `/usr/bin/python3`, and matches each window with its frame by normalised title and, if needed, by geometry overlap. |
| State | `core/controller.py` | Distributes the titles among windows and profiles and publishes a warning when reading is not possible. |

Details that shape the design:

- **Chromium only publishes its interface** (tab strip included) when started
  with `--force-renderer-accessibility`. That is why `core/launcher.py` adds
  the flag to the profiles the app opens. If the browser was already running,
  the flag has no effect: `processes.accesibilidad_activada()` detects it and
  the interface explains that only the active tab is visible.
- **The tab strip** appears as a `page tab list` with one `page tab` per tab;
  the one in the foreground has the `selected` state. Chromium also leaves an
  empty, hidden strip, which is discarded.
- **Page content is not read**: the reader does not descend into
  `document web` subtrees, so only each tab's title is obtained. No URLs,
  cookies, passwords or history are read, and the titles are not stored.
- **Reading happens in a subprocess and a thread**: `TabReaderThread` runs it
  outside the interface thread, every 10 s, so the window does not freeze.

## 5. Window backends

`x11/base.py` defines the `WindowBackend` protocol and `x11/__init__.py`
picks the available implementation:

| Backend | When it is used | Notes |
|---|---|---|
| `X11Backend` | X11 session with `python-xlib` installed | Preferred: no external binaries. Uses `_NET_CLIENT_LIST`, `_NET_WM_PID`, `_NET_WM_NAME`, `WM_CLASS` and `_NET_WM_STATE`. |
| `WmctrlBackend` | X11 without python-xlib, or when the former fails | Wraps `wmctrl -lp -x`. |
| `NullBackend` | Wayland or no support | The app keeps working: it discovers and opens profiles, but does not list windows. |

`X11Backend` performs window actions with EWMH `ClientMessage`s, which is
what Muffin/Cinnamon expects:

| Action | `X11Backend` | `WmctrlBackend` |
|---|---|---|
| Activate | `_NET_ACTIVE_WINDOW` | `wmctrl -i -a` |
| Minimise / restore | `_NET_WM_STATE_HIDDEN` | `xdotool windowminimize` / `windowmap windowraise` (needs `xdotool`) |
| Maximise / restore size | `_NET_WM_STATE_MAXIMIZED_VERT` + `_NET_WM_STATE_MAXIMIZED_HORZ` | `wmctrl -b add/remove,maximized_vert,maximized_horz` |
| Close | `WM_PROTOCOLS` / `WM_DELETE_WINDOW` | `wmctrl -i -c` |

Closing is always a polite request, equivalent to clicking the window's close
button: Brave can still ask for confirmation, and no process is ever killed.

## 6. Global shortcuts

`x11/grab.py` runs a thread with passive keyboard grabs (`grab_key`) on the
X11 root window. If the combination is already taken by another application,
the server answers `BadAccess`; the app detects it, reports it in the status
bar and leaves that shortcut disabled instead of failing. Shortcuts are also
registered as local `QShortcut`s, so they remain usable while the window has
focus even if the global grab fails.

The default shortcuts are `Ctrl+Alt+1`…`9` (profile N in gallery order),
`Ctrl+Alt+Tab` and `Ctrl+Alt+Shift+Tab` (next / previous profile).

## 7. Persistence

SQLite in `~/.local/share/brave-workspace-manager/workspace.db`:

| Table | Contents |
|---|---|
| `profiles` | `id`, `directory_name`, `display_name`, `color`, `icon`, `sort_order`, `is_favorite`, `custom_image`, `is_virtual`, timestamps. |
| `window_assignments` | `window_id`, `browser_pid`, `profile_id`, `title`, `method`, timestamp. Composite primary key `(window_id, browser_pid)`. |
| `settings` | Application preferences as key/value pairs (refresh interval, activate on click, shortcuts, tray, autostart, tab reading, `language`). |

Access is thread-safe (`RLock` + `check_same_thread=False`) because the
keyboard grab thread also reads settings.

**Migrations**: `Database.migrate()` runs on every start. It creates missing
tables and `_add_missing_columns()` adds the columns introduced after the
first release (`custom_image`, `is_virtual`) with `ALTER TABLE`, so existing
databases are upgraded in place without losing data.

**Custom images**: `AppController.set_profile_image()` accepts `.png`,
`.jpg`, `.jpeg`, `.webp`, `.bmp` and `.gif`, copies the file to
`~/.local/share/brave-workspace-manager/images/<profile-id>.<ext>` and stores
that path in `custom_image`. Replacing or removing the image deletes the
previous copy. The original file and Brave's own avatars are never modified.

## 8. Virtual profiles

A Brave window that cannot be attributed can be turned into a **virtual
profile** with **Save as new profile** (`AppController.save_window_as_profile`).
It is a row in the app's `profiles` table with `is_virtual = 1` and an id of
the form `virtual-N`, plus a `manual` assignment of that window. It exists
only in the app's database: nothing is created in Brave.

Virtual profiles are shown, customised, reordered and activated like any
other profile, and count as open while they own a window. They cannot be
launched (`launch_profile` refuses and reports why) because there is no Brave
profile folder to pass to `--profile-directory`.

## 9. Internationalisation

`i18n.py` loads flat JSON catalogues from `locales/` (`en.json`, `es.json`),
one per language, mapping keys to texts with `str.format` placeholders.

- `tr(key, **values)` returns the text in the active language, falls back to
  English when the key is missing, and to the key itself as a last resort.
- `available_languages()` lists the catalogue files; each catalogue's
  `language_name` key holds the language's own name, used in the selector.
- Unknown codes fall back to the base language (`es_MX` → `es`) and then to
  English.
- The language is chosen, in order, from `--language`, the stored `language`
  setting, and the system language (`LANG`/`LC_*`), falling back to English. The header selector changes it live (the main window
  calls `retranslate()` on every widget that has one, then refreshes) and
  saves it.
- Adding a language means adding a catalogue file; no code changes.
  `tests/test_i18n.py` checks that all catalogues have the same keys as
  `en.json` and no empty texts.

## 10. Security model

- **Read-only** access to Brave's data directory. Nothing is ever written to
  `Local State` or to the profile databases.
- No cookies, passwords, tokens, history or URLs are read.
- Only the **title** of each tab is read from the tab strip, in memory: it is
  not persisted or transmitted, and it can be turned off completely with the
  **List the open tabs** setting.
- No traffic is intercepted and no certificates are installed.
- Creating or renaming profiles in Brave is delegated to Brave's native
  manager (`brave://settings/manageProfile`); the app only stores its own
  **display name** in its own database, not in Brave's.
- Custom images are copied into the app's own data directory.
- Profiles are always opened with their native folder on the single Brave
  instance, avoiding concurrent instances over the same profile.
- Windows are closed politely; processes are never killed.
- The application needs no special privileges: everything lives in the
  user's `$HOME`.

## 11. Interface

- `ui/theme.py` defines the dark palette and the full stylesheet.
- `ui/icons.py` draws icons procedurally (profile glyphs and the card action
  icons) and builds each profile's avatar from its custom image, its Brave
  avatar or its initials, so the repository needs no binary resources.
- `ui/main_window.py` builds the main window: the header (title, language
  selector, Refresh, Help), a splitter with the left column (summary on top,
  administration panel below, both always visible) and the gallery on the
  right, and the status bar with the active backend.
- `ui/profile_gallery.py` contains `ProfileSummary` and `ProfileGallery`. The
  gallery computes the responsive grid (columns depend on the available
  width, the grid is centred), handles drag and drop reordering (it emits
  `reordered`, which calls `AppController.reorder_profiles`) and always
  places the Unassigned windows card last.
- `ui/profile_tab.py` draws a profile card: colour strip, avatar or image,
  name, status, number of windows and tabs (titles in the tooltip), favourite
  mark, and the row of action buttons (activate, minimise/restore,
  maximise/restore, close) that only appears when the profile has a window.
  A "…" button with a per-window menu appears when it has more than one.
- `ui/unassigned_card.py` is the final card: a window selector, **Save as new
  profile**, **Assign to profile…**, and activate / minimise / close buttons.
- `ui/admin_panel.py` contains the profiles table, the customisation form
  (name, colour, icon, image, favourite, order, open, reset), the settings
  and the shortcut table.
- `ui/tray.py` provides the optional tray icon with quick access to profiles.

## 12. Degraded mode and expected failures

| Situation | Behaviour |
|---|---|
| Wayland session | Backend `none`: profiles are listed and opened, no window management. |
| `python-xlib` missing | Backend `wmctrl` if the binary exists; otherwise `none`. |
| Neither `wmctrl` nor `python-xlib` | The app starts anyway and says so in the status bar. |
| Brave not installed | Existing profiles are listed; **Open profile** warns that the executable is missing. |
| A Brave process disappears during the scan | Ignored without aborting the refresh. |
| Global shortcut conflict | That shortcut is disabled and reported; the rest keep working. |
| `python3-gi` missing | The accessibility tree cannot be read: a warning is shown and only each window's active tab is visible. |
| Brave already running without `--force-renderer-accessibility` | A warning explains that Brave must be closed completely and a profile opened from the app to list the tabs. |
| Launching a virtual profile | Refused with a status message; it has no Brave folder. |
| Unsupported or unreadable image file | The image is not changed and a status message is shown. |

## 13. Known limitations and future work

- Exact grouping of windows by profile is not possible when several profiles
  are open and none was launched from the app: those windows stay on the
  Unassigned windows card until they are resolved by hand or relaunched from
  the application.
- Tabs are listed by title, not URL: reading URLs would require opening a
  Chromium debugging port, which would give any local process access to
  cookies and credentials, or parsing Chromium's session files, which contain
  them as well. Both routes are rejected on purpose.
- The tab count depends on the browser having been opened in accessibility
  mode: if Brave was running before the app was used, only the active tab is
  visible.
- No Wayland support beyond degraded mode.
- Tab previews and a profile tree are left for later phases.
