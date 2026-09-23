# Notes to AI Agents

## What this is

Postit is a PyQt6 desktop app that does exactly one thing: pop a dialog with a text area, and on **Save** write what you typed into a timestamped markdown file. There is no main window. The note dialog *is* the application, and the process exits as soon as the note is written. The only state is a small per-user config file holding two paths.

It's a rewrite of an older bash + zenity version (`../Postit--bash`), kept behavior-for-behavior identical except that the old version's desktop notification after saving was deliberately dropped.

The notes folder and the note template are **settings, read from `~/.config/postit/postit-config.yaml`** (keys `notes_dir` and `template`). Nothing is passed on the command line and installing asks nothing. That is what lets a system-wide package (a `.deb`) install Postit without knowing anything about the user. At startup, if the file is missing or unparseable, or either path doesn't exist, the **Settings dialog opens before the note dialog**, and cancelling it exits the app. The note dialog also has a **Settings** button for changing either path later.

The modules are heavily commented, and the comments record *why*. Read the comments at a site before "simplifying" it. See `README.md` for the template reference and `docs/USER_GUIDE.md` for end-user documentation.

## Running

```bash
./start.sh
./lint.sh
```

`start.sh` runs through `uv`; `pyproject.toml` sets `package = false`, so there is no install step and edits are live. There is deliberately no automated test suite; `./lint.sh` (ruff, pyright, `bash -n`) must stay clean.

## Layout

Top level: `postit/` (the app), `docs/` (the User Guide and its screenshot; not shipped), `packaging/` (`build-deb.sh`, the `.desktop` template, and `icons/` with `source.png`, `make-icons.py` and the generated hicolor PNGs), `start.sh` and `lint.sh`. Tool settings live in `ruff.toml` and `pyrightconfig.json`, so `pyproject.toml` stays the runtime dependency list. The package, split so that everything testable is free of Qt:

- `__init__.py` — `APP_NAME` and `UI_POINT_SIZE`, the size of the buttons and the Settings dialog's labels and fields.
- `note.py` — **the model, no Qt imports.** Timestamp formatting, template rendering, and the file write. Two details worth not "simplifying":
  - `format_date`/`format_time` build their strings by hand instead of using strftime's `%-m`/`%-I`, which are a glibc extension. The formats (`8/21/2026`, `1:05 PM`) are what the Timex Extension reads, and are deliberately different from the sortable filename timestamp.
  - `write_note` walks `candidate_paths()` (the stamped name, then `-2`, `-3`, …) and opens each in exclusive-create (`"x"`) mode, so a note is never silently overwritten — not even by one written in the same instant. It does **not** create the notes folder; see "Deliberate behavior".
- `config.py` — **the settings, no Qt imports.** The same YAML-config approach as the sibling `sonar` project. Its pieces:
  - `Settings` (two absolute paths; `""` means not set).
  - `load_settings()`, which returns the settings plus an error message instead of raising. A missing file is no error; an unreadable or malformed one is, because the Settings dialog opened over it will replace the file on Save and needs to say so.
  - `save_settings()`, atomic (temp file + `os.replace`, symlinks followed), so a failed write leaves the old file whole.
  - `problem()`: the **single validity rule** (the folder is an existing directory, the template an existing file), shared by the startup check and the dialog's Save button. Don't let the two drift apart.
  - `DATA_DIR` (`postit/data/`) and `BUNDLED_TEMPLATE`, the shipped `data/note-template.md`. The template is only filled into an *empty* template field as a starting point, and never used silently.
- `style.py` — the shared look: `BUTTON_STYLE`, `field_background()`, `field_border()`. Imports nothing from the package except `UI_POINT_SIZE`, so either dialog can use it without importing the other.
  - `field_background()` and `field_border()` derive their colors from the live `QPalette` at build time — not import time, since no theme is attached until `QApplication` exists — so they track light and dark desktop themes. `field_border()` lightens by default but **darkens** when lightening does nothing, which is the case on a light theme where `Base` is already white and `lighter()` saturates.
- `note_dialog.py` — `NoteDialog`.
  - **Layout.** The text area and the button row sit directly on the `QDialog` in a single layout with one 10px margin — no inner frame, no second level of padding; the window decoration's own frame is the only border the app has. The button row is an explicit `QHBoxLayout`, with Settings at the left and the Save/Cancel `QDialogButtonBox` at the right, so Settings' position doesn't depend on the box's per-platform button ordering.
  - **Font.** The note is set in the desktop's fixed-width face at `NOTE_POINT_SIZE`, larger than `UI_POINT_SIZE`. The family is asked for through `QFontDatabase.systemFont(FixedFont)` rather than named, so don't replace it with a hardcoded "Monospace"/"DejaVu Sans Mono" that may not be installed. Wrapping stays at the widget edge — monospace here is for a steadier, more legible note, not for lining up columns — so there is still no horizontal scrollbar.
  - **Scroll bar.** The vertical scroll bar is drawn at twice the desktop's own thickness through `windowchrome.apply_scrollbars()` — a shared decision, not a Postit-local one, so change it in the library or not at all (`../windowchrome/README.md` §9). It is handed `field_background()` explicitly, because the field is *not* painted in the palette's `Base` the library would otherwise assume, and the groove would read as a darker stripe against it.
- `settings_dialog.py` — `SettingsDialog`: two path fields, each with a Browse… button (`QFileDialog.getExistingDirectory` / `getOpenFileName`, the pickers `sonar` uses).
  - Save is disabled while `problem()` has something to say, and a hint label under the fields shows that message.
  - `_save()` closes the dialog only if the write succeeded.
- `__main__.py` — argparse (no arguments; kept for `--help`), `QApplication`, the `sys.excepthook` that turns an exception escaping a slot into a dialog instead of a process abort (which would lose the typed note), `ensure_settings()`, run the note dialog, write the note, report failures with a `QMessageBox` (a bare stderr traceback is invisible when launched from a desktop icon). Settings are **read again after the note dialog is accepted**, so a change made through the Settings button applies to the note being saved.
- `data/` — `note-template.md` (the bundled template) and `postit.png` (the window icon, which a checkout run needs because no desktop entry supplies one). Found through `config.DATA_DIR`.

## Things that will bite you

- **The wide scroll bar lives in `windowchrome`, not here — read `../windowchrome/README.md` §9 before touching it.** `windowchrome` is a sibling library (`[tool.uv.sources]` in `pyproject.toml` points at `../windowchrome`, editable, so an edit there is live here with no reinstall; the checkout has to *be* a sibling or `uv run` fails outright). `apply_scrollbars()` in `note_dialog.py` is the only thing Postit takes from it, and it has no setup call or ordering rule.

- **Don't set `applicationDisplayName`.** Qt appends it to every window title that isn't exactly it, which doubled "Postit — could not save" into "Postit — could not save — Postit". Each window spells out its own full title (`"Settings — Postit"`, `"Postit — internal error"`, …).

- **The title bar and window frame are the platform's own, and deliberately unstyled.** They used to be colored through `windowchrome`, which on Wayland meant choosing Qt's `bradient` decoration plugin and repurposing the application palette's `Window`/`WindowText` roles and the application font for it, then handing them back to every widget through an application-wide event filter. That was removed as too fragile — it rested on undocumented plugin internals and leaked into unrelated code. Do not reintroduce title-bar or frame coloring, and don't nest the dialog's content in a bordered frame: the decoration's own frame is the only border the design wants.

- **The `.deb` is built by `packaging/build-deb.sh`.** It copies the whole `postit/` (including `data/`) and `windowchrome/` trees, installs the hicolor icons, then smoke-tests the stage before packing: every intra-package import resolves to a staged file, the data files exist, the bundled template renders with every placeholder substituted, and the modules import (only the Qt-free ones when the system python3 has no PyQt6). Regenerate icons with `uv run --no-project --with pillow packaging/icons/make-icons.py`.
  - PyQt6 and PyYAML come from apt (`python3-pyqt6`, `python3-yaml`) and are not bundled. A new third-party dependency needs a Debian package, and must be added to the script's `Depends:` as well as to `pyproject.toml`.
  - The launcher runs `python3 -I`, so neither `PYTHONPATH` nor pip user installs can shadow the system packages.
  - `__main__` calls `setDesktopFileName("postit")` to tie the window to `postit.desktop`, so renaming either one breaks the icon in the dock.

## Deliberate behavior

- **No Ctrl+Enter save accelerator.** This is a free-form note, so Enter always means a newline. Don't add one.
- **No desktop notification** on save. The bash version had one; it was explicitly removed in this rewrite.
- Save is disabled while the text is blank or whitespace-only, mirroring the bash version's `[ -n "$NOTE_CONTENT" ]` check.
- **Cancel in the Settings dialog means two different things.** At startup it exits the app (the user reruns Postit to try again). From the note dialog's Settings button it only closes Settings and returns to the note.
- **Settings' Save requires both paths to already exist, and the notes folder is never created on demand** — not by Settings, not by `write_note`. The folder picker can create one.
- **No command-line notes folder.** The config file is the only source of truth, so there is never a question of which folder is in effect.

## Working in this repo

* Do not commit changes to 'git' repository, or offer to. Only the Human developer will do commits.
