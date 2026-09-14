"""The config file: where notes go and which template they're built from.

Deliberately Qt-free, like `note.py`: loading, saving and validating the
settings are plain Python, so they can be exercised without a display.
`settings.py` is the dialog that edits them, `__main__.py` the startup check.

One YAML file at `CONFIG_PATH` holds both settings. `Settings` is that file as
a record; `load_settings()` and `save_settings()` are the whole of what the
rest of the app needs, and `problem()` is the one rule for "good enough to
write a note with", shared by the startup check and the dialog's Save button.
"""

from __future__ import annotations

import os
from typing import NamedTuple

import yaml

CONFIG_PATH = os.path.expanduser("~/.config/postit/postit-config.yaml")

# The program's own folder, and the template shipped in it. That template is
# only ever a suggestion: the Settings dialog fills it into an empty template
# field, so a first run needs nothing chosen but the notes folder.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BUNDLED_TEMPLATE = os.path.join(PROJECT_ROOT, "note-template.md")

HEADER = "# Postit configuration. Edit here or from the Settings button.\n"


class Settings(NamedTuple):
    """Both settings, as absolute paths. An empty string means "not set"."""

    notes_dir: str = ""
    template: str = ""


def normalize(path: str) -> str:
    """`path` with `~` expanded and made absolute; "" stays "" (not set)."""
    path = path.strip()
    if not path:
        return ""
    return os.path.abspath(os.path.expanduser(path))


def load_settings() -> tuple[Settings, str | None]:
    """The saved settings, plus a message if the file could not be read.

    A missing file is not an error — it is simply the first run — and reports
    none. An unreadable or malformed file does, because the settings dialog
    opened over it will *replace* the file on Save, and whoever broke it by
    hand needs to know that before they overwrite it.

    Every failure still yields a usable (empty) `Settings`.
    """
    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except FileNotFoundError:
        return Settings(), None
    except (OSError, yaml.YAMLError) as exc:
        return Settings(), str(exc)
    # safe_load returns None for an empty file, and could return a scalar or a
    # list for a file that parses but isn't a mapping.
    if loaded is None:
        return Settings(), None
    if not isinstance(loaded, dict):
        return Settings(), "The config file does not contain a YAML mapping."

    def path_value(key: str) -> str:
        value = loaded.get(key)
        return normalize(value) if isinstance(value, str) else ""

    return Settings(notes_dir=path_value("notes_dir"), template=path_value("template")), None


def save_settings(settings: Settings) -> None:
    """Write `settings` to `CONFIG_PATH`, replacing whatever was there.

    Raises OSError if the directory can't be created or the file written.
    """
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    # safe_dump rather than an f-string, so a path containing a colon, a quote
    # or a leading `~` is quoted the way YAML needs it to be.
    body = yaml.safe_dump(
        {"notes_dir": settings.notes_dir, "template": settings.template},
        sort_keys=False,
        allow_unicode=True,
    )
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        handle.write(HEADER + body)


def problem(settings: Settings) -> str | None:
    """The first thing stopping `settings` from being used, or None if nothing.

    Both must exist already: the folder picker can create a folder, so there
    is no need to guess at creating one from a typo.
    """
    if not settings.notes_dir:
        return "Choose a folder to save notes into."
    if not os.path.isdir(settings.notes_dir):
        return "The notes folder does not exist."
    if not settings.template:
        return "Choose a template file."
    if not os.path.isfile(settings.template):
        return "The template file does not exist."
    return None


def nearest_existing_dir(path: str) -> str:
    """The closest existing directory at or above `path`, else the home folder.

    Where a picker starts: a field holding a folder that has since been moved
    still opens the chooser near where it used to be.
    """
    path = normalize(path)
    while path:
        if os.path.isdir(path):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return os.path.expanduser("~")
