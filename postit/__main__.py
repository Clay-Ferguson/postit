"""Entry point: python -m postit

The notes folder and template come from ~/.config/postit/postit-config.yaml,
chosen in the Settings dialog that opens on first run.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from . import APP_NAME
from .config import CONFIG_PATH, DATA_DIR, Settings, load_settings, problem
from .note import TemplateNotFound, write_note
from .note_dialog import NoteDialog
from .settings_dialog import SettingsDialog

# The window's own icon. An installed copy also gets its dock icon from the
# themed icons the .deb installs; a checkout run has only this.
ICON = os.path.join(DATA_DIR, "postit.png")

# How much of a traceback the internal-error dialog shows.
TRACEBACK_LINES = 12


def ensure_settings() -> Settings | None:
    """Settings good enough to write a note with, or None to exit.

    Valid saved settings are used as they are. Anything else opens the Settings
    dialog before the note dialog, so nobody types a note that has nowhere to
    go. That covers a first run, a folder or template that has since
    disappeared, and a config file that won't parse. Cancelling that dialog is
    how the user declines, and the app exits rather than asking again.
    """
    settings, error = load_settings()
    if error is None and problem(settings) is None:
        return settings

    dialog = SettingsDialog(settings, error)
    dialog.show()
    dialog.activateWindow()
    dialog.raise_()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.settings()


def _report_unhandled(kind, value, trace) -> None:
    """Show an exception that escaped a slot, instead of dying of it.

    PyQt6 aborts the whole process when a Python exception leaves a slot and
    no `sys.excepthook` has been installed — a bug behind the Settings or a
    Browse… button would close Postit outright and take the typed note with
    it, with nothing to show for it when launched from a desktop icon. With a
    hook installed PyQt calls it instead and carries on, so the bug is
    reported and the note is still there to save.
    """
    text = "".join(traceback.format_exception(kind, value, trace))
    if sys.__stderr__ is not None:
        sys.__stderr__.write(text)
    if QApplication.instance() is None:
        return
    # The tail of the traceback, where the failing line is: a desktop launch
    # has no terminal for the stderr copy above to reach.
    tail = "\n".join(text.rstrip().splitlines()[-TRACEBACK_LINES:])
    QMessageBox.critical(
        None,
        f"{APP_NAME} — internal error",
        f"Something went wrong inside {APP_NAME}. The note should still be "
        f"there to save.\n\n{tail}",
    )


def _save_failed(message: str) -> int:
    """Report a note that could not be written, and the exit status for it."""
    # The dialog is gone by now, so a bare stderr message would vanish with it
    # when launched from the icon; report it where it can be seen.
    QMessageBox.critical(None, f"{APP_NAME} — could not save", message)
    print(f"Error: {message}", file=sys.stderr)
    return 1


def main() -> int:
    # No arguments any more, but argparse stays so --help says what Postit is,
    # and so a stale launcher that still passes a notes folder fails loudly
    # instead of being quietly ignored.
    parser = argparse.ArgumentParser(prog="postit", description=__doc__)
    parser.parse_args()

    app = QApplication(sys.argv)
    sys.excepthook = _report_unhandled
    app.setApplicationName(APP_NAME)
    # applicationDisplayName is deliberately NOT set. Every platform backend
    # runs window titles through QPlatformWindow::formatWindowTitle(), which
    # appends the display name to any title that isn't exactly it — so with
    # it set, "Postit — could not save" reached the title bar as
    # "Postit — could not save — Postit". Each window spells out its own full
    # title instead.
    # Ties the window to postit.desktop, so the desktop shows our icon in the
    # dock and alt-tab instead of a generic one. Without it the Wayland app_id
    # is derived from argv[0] ("python3") and matches nothing.
    app.setDesktopFileName("postit")
    if os.path.isfile(ICON):
        app.setWindowIcon(QIcon(ICON))

    if ensure_settings() is None:
        print("Settings not saved - exiting.")
        return 0

    dialog = NoteDialog()
    dialog.show()
    dialog.activateWindow()
    dialog.raise_()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("Note cancelled - no file created.")
        return 0

    # Read again rather than reusing what ensure_settings() returned: the
    # Settings button may have changed either path while the note was typed.
    settings, error = load_settings()
    issue = error or problem(settings)
    if issue:
        return _save_failed(f"{CONFIG_PATH}\n\n{issue}")
    try:
        path = write_note(settings.notes_dir, settings.template, dialog.text())
    except (TemplateNotFound, OSError) as exc:
        return _save_failed(str(exc))

    print(f"Note saved to: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
