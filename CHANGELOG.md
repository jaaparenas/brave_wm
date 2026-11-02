# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [semantic versioning](https://semver.org/).

## [1.1.0] — 2026-11-02

### Added

- Window controls on every profile card: activate, minimise / restore,
  maximise / restore and close, plus a "…" menu with per-window actions when a
  profile has several windows. Closed profiles show no action buttons.
- Closing a window is a polite request (`WM_DELETE_WINDOW` with python-xlib,
  `wmctrl -c` with the fallback backend); processes are never killed.
- Drag and drop to reorder the profile cards; the order is saved.
- Each window's profile is read from the accessibility tree, where Brave
  publishes the profile name next to the window title. It corrects wrong
  learned assignments automatically; manual assignments are respected.
- Tab counts for Brave started outside the app: the app briefly turns on the
  `ScreenReaderEnabled` property of the AT-SPI bus so Brave builds its
  accessibility tree without a restart, then restores the property.
- `install.sh` and `uninstall.sh`: per-user installation without `sudo` in
  its own virtual environment (`~/.local/lib/brave-workspace-manager`), with
  the `brave-workspace-manager` command, menu entry, icon and start at login
  hidden in the tray. Uninstalling keeps the user's data unless `--purge`.
- The system tray icon is always present. Its menu switches between
  profiles: open ones first with avatar and tab count (the active one marked),
  closed ones under **Other profiles**. A double click opens the window
  maximised, and closing the window hides it to the tray.
- **Move to profile** and **Not from this profile** in a card's **…** menu, to
  correct the profile of a window.
- Custom image per profile, from the administration panel (**Choose image…**
  / **Remove image**) or the card's context menu (**Change image…**). PNG,
  JPG/JPEG, WebP, BMP and GIF are accepted. The file is copied to
  `~/.local/share/brave-workspace-manager/images/`; Brave's files are not
  touched.
- **Unassigned windows** card at the end of the gallery: pick a window and
  assign it to an existing profile, save it as a new profile, or activate,
  minimise or close it.
- Virtual profiles: **Save as new profile** creates a profile that exists only
  inside the app and owns that window. Virtual profiles cannot be launched
  directly because they have no Brave profile folder.
- Internationalisation: English and Spanish interface; the first start
  follows the system language and English is the fallback. Flat key→text JSON catalogues in
  `brave_workspace_manager/locales/`, a language selector in the header that
  switches live, the choice saved in the `language` setting, and a
  `--language` command-line option. New languages are added by dropping a new
  catalogue file.
- Automatic database migration that adds the `custom_image` and `is_virtual`
  columns to the `profiles` table.
- Tests for the translation layer, including a check that every catalogue has
  the same keys. 149 tests in total.

### Changed

- The left column shows the summary on top and the administration panel
  (profiles table, customisation, settings and shortcuts) below it, always
  visible.
- The profile gallery sits on the right, centred, and each open profile's card
  shows its number of tabs.
- All documentation is now in English. Screenshots moved to
  `docs/images/main-window.png`, `docs/images/main-window-es.png` and
  `docs/images/unassigned-card.png`.

### Fixed

- Minimise did nothing on Cinnamon: windows are now iconified with the ICCCM
  `WM_CHANGE_STATE` message and restored with `_NET_ACTIVE_WINDOW` (window
  managers ignore client requests for `_NET_WM_STATE_HIDDEN`). The minimise
  button of an already minimised window now restores it.
- Maximise / restore sends both states in one request and brings the window
  to the front, so the change is visible.
- Windows could be shown on the wrong profile: the window-title rule matched
  page titles that mention a profile name, and clicking a card saved that
  guess permanently. The title rule is gone and guesses are no longer saved.
- Local keyboard shortcuts were registered twice, which made Qt ignore them.

### Removed

- The window-title matching rule.
- The **Administrator** toggle button and its `Ctrl+Alt+B` shortcut (the
  administration panel is always visible now).
- The **Tray** button in the header and the tray setting: the tray icon is
  always present now.
- The bottom panel with the windows of the selected profile
  (`ui/window_panel.py`); its actions now live on the cards.
- The old screenshots `docs/images/ventana-principal.png` and
  `docs/images/panel-admin.png`.

## [1.0.0] — 2026-11-02

### Added

- Non-destructive discovery of Brave's native profiles from `Local State` and
  the folders of the data directory, with each profile's display name, avatar
  and open/closed status.
- Profile bar with colour, icon, avatar, favourite mark and custom order,
  persisted in SQLite.
- Windows panel with activate, minimise, restore and manual assignment, and a
  separate section for the windows Chromium does not allow to identify.
- Window-to-profile resolution with five rules (learned assignment, single
  open profile, title match, elimination and unassigned) with visible
  confidence.
- Administrator panel: profiles table, customisation (name, colour, icon,
  favourite), order, settings and shortcut editing.
- Global shortcuts `Ctrl+Alt+1`…`9`, `Ctrl+Alt+Tab`, `Ctrl+Alt+Shift+Tab` and
  `Ctrl+Alt+B`, with conflict detection and local fallback shortcuts.
- System tray icon and autostart through an XDG `.desktop` file.
- Interchangeable window backends: EWMH with `python-xlib`, a `wmctrl`
  fallback and a degraded mode without window support.
- Command-line options: `--version`, `--minimized` and `--user-data-dir`.
- Single instance through `QLockFile`.
- Count of the open tabs of each window and each profile, read from the
  browser's accessibility tree (AT-SPI) in a separate process, with a
  drop-down list of titles and the active tab marked. The launcher opens
  profiles with `--force-renderer-accessibility`, without which Chromium does
  not publish its tab strip; if the browser was already running, the app
  warns that only the active tab is visible.
- **List the open tabs** setting to turn off tab reading and the browser flag.
- 96 automated tests that never access the browser's real data.
- GitHub release with MIT licence, `pyproject.toml` packaging, installers, a
  systemd user service and continuous integration.

### Changed

- The horizontal profile bar is replaced by a **gallery**: cards are laid out
  in columns that depend on the window width, the grid is centred and the
  active profile is highlighted with an accent border.
- The profile summary becomes a fixed panel on the left that is always
  visible, with the total of profiles, open, closed and favourite profiles,
  Brave windows detected, unassigned windows and the active profile.
- Each card shows the avatar, name, status and favourite mark vertically, with
  the profile colour on top.

### Security

- No writes to Brave's internal data.
- No access to cookies, passwords, history, URLs or HTTPS traffic.
- Creating and renaming profiles in Brave is delegated to Brave's native
  profile manager.
- Only the title of each tab is read from the tab strip, in memory: it is not
  saved to disk or sent anywhere, and no URLs, cookies or history are read.

### Fixed

- Global shortcuts are now really reserved in the X server: the correct
  `grab_key` signature is used with a per-request error handler, and the grab
  thread reads events with `next_event()` instead of treating
  `pending_events()` as a list.
- Shortcuts are registered after the application starts, so they work even if
  the administrator panel is opened later.
- The application's own window no longer appears in the Brave windows panel:
  it is filtered out by its own PID and by the `brave-browser` class.
- If the application ends abruptly, the instance lock file is recovered only
  when the process that created it no longer exists.
- Gallery cards no longer stay hidden when the profile list is updated while
  the window is already visible.
