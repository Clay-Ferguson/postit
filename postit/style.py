"""The app's shared look: the button style and the note field's colors.

Anything used by more than one module lives here, so the Settings dialog never
has to import the note dialog just for a style. Styling only one module needs
stays in that module. Imports nothing from the package except `UI_POINT_SIZE`.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from . import UI_POINT_SIZE

BUTTON_STYLE = f"QPushButton {{ font-size: {UI_POINT_SIZE}pt; padding: 8px 20px; }}"


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
    that has to go. Setting any QSS on a widget (as the note dialog does, to
    paint the field with `field_background()`) opts it out of the style's
    native border too, so this is drawn explicitly rather than left to the theme.

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
