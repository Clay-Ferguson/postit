"""The note dialog: a text area, with Settings, Save and Cancel below it.

The window decoration draws its own frame around the whole window, so the
dialog adds no border of its own — the content sits directly on the QDialog
with one level of padding, nothing more.
"""

from __future__ import annotations

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from windowchrome import apply_scrollbars

from . import APP_NAME
from .config import load_settings
from .settings_dialog import SettingsDialog
from .style import BUTTON_STYLE, field_background, field_border

# The note is set larger than the UI around it, and in the desktop's fixed-width
# face. Monospace faces read a shade smaller than a proportional one at the same
# point size, so the gap above `UI_POINT_SIZE` is partly making that back.
NOTE_POINT_SIZE = 16

DIALOG_WIDTH = 700
DIALOG_HEIGHT = 500


class NoteDialog(QDialog):
    """A multi-line text area with Settings, Save and Cancel underneath it.

    Save stays disabled until there's something other than whitespace to save,
    so an empty note can never be written. Escape rejects the dialog, which is
    QDialog's own default behavior — nothing extra is wired up for it.

    Deliberately *no* Ctrl+Enter save accelerator: this is a free-form note, so
    Enter always just means a new line.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)

        # The note is set large and in the desktop's own fixed-width face, asked
        # for through QFontDatabase rather than named here, so it follows
        # whatever the system has configured instead of guessing at a family
        # that may not be installed. Lines still wrap at the widget edge — this
        # is prose in a monospace font, not code, so there is nothing worth a
        # horizontal scrollbar.
        self._text_edit = QPlainTextEdit()
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(NOTE_POINT_SIZE)
        self._text_edit.setFont(font)
        background = field_background()
        self._text_edit.setStyleSheet(
            f"background-color: {background.name()}; border: 1px solid {field_border()};"
        )
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        # Scroll bars at twice the desktop's own thickness, so they are easier
        # to grab with the mouse. Styled through the edit's own scroll bar
        # children, so the edit itself keeps its native rendering — and handed
        # the field's background, since that is not the palette's Base the
        # library would otherwise assume and the groove would read as a darker
        # stripe against the field. See `../windowchrome/README.md` §9.
        apply_scrollbars(self._text_edit, background)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(BUTTON_STYLE)
        self._save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Settings sits apart at the left, in a row of our own rather than in
        # the button box: where a box places an extra button varies by platform
        # style, and this one should never read as a third way to close the note.
        settings_button = QPushButton("Settings")
        settings_button.setStyleSheet(BUTTON_STYLE)
        settings_button.setAutoDefault(False)
        settings_button.clicked.connect(self._open_settings)

        button_row = QHBoxLayout()
        button_row.addWidget(settings_button)
        button_row.addStretch(1)
        button_row.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._text_edit)
        layout.addLayout(button_row)

        self._text_edit.textChanged.connect(self._validate)
        self._validate()
        self._text_edit.setFocus()

    def _validate(self) -> None:
        # A whitespace-only note would be a file with an empty body, so Save
        # stays disabled — the same check the bash version made with [ -n ... ].
        self._save_button.setEnabled(bool(self._text_edit.toPlainText().strip()))

    def _open_settings(self) -> None:
        """Change the notes folder or template without losing the note.

        Cancel here only closes the settings. Unlike at startup, there is a note
        to go back to. Nothing is handed back either way: `__main__` reads the
        config again when the note is saved.
        """
        settings, error = load_settings()
        SettingsDialog(settings, error, parent=self).exec()
        self._text_edit.setFocus()

    def text(self) -> str:
        """The typed note, exactly as entered apart from trailing whitespace."""
        return self._text_edit.toPlainText().rstrip()
