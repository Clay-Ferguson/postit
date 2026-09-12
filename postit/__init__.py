"""Postit: a one-dialog utility for jotting a timestamped markdown note."""

APP_NAME = "Postit"

# A postit note is scribbled on and dismissed in a few seconds, not studied, so
# the UI runs a few points above the desktop default. This is the chrome size —
# the dialog's buttons — and the floor the note text sits above.
UI_POINT_SIZE = 15

# The note itself is bigger again, and set in the desktop's fixed-width face
# (see `dialog.py`). Monospace faces read a shade smaller than a proportional
# one at the same point size, so the gap here is partly making that back.
NOTE_POINT_SIZE = 16
