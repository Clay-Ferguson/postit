# Notes to AI Agents

## What this is

Postit is a PyQt6 desktop app that does exactly one thing: pop a dialog with a
text area, and on **Save** write what you typed into a timestamped markdown
file. There is no main window, no state, no config file — the dialog *is* the
application, and the process exits as soon as the note is written.

It's a rewrite of an older bash + zenity version (`../Postit--bash`), kept
behavior-for-behavior identical except that the old version's desktop
notification after saving was deliberately dropped.

The notes directory is a **command-line argument** (default `~/ferguson`).
`install.sh` prompts for it and bakes it into the desktop entry's `Exec=` line,
which is the same approach PyCommander uses for its `menu.yaml` path — nothing
is read from a fixed location.

## Architecture

Three modules, split so that everything testable is free of Qt:

- `postit/note.py` — **the model, no Qt imports.** Timestamp formatting,
  template rendering, and the file write. Can be exercised without a display.
  Two details worth not "simplifying":
  - `format_date`/`format_time` build their strings by hand instead of using
    strftime's `%-m`/`%-I`, which are a glibc extension. The formats
    (`8/21/2026`, `1:05 PM`) are what the Timex Extension reads, and are
    deliberately different from the sortable filename timestamp.
  - `unique_path` falls back to a `-2`, `-3`, … suffix when two notes land in
    the same second, so a note is never silently overwritten.
- `postit/dialog.py` — `NoteDialog`, plus the styling helpers it uses (no
  separate `style.py`: there is only one dialog to share them with). The content
  sits in a bordered `QFrame` rather than on the `QDialog` itself, because a
  QDialog won't reliably paint a stylesheet border. `field_background()` and
  `field_border()` derive their colors from the live `QPalette` at build time —
  not import time, since no theme is attached until `QApplication` exists — so
  they track light and dark desktop themes. `field_border()` lightens by
  default but **darkens** when lightening does nothing, which is the case on a
  light theme where `Base` is already white and `lighter()` saturates.
- `postit/__main__.py` — argparse, `QApplication`, run the dialog, write the
  note, report failures with a `QMessageBox` (a bare stderr traceback is
  invisible when launched from a desktop icon).

## Deliberate non-features

- **No Ctrl+Enter save accelerator.** This is a free-form note, so Enter always
  means a newline. Don't add one.
- **No desktop notification** on save. The bash version had one; it was
  explicitly removed in this rewrite.
- Save is disabled while the text is blank or whitespace-only, mirroring the
  bash version's `[ -n "$NOTE_CONTENT" ]` check.

See `README.md` for the template reference and `USER_GUIDE.md` for end-user
documentation.

## Working in this repo

* Do not commit changes to 'git' repository, or offer to. Only the Human
  developer will do commits.
