"""Turning typed text into a note file on disk.

Deliberately Qt-free: everything here is plain Python, so the filename,
template and timestamp rules can be exercised without a display attached.
`note_dialog.py` handles the GUI, `__main__.py` wires the two together.
"""

from __future__ import annotations

import datetime as dt
import itertools
import os
from collections.abc import Iterator

from .birthtime import birth_time_ns

# The filename timestamp is shell-friendly: no slashes, no spaces, no colons.
# Its time is 12-hour with a trailing `-AM`/`-PM`, e.g.
# `note-2026-08-21--01-05-07-PM.md`. The date and time written *into* the note
# are a different, more readable pair of formats (see `format_date`/
# `format_time`) — they're what the Timex Extension reads, so they must keep
# their slashes and AM/PM.
FILENAME_PREFIX = "" # Now going with no template, instead of "note-"
FILENAME_EXT = ".md"

DATE_PLACEHOLDER = "{date}"
TIME_PLACEHOLDER = "{time}"
CONTENT_PLACEHOLDER = "{content}"


class TemplateNotFound(Exception):
    """The note template file is missing or unreadable."""


def format_date(when: dt.datetime) -> str:
    """`8/21/2026` — month and day unpadded, for Timex Extension compatibility.

    Built by hand rather than with strftime's `%-m`/`%-d`, which are a glibc
    extension: they happen to work on Linux (where the bash version used them)
    but silently produce the wrong thing elsewhere.
    """
    return f"{when.month}/{when.day}/{when.year}"


def format_time(when: dt.datetime) -> str:
    """`1:05 PM` — 12-hour, unpadded hour, for Timex Extension compatibility."""
    hour = when.hour % 12 or 12
    meridiem = "AM" if when.hour < 12 else "PM"
    return f"{hour}:{when.minute:02d} {meridiem}"


def filename_stamp(when: dt.datetime) -> str:
    """`2026-08-21--01-05-07-PM` — the timestamp part of a note's filename.

    The meridiem is built by hand rather than with strftime's `%p`, which
    follows the locale (and Qt sets the locale from the environment), so it
    could come out as something other than AM/PM, or as nothing at all.
    """
    hour = when.hour % 12 or 12
    meridiem = "AM" if when.hour < 12 else "PM"
    return f"{when:%Y-%m-%d}--{hour:02d}-{when:%M-%S}-{meridiem}"


def render(template: str, content: str, when: dt.datetime) -> str:
    """Substitute the three placeholders in `template`.

    str.replace treats both arguments literally, so note text containing `&`,
    backslashes or anything else regex- or sed-like passes through untouched.
    (The bash version had to split the template on each placeholder and
    concatenate the pieces, because bash's `${var//pat/rep}` reads a literal
    `&` in the replacement as "insert the matched text".)
    """
    rendered = template.replace(DATE_PLACEHOLDER, format_date(when))
    rendered = rendered.replace(TIME_PLACEHOLDER, format_time(when))
    # Content goes last so a note that happens to mention "{date}" is left alone.
    return rendered.replace(CONTENT_PLACEHOLDER, content)


def read_template(template_path: str) -> str:
    try:
        with open(template_path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise TemplateNotFound(f"Template not found: {template_path}\n\n{exc}") from exc


def candidate_paths(notes_dir: str, when: dt.datetime) -> Iterator[str]:
    """Paths for a note stamped `when`, in the order they should be tried.

    The timestamp is only second-resolution, so two notes saved in the same
    second would collide. Rather than overwrite the first one, the second
    becomes `<stamp>-2.md`, the third `-3`, and so on.
    """
    stem = FILENAME_PREFIX + filename_stamp(when)
    yield os.path.join(notes_dir, stem + FILENAME_EXT)
    for suffix in itertools.count(2):
        yield os.path.join(notes_dir, f"{stem}-{suffix}{FILENAME_EXT}")


def write_note(
    notes_dir: str, template_path: str, content: str, when: dt.datetime | None = None
) -> str:
    """Render `content` into the template and save it. Returns the path written.

    An empty `template_path` means no template: the note is just `content`.

    The notes folder must already exist; it is never created here (see
    `config.problem()`). Each candidate name is opened in exclusive-create mode,
    so checking that a name is free and taking it are one step, and a note can
    never land on top of another, even one written in the same instant.

    Raises TemplateNotFound if the template is missing, or OSError if the file
    can't be written.
    """
    when = when or dt.datetime.now()
    template = read_template(template_path) if template_path else CONTENT_PLACEHOLDER
    body = render(template, content, when)
    if not body.endswith("\n"):
        body += "\n"

    for path in candidate_paths(notes_dir, when):
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(body)
        except FileExistsError:
            continue
        return path
    raise AssertionError("unreachable: candidate_paths() never ends")


def latest_note(notes_dir: str) -> str | None:
    """The most recently *created* `.md` file in `notes_dir`, or None if none.

    Chosen by each file's birth time alone — not its modification time, and not
    the timestamp in its name, so a note renamed or written by something other
    than Postit counts just the same. Only the folder itself is searched, not
    its subfolders. Two files born in the same nanosecond go to the later name.

    Raises BirthTimeUnavailable if creation times aren't recorded here, or
    OSError if the folder can't be listed.
    """
    latest: tuple[int, str] | None = None
    latest_path = None
    with os.scandir(notes_dir) as entries:
        for entry in entries:
            if not entry.name.endswith(FILENAME_EXT) or not entry.is_file():
                continue
            try:
                key = (birth_time_ns(entry.path), entry.name)
            except FileNotFoundError:
                continue  # deleted since the folder was listed
            if latest is None or key > latest:
                latest, latest_path = key, entry.path
    return latest_path


def read_note(path: str) -> str:
    """The text of an existing note, for Append to open.

    Raises OSError if it can't be read, or UnicodeDecodeError (a ValueError) if
    it isn't UTF-8 — every note Postit writes is.
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def rewrite_note(path: str, content: str) -> None:
    """Replace the note at `path` with `content`, as typed — no template.

    The file is truncated and rewritten in place rather than replaced through a
    temporary file. A replacement would be a new file, stamped as created now,
    and birth time is both the record of when the note was first written and
    the very thing Append goes by. The cost is that a write failing halfway
    through leaves the note cut short.

    If the note was deleted while it was open, it is written again at the same
    path. Raises OSError if the file can't be written.
    """
    if not content.endswith("\n"):
        content += "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
