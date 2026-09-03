"""Postit: a one-dialog utility for jotting a timestamped markdown note."""

from windowchrome import ChromeTheme

APP_NAME = "Postit"

# A postit note is scribbled on and dismissed in a few seconds, not studied, so
# the UI runs a few points above the desktop default. This is the chrome size —
# the dialog's buttons — and the floor the note text sits above.
UI_POINT_SIZE = 15

# The note itself is bigger again, and set in the desktop's fixed-width face
# (see `dialog.py`). Monospace faces read a shade smaller than a proportional
# one at the same point size, so the gap here is partly making that back.
NOTE_POINT_SIZE = 16

# The window's title bar, and with it the thin frame the decoration draws down
# the sides and along the bottom. `windowchrome` owns both — see
# `../windowchrome/README.md` for why they are reachable at all (Wayland only,
# by repurposing three palette roles) and why their *size* is not.
#
# The library ships neutral defaults; this is Postit's override of them, and it
# deliberately matches the other apps here so they read as one family rather
# than as unrelated windows.
POSTIT_THEME = ChromeTheme(title_bg="#1369da")
