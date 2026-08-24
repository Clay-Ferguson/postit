"""The one dialog: a text area, Save and Cancel.

The styling helpers live here rather than in a module of their own — Postit has
exactly one dialog, so there is nothing to share them with.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, UI_POINT_SIZE

# A plain QDialog's outer edge is easy to lose against the desktop behind it,
# so the real content sits inside a bordered QFrame instead — a QDialog won't
# reliably paint a stylesheet border of its own, but a QFrame always will.
BORDER_STYLE = "#dialogFrame { border: 1px solid #a0a0a0; border-radius: 6px; }"
BUTTON_STYLE = f"QPushButton {{ font-size: {UI_POINT_SIZE}pt; padding: 8px 20px; }}"

DIALOG_WIDTH = 700
DIALOG_HEIGHT = 500


def field_background() -> str:
    """A background a shade lighter than the theme's default input color.

    Computed from the live application palette (rather than a fixed hex) so it
    lightens relative to whatever the desktop theme's own input background is,
    instead of assuming a light or a dark theme. Queried lazily — at dialog-build
    time, not import time — since no theme is attached to the palette until
    QApplication exists.
    """
    base = QApplication.palette().color(QPalette.ColorRole.Base)
    return base.lighter(130).name()


def field_border() -> str:
    """A border that contrasts with the field's own background, whichever way
    that has to go. Setting any QSS on a widget (as `field_background` does)
    opts it out of the style's native border too, so this is drawn explicitly
    rather than left to the theme.

    Lightening is tried first, to match the lightened background — but both
    `lighter()` and `darker()` work in HSV, by scaling the value component,
    so each is a no-op at the end of the scale it is heading toward. On a
    light theme the Base color is already white and lightening returns white
    again, leaving an outline indistinguishable from the field it is supposed
    to outline; darkening covers that case. On a pure black Base (some
    high-contrast and OLED themes) the value component is zero and *neither*
    direction moves, so the last resort is a fixed gray.
    """
    background = QColor(field_background())
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

        # Notes are prose, so this keeps the theme's proportional font and wraps
        # at the widget edge — unlike a code editor, there are no columns to
        # line up and nothing worth a horizontal scrollbar.
        self._text_edit = QPlainTextEdit()
        font = self._text_edit.font()
        font.setPointSize(UI_POINT_SIZE)
        self._text_edit.setFont(font)
        self._text_edit.setStyleSheet(
            f"background-color: {field_background()}; border: 1px solid {field_border()};"
        )
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(BUTTON_STYLE)
        self._save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        frame = QFrame(self)
        frame.setObjectName("dialogFrame")
        frame.setStyleSheet(BORDER_STYLE)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(24, 24, 24, 24)
        frame_layout.setSpacing(14)
        frame_layout.addWidget(self._text_edit)
        frame_layout.addWidget(buttons)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.addWidget(frame)

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
