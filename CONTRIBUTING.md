# Contributing

Thanks for your interest. The project is small and its technical decisions are
documented, so it should be easy to follow the reasoning behind them.

## Setup

```bash
git clone https://github.com/jaaparenas/brave_wm.git
cd brave_wm
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest pytest-cov ruff
```

## Running the tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

The tests **never touch real Brave data**: they build a synthetic data
directory in a temporary folder. Changes to resolution, discovery,
persistence, the launcher, processes and the gallery can be checked without
opening the browser. `QT_QPA_PLATFORM=offscreen` lets the widget tests run
without a display.

With coverage:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest --cov=brave_workspace_manager --cov-report=term-missing
```

## Code style

- Python 3.10+, with type hints where they add clarity.
- `ruff check` and `ruff format --check` must pass without warnings.
- The low-level modules (`config`, `discovery`, `processes`, `database`,
  `i18n`, `core/resolver`, `core/launcher`, `core/autostart`, `x11/*`) **do
  not import PySide6**: the interface is a layer on top. The only exception is
  `core/controller.py`, which uses `QObject` signals and timers to talk to the
  interface.
- Comments only where the code does not explain itself; in particular,
  explain *why* something is done when Chromium or X11 behave in
  counter-intuitive ways.
- User-facing text never goes in the code as a literal: add a key to
  `brave_workspace_manager/locales/en.json` and the same key to every other
  catalogue (currently `es.json`), and use `tr("key")`. `tests/test_i18n.py`
  fails if the catalogues get out of sync.

## Non-negotiable rules

1. **Never** write to Brave's data directory (`Local State`, profile
   databases, etc.). Read-only.
2. **Never** touch cookies, passwords, tokens, history or URLs.
3. **Never** intercept HTTPS traffic or install certificates.
4. Profiles are opened with their native folder
   (`--profile-directory=<folder>`), without creating parallel instances.
5. Windows are closed politely (`WM_DELETE_WINDOW` / `wmctrl -c`); processes
   are never killed.
6. Anything the app stores (including custom images) goes into its own data
   directory, never into Brave's.

## Sending a change

1. Create a branch: `git checkout -b feature/my-change`.
2. Add or adjust tests for the new behaviour.
3. Run `pytest` and `ruff`.
4. Open a pull request describing **what** changes and **why**.
5. If the change affects how windows are matched to profiles, explain the
   evidence you gathered on your system (session type, Brave version, number
   of open profiles). This is the most delicate part of the project and
   claims without evidence cannot be reviewed.

If the change alters the interface, regenerate the screenshots with
`.venv/bin/python tools/screenshot.py` (it uses synthetic data only).

## Adding a translation

1. Copy `brave_workspace_manager/locales/en.json` to `<code>.json`.
2. Translate the values, keeping the keys and the `{placeholders}` unchanged.
3. Set `"language_name"` to the language's own name.
4. Run the tests; `tests/test_i18n.py` checks that the keys match `en.json`
   and that no text is empty.

The language shows up in the header selector automatically.

## Reporting bugs

Use the template in `.github/ISSUE_TEMPLATE/bug_report.yml`. Include the
application's terminal output and the active backend (shown in the status
bar: `x11`, `wmctrl` or `none`).

## Scope of contributions

Areas where help is especially welcome:

- Compatibility with other X11 window managers and with Wayland.
- Better window-to-profile matching (for example, following the user's focus
  changes to learn assignments).
- Window previews and better handling of multiple windows per profile.
- Translations of the interface into more languages.

See `docs/ARCHITECTURE.md` for technical details and `docs/SPECIFICATION.md`
for the original requirements.
