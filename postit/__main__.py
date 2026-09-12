"""Entry point: python -m postit [NOTES_DIR]"""

from __future__ import annotations

import argparse
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from . import APP_NAME
from .dialog import NoteDialog
from .note import TemplateNotFound, write_note

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ICON = os.path.join(PROJECT_ROOT, "postit.png")
TEMPLATE = os.path.join(PROJECT_ROOT, "note-template.md")

DEFAULT_NOTES_DIR = "~/ferguson"


def main() -> int:
    # notes_dir is nargs="?" rather than required: argparse's own handling of a
    # missing required argument prints to stderr and exits before a QApplication
    # exists, which is invisible when launched from a desktop icon rather than a
    # terminal. Given a default instead, there is no such failure to report.
    parser = argparse.ArgumentParser(prog="postit", description=__doc__)
    parser.add_argument(
        "notes_dir",
        nargs="?",
        default=DEFAULT_NOTES_DIR,
        metavar="NOTES_DIR",
        help=f"directory to save notes into, created if it doesn't exist (default: {DEFAULT_NOTES_DIR})",
    )
    args = parser.parse_args()
    notes_dir = os.path.abspath(os.path.expanduser(args.notes_dir))

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    # Ties the window to postit.desktop, so the desktop shows our icon in the
    # dock and alt-tab instead of a generic one. Without it the Wayland app_id
    # is derived from argv[0] ("python3") and matches nothing.
    app.setDesktopFileName("postit")
    if os.path.isfile(ICON):
        app.setWindowIcon(QIcon(ICON))

    dialog = NoteDialog()
    dialog.show()
    dialog.activateWindow()
    dialog.raise_()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("Note cancelled - no file created.")
        return 0

    try:
        path = write_note(notes_dir, TEMPLATE, dialog.text())
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
