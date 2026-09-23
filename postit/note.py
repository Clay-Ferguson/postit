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

# The filename timestamp is sortable and shell-friendly: no slashes, no spaces,
# no colons. The date and time written *into* the note are a different, more
# readable pair of formats (see `format_date`/`format_time`) — they're what the
# Timex Extension reads, so they must keep their slashes and AM/PM.
FILENAME_FORMAT = "note-%Y-%m-%d--%H-%M-%S.md"

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
    becomes `note-<stamp>-2.md`, the third `-3`, and so on.
    """
    base = when.strftime(FILENAME_FORMAT)
    yield os.path.join(notes_dir, base)
    stem, ext = os.path.splitext(base)
    for suffix in itertools.count(2):
        yield os.path.join(notes_dir, f"{stem}-{suffix}{ext}")


def write_note(
    notes_dir: str, template_path: str, content: str, when: dt.datetime | None = None
) -> str:
    """Render `content` into the template and save it. Returns the path written.

    The notes folder must already exist; it is never created here (see
    `config.problem()`). Each candidate name is opened in exclusive-create mode,
    so checking that a name is free and taking it are one step, and a note can
    never land on top of another, even one written in the same instant.

    Raises TemplateNotFound if the template is missing, or OSError if the file
    can't be written.
    """
    when = when or dt.datetime.now()
    body = render(read_template(template_path), content, when)
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
