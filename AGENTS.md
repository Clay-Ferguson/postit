# Notes to AI Agents

## What this is

Postit is a PyQt6 desktop app that does exactly one thing: pop a dialog with a text area, and on **Save** write what you typed into a timestamped markdown file. There is no main window, no state, no config file — the dialog *is* the application, and the process exits as soon as the note is written.

It's a rewrite of an older bash + zenity version (`../Postit--bash`), kept behavior-for-behavior identical except that the old version's desktop notification after saving was deliberately dropped.

The notes directory is a **command-line argument** (default `~/ferguson`). `install.sh` prompts for it and bakes it into the desktop entry's `Exec=` line, which is the same approach PyCommander uses for its `menu.yaml` path — nothing is read from a fixed location.

## Architecture

Three modules, split so that everything testable is free of Qt:

- `postit/note.py` — **the model, no Qt imports.** Timestamp formatting, template rendering, and the file write. Can be exercised without a display. Two details worth not "simplifying":
  - `format_date`/`format_time` build their strings by hand instead of using strftime's `%-m`/`%-I`, which are a glibc extension. The formats (`8/21/2026`, `1:05 PM`) are what the Timex Extension reads, and are deliberately different from the sortable filename timestamp.
  - `unique_path` falls back to a `-2`, `-3`, … suffix when two notes land in the same second, so a note is never silently overwritten.
- `postit/dialog.py` — `NoteDialog`, plus the styling helpers it uses (no separate `style.py`: there is only one dialog to share them with). The text area and the button box sit directly on the `QDialog` in a single layout with one 10px margin — no inner frame, no second level of padding; the window decoration's own frame is the only border the app has. The note is set in the desktop's fixed-width face at `NOTE_POINT_SIZE`, larger than the `UI_POINT_SIZE` the buttons use; the family is asked for through `QFontDatabase.systemFont(FixedFont)` rather than named, so don't replace it with a hardcoded "Monospace"/"DejaVu Sans Mono" that may not be installed. Wrapping stays at the widget edge — monospace here is for a steadier, more legible note, not for lining up columns, so there is still no horizontal scrollbar. The vertical scroll bar is drawn at twice the desktop's own thickness through `windowchrome.apply_scrollbars()` — a shared decision, not a Postit-local one, so change it in the library or not at all (`../windowchrome/README.md` §9). It is handed `field_background()` explicitly, because the field is *not* painted in the palette's `Base` the library would otherwise assume, and the groove would read as a darker stripe against it. `field_background()` and `field_border()` derive their colors from the live `QPalette` at build time — not import time, since no theme is attached until `QApplication` exists — so they track light and dark desktop themes. `field_border()` lightens by default but **darkens** when lightening does nothing, which is the case on a light theme where `Base` is already white and `lighter()` saturates.
- `postit/__main__.py` — argparse, `QApplication`, run the dialog, write the note, report failures with a `QMessageBox` (a bare stderr traceback is invisible when launched from a desktop icon). Also the two `windowchrome` setup calls, which are order-sensitive — see below.

## Things that will bite you

- **The window chrome lives in `windowchrome`, not here — read `../windowchrome/README.md` before touching any of it.** The colored title bar — and with it the thin frame the decoration draws down the sides and along the bottom — is a sibling library (`[tool.uv.sources]` in `pyproject.toml` points at `../windowchrome`, editable, so an edit there is live here with no reinstall; the checkout has to *be* a sibling or `uv run` fails outright). Its README carries the whole of what was measured: that the bar is colorable only on Wayland and only by repurposing three application palette roles; that `libadwaita.so` links no `QPalette` symbol at all while `bradient` does, which is what `QT_WAYLAND_DECORATION` is choosing between; that the decoration's `QMargins{3, 30, 3, 3}` are compiled-in constants, so neither the bar's height nor the frame's 3px is adjustable; and that giving a widget a stylesheet severs its palette inheritance, which is why an application event filter hands the body colors back — not hypothetical here, since the text area and the button box are both styled.

  What this app owes it, and what will break if it is forgotten: `windowchrome.configure(POSTIT_THEME)` **before** `QApplication` and `windowchrome.install(app)` **after** it — both in `__main__`, and both order-sensitive, the first because the decoration plugin is chosen by an environment variable read inside that constructor. That is the whole of the *chrome* integration: two calls, and nothing about the dialog's layout changes.

  The library is also where the wide scroll bars come from — `apply_scrollbars()` in `dialog.py`, which has no ordering rule and nothing to do with the title bar. It reads `Base`, not `Window`, so the caution below applies to it too and costs nothing.

  `POSTIT_THEME` is in `postit/__init__.py`, beside `APP_NAME`, `UI_POINT_SIZE` and `NOTE_POINT_SIZE`. It matches the other apps here deliberately.

  Nothing in this app derives a color from the palette's `Window` or `WindowText` roles, so the `body_window_color()` / `body_text_color()` rule the library states costs nothing here — `field_background()` reads `Base`, which the title bar never touches. Keep it that way: a new color derived from `Window` would come out tinted with the title bar blue.

  The `QMessageBox` on a failed save deliberately calls none of this and keeps the title bar's colors, being transient.

  The library briefly also painted a thicker border just inside the window (`bordered_body()`), and this dialog once drew a gray `QFrame` border of its own inside that. Both are gone: the decoration's own 3px frame, which takes the title bar's color for free, is the only border the design wants. Do not reintroduce either one, and don't nest the content in a frame again.

## Deliberate non-features

- **No Ctrl+Enter save accelerator.** This is a free-form note, so Enter always means a newline. Don't add one.
- **No desktop notification** on save. The bash version had one; it was explicitly removed in this rewrite.
- Save is disabled while the text is blank or whitespace-only, mirroring the bash version's `[ -n "$NOTE_CONTENT" ]` check.

See `README.md` for the template reference and `USER_GUIDE.md` for end-user documentation.

## Working in this repo

* Do not commit changes to 'git' repository, or offer to. Only the Human developer will do commits.
