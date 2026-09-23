"""Postit: a one-dialog utility for jotting a timestamped markdown note."""

APP_NAME = "Postit"

# A postit note is scribbled on and dismissed in a few seconds, not studied, so
# the UI runs a few points above the desktop default. This is the chrome size —
# the buttons, and the Settings dialog's labels and fields — and the floor the
# note text sits above (see `NOTE_POINT_SIZE` in `note_dialog.py`).
UI_POINT_SIZE = 15
