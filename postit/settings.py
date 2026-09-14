"""The Settings dialog: the notes folder and the note template.

Two path fields, each with a Browse… button that opens the desktop's own
chooser. Save stays disabled until `config.problem()` has nothing to say about
what's typed — the same rule the startup check uses — and a hint under the
fields says what is still wrong, so the dialog explains itself when it opens
unasked on a first run.

Saving writes the config file and nothing else. `__main__` reads the file again
when the note is saved, so a change made from the note dialog's Settings button
applies to that note with nothing to hand back.
"""

from __future__ import annotations

import os
from html import escape

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import UI_POINT_SIZE
from .config import (
    BUNDLED_TEMPLATE,
    CONFIG_PATH,
    Settings,
    nearest_existing_dir,
    normalize,
    problem,
    save_settings,
)
from .dialog import BUTTON_STYLE

# Wide enough for a typical home-folder path without scrolling the field.
MIN_WIDTH = 640

# Vertical gaps: between one labelled field and the next, and between a label
# and its field. The second is smaller so the pair reads as one thing.
SECTION_SPACING = 14
LABEL_SPACING = 4


class SettingsDialog(QDialog):
    """Edit the notes folder and the template. Accepted only once saved."""

    def __init__(
        self,
        settings: Settings,
        load_error: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # Just "Settings": the application display name is set, and Qt appends
        # it to every window title, so this reaches the title bar as
        # "Settings — Postit".
        self.setWindowTitle("Settings")
        self.setMinimumWidth(MIN_WIDTH)
        # Set on the dialog so every label and field inherits it; the buttons
        # get the same size through BUTTON_STYLE, as in the note dialog.
        font = self.font()
        font.setPointSize(UI_POINT_SIZE)
        self.setFont(font)

        self._saved = settings
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(LABEL_SPACING)

        if load_error:
            # Shown first, because Save rewrites the file: whoever has a typo
            # in their YAML is looking at fields that don't reflect it. Escaped,
            # since the label is rich text and a YAML error is full of the
            # file's own punctuation.
            warning = QLabel(
                f"<b>{escape(CONFIG_PATH)} could not be read</b><br>"
                f"{escape(load_error)}<br>"
                "The fields below don't reflect that file; saving replaces it."
            )
            warning.setWordWrap(True)
            self._layout.addWidget(warning)

        template = settings.template
        if not template and os.path.isfile(BUNDLED_TEMPLATE):
            template = BUNDLED_TEMPLATE

        self._folder_edit = self._add_path_row(
            "Notes folder:", settings.notes_dir, self._browse_folder
        )
        self._template_edit = self._add_path_row(
            "Note template:", template, self._browse_template
        )

        self._layout.addSpacing(SECTION_SPACING - LABEL_SPACING)
        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._layout.addWidget(self._hint)

        self._layout.addStretch(1)
        self._layout.addSpacing(SECTION_SPACING - LABEL_SPACING)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(BUTTON_STYLE)
        self._save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self._layout.addWidget(buttons)

        self._validate()

    # -- construction ------------------------------------------------------

    def _add_path_row(self, label: str, value: str, browse) -> QLineEdit:
        """A caption, then a path field with a Browse… button beside it."""
        if self._layout.count():
            self._layout.addSpacing(SECTION_SPACING - LABEL_SPACING)
        self._layout.addWidget(QLabel(label))

        edit = QLineEdit(value)
        edit.textChanged.connect(self._validate)

        button = QPushButton("Browse…")
        button.setStyleSheet(BUTTON_STYLE)
        # Enter in a field should mean Save, not "open a chooser".
        button.setAutoDefault(False)
        button.clicked.connect(browse)
        # The padded button is taller than a bare line edit; matched, the two
        # read as one control.
        edit.setMinimumHeight(button.sizeHint().height())

        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(button)
        self._layout.addLayout(row)
        return edit

    # -- state -------------------------------------------------------------

    def _current(self) -> Settings:
        return Settings(
            notes_dir=normalize(self._folder_edit.text()),
            template=normalize(self._template_edit.text()),
        )

    def _validate(self) -> None:
        issue = problem(self._current())
        self._save_button.setEnabled(issue is None)
        self._hint.setText(issue or "")

    def settings(self) -> Settings:
        """What was saved — or, if the dialog was cancelled, what it opened with."""
        return self._saved

    # -- actions -----------------------------------------------------------

    def _browse_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Folder to save notes into",
            nearest_existing_dir(self._folder_edit.text()),
        )
        if chosen:
            self._folder_edit.setText(chosen)

    def _browse_template(self) -> None:
        current = normalize(self._template_edit.text())
        # Starting at the file itself preselects it; otherwise the nearest
        # folder that still exists.
        start = current if os.path.isfile(current) else nearest_existing_dir(current)
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Note template", start, "Markdown (*.md);;All files (*)"
        )
        if chosen:
            self._template_edit.setText(chosen)

    def _save(self) -> None:
        """Write both fields back, and close only if that worked."""
        settings = self._current()
        # Save is disabled while there's a problem, but a path can vanish
        # between the last edit and the click.
        issue = problem(settings)
        if issue:
            self._validate()
            return
        try:
            save_settings(settings)
        except OSError as exc:
            QMessageBox.warning(
                self, "Could not save settings", f"{CONFIG_PATH}\n\n{exc}"
            )
            return
        self._saved = settings
        self.accept()
