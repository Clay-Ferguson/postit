"""The one dialog: a text area, Save and Cancel.

The styling helpers live here rather than in a module of their own — Postit has
exactly one dialog, so there is nothing to share them with.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFontDatabase, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from windowchrome import apply_scrollbars

from . import APP_NAME, NOTE_POINT_SIZE, UI_POINT_SIZE

# The window decoration draws its own frame around the whole window (see
# `../windowchrome/README.md`), so the dialog adds no border of its own — the
# content sits directly on the QDialog with one level of padding, nothing more.
BUTTON_STYLE = f"QPushButton {{ font-size: {UI_POINT_SIZE}pt; padding: 8px 20px; }}"

DIALOG_WIDTH = 700
DIALOG_HEIGHT = 500


def field_background() -> QColor:
    """A background a shade lighter than the theme's default input color.

    Computed from the live application palette (rather than a fixed hex) so it
    lightens relative to whatever the desktop theme's own input background is,
    instead of assuming a light or a dark theme. Queried lazily — at dialog-build
    time, not import time — since no theme is attached to the palette until
    QApplication exists.

    Returned as a QColor rather than a hex string because most of what wants
    it wants the color: `field_border()` derives from it and `apply_scrollbars`
    is handed it. Only the stylesheet needs `.name()`.
    """
    base = QApplication.palette().color(QPalette.ColorRole.Base)
    return base.lighter(130)


def field_border() -> str:
    """A border that contrasts with the field's own background, whichever way
    that has to go. Setting any QSS on a widget (as the dialog does, to paint
    the field with `field_background()`) opts it out of the style's native
    border too, so this is drawn explicitly rather than left to the theme.

    Lightening is tried first, to match the lightened background — but both
    `lighter()` and `darker()` work in HSV, by scaling the value component,
    so each is a no-op at the end of the scale it is heading toward. On a
    light theme the Base color is already white and lightening returns white
    again, leaving an outline indistinguishable from the field it is supposed
    to outline; darkening covers that case. On a pure black Base (some
    high-contrast and OLED themes) the value component is zero and *neither*
    direction moves, so the last resort is a fixed gray.
    """
    background = field_background()
    lightened = background.lighter(140)
    if lightened != background:
        return lightened.name()
    darkened = background.darker(115)
    if darkened != background:
        return darkened.name()
    return "#2e2e2e"


class NoteDialog(QDialog):
    """A multi-line text area with Save and Cancel underneath it.

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._text_edit)
        layout.addWidget(buttons)

        self._text_edit.textChanged.connect(self._validate)
        self._validate()
        self._text_edit.setFocus()

    def _validate(self) -> None:
        # A whitespace-only note would be a file with an empty body, so Save
        # stays disabled — the same check the bash version made with [ -n ... ].
        self._save_button.setEnabled(bool(self._text_edit.toPlainText().strip()))

    def text(self) -> str:
        """The typed note, exactly as entered apart from trailing whitespace."""
        return self._text_edit.toPlainText().rstrip()
