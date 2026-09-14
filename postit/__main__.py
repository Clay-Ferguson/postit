"""Entry point: python -m postit

The notes folder and template come from ~/.config/postit/postit-config.yaml,
chosen in the Settings dialog that opens on first run.
"""

from __future__ import annotations

import argparse
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from . import APP_NAME
from .config import CONFIG_PATH, PROJECT_ROOT, Settings, load_settings, problem
from .dialog import NoteDialog
from .note import TemplateNotFound, write_note
from .settings import SettingsDialog

ICON = os.path.join(PROJECT_ROOT, "postit.png")


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


def main() -> int:
    # No arguments any more, but argparse stays so --help says what Postit is,
    # and so a stale launcher that still passes a notes folder fails loudly
    # instead of being quietly ignored.
    parser = argparse.ArgumentParser(prog="postit", description=__doc__)
    parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
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
    try:
        if issue:
            raise OSError(f"{CONFIG_PATH}\n\n{issue}")
        path = write_note(settings.notes_dir, settings.template, dialog.text())
    except (TemplateNotFound, OSError) as exc:
        # The dialog is gone by now, so a bare stderr traceback would vanish
        # with it when launched from the icon; report it where it can be seen.
        QMessageBox.critical(None, f"{APP_NAME} - could not save", str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Note saved to: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
