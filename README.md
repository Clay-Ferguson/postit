# Postit

A one-dialog utility for taking a quick note — the software equivalent of a sticky note. Launch it, type, click **Save**, and the text lands in a timestamped markdown file. There is no main window: the dialog is the whole application, and the process exits as soon as the note is written. The only thing it remembers is two paths: where notes go, and which template they're built from.

It is a PyQt6 rewrite of an earlier bash + zenity version, with the same file format and the same date handling. The one behavior change is that the old version's "Note saved" desktop notification is gone — saving is silent.

![](docs/img/postit-screenshot.png)

## Running

```bash
./start.sh
```

The first time it runs, Postit opens its **Settings** dialog before anything else, to ask for the two things it needs: the folder notes are saved into and the template file they're built from. Both are stored in `~/.config/postit/postit-config.yaml`:

```yaml
# Postit configuration. Edit here or from the Settings button.
notes_dir: /home/you/Documents/notes
template: /home/you/Postit/postit/data/note-template.md
```

Settings comes back on its own whenever the configuration stops being usable: the folder was moved, the template deleted, or the file edited into something that isn't valid YAML. Cancel it and Postit exits without opening the note dialog; run it again to retry.

`start.sh` runs the app through [uv](https://docs.astral.sh/uv/), which creates and refreshes the virtualenv from `pyproject.toml` on every run — there is no install step and nothing to activate. You need Python 3.11+ and `uv` on your PATH, plus the sibling checkout described next.

### The `windowchrome` sibling project

Postit's wide scroll bar comes from **[windowchrome](https://github.com/Clay-Ferguson/windowchrome)**, a small reusable PyQt6 library kept in its own repository so several apps can share the same look. It is **not on PyPI**: `pyproject.toml` resolves it by path, from a directory sitting *beside* this one.

```bash
cd ..                      # the directory holding Postit/
git clone https://github.com/Clay-Ferguson/windowchrome.git
```

giving:

```
projects/
├── Postit/
└── windowchrome/          <- must be a sibling, and named this
```

If it is missing, `./start.sh` fails immediately with an unresolved path dependency rather than with anything subtle. The checkout is used in place — `uv` installs it editable, so there is nothing to build and an edit there is live here on the next run.

## Installing

```bash
packaging/build-deb.sh
sudo apt install ./dist/postit_0.1.0_all.deb
```

`packaging/build-deb.sh` builds `dist/postit_<version>_all.deb`, which any Debian-based distribution can install if its repositories carry `python3-pyqt6` and Python 3.11 or newer. It installs:

| Path | What it is |
|---|---|
| `/usr/bin/postit` | The launcher. |
| `/usr/lib/postit/` | The `postit` package (including its `data/`: the bundled template and window icon) and a copy of `windowchrome`. |
| `/usr/share/applications/postit.desktop` | The application-menu entry. |
| `/usr/share/icons/hicolor/*/apps/postit.png` | The menu and dock icon, at every size. |

PyQt6 and PyYAML aren't bundled. The package depends on the distribution's own `python3-pyqt6` and `python3-yaml`, which `apt` installs along with it, and `uv` isn't needed at all.

Building needs only `dpkg-deb`, which every Debian system has, and the `windowchrome` sibling checkout described above, whose source is copied into the package. Before packing, the script smoke-tests the staged files: every import between modules resolves to a file that was copied, the data files are present, the bundled template renders, and the modules import (only the Qt-free ones if the build machine's `python3` has no PyQt6), so a file the copy missed fails the build rather than the first launch. The version comes from `pyproject.toml`. The package's Maintainer field comes from your `git config user.name` and `user.email`; override it with `POSTIT_MAINTAINER="Name <email>"`.

When installing from inside your home folder, `apt` may end with this notice:

```
N: Download is performed unsandboxed as root as file '.../postit_0.1.0_all.deb' couldn't be accessed by user '_apt'. - pkgAcquire::Run (13: Permission denied)
```

It's harmless, and the package still installs normally. `apt` usually reads package files as its unprivileged `_apt` user, and Ubuntu home folders are private by default, so `apt` read the file as root instead. To avoid the notice, copy the `.deb` somewhere world-readable first, such as `/tmp`, and install it from there.

Remove the package with `sudo apt remove postit`. Your notes and `~/.config/postit` are untouched.

The package is the only way to install Postit. To run it from this checkout instead — while working on it, say — use `./start.sh` directly; there is nothing to install for that.

## The dialog

A text area and three buttons.

| Action | Result |
|---|---|
| **Save** | Writes the note and exits. Disabled while the box is empty or whitespace-only. |
| **Cancel** or `Esc` | Exits without writing anything. |
| **Settings** | Opens the Settings dialog over the note. What you've typed is kept, and a change applies to the note you're about to save. |
| `Enter` | Inserts a newline — always. There is no keyboard save shortcut, by design. |

## Settings

Two fields, each with a **Browse…** button that opens the desktop's own folder or file chooser:

| Field | What it is |
|---|---|
| **Notes folder** | Where notes are written. Must already exist — the folder chooser can create one. |
| **Note template** | The file each note is built from (see below). Filled in with the bundled `note-template.md` when empty. |

**Save** stays disabled until both paths exist, and a line under the fields says what's still wrong. `~` is accepted in either field. **Cancel** at startup exits Postit; Cancel from the note dialog's Settings button just returns to the note.

## The note template

Each note is built from the template file chosen in Settings, with three placeholders substituted. The one bundled with Postit, `note-template.md`, is:

```markdown
---
tags:
  - p3
  - todo
due: {date}
start: {time}
---
{content}
```

| Placeholder | Replaced with | Example |
|---|---|---|
| `{date}` | Today's date, month and day unpadded | `8/21/2026` |
| `{time}` | The current time, 12-hour, hour unpadded | `1:05 PM` |
| `{content}` | Exactly what you typed | |

To change the frontmatter — different tags, extra fields, no frontmatter at all — copy `note-template.md` somewhere of your own, edit the copy, and point Settings at it. The template is read fresh on every save, so edits take effect immediately with no restart.

`{date}` and `{time}` use those slash-and-AM/PM formats for compatibility with the Timex Extension, which is why they don't match the filename's timestamp. Substitution is literal, so note text containing `&`, backslashes, or even the string `{date}` is written through untouched.

## Output files

Notes are named `note-YYYY-MM-DD--HH-MM-SS.md` — no slashes, spaces or colons, so they sort chronologically and are painless to type at a shell. If two notes land inside the same second, the second one gets a `-2` suffix (`note-2026-08-21--13-05-07-2.md`) rather than overwriting the first.

## Development

```bash
./start.sh     # run from the checkout
./lint.sh      # ruff, pyright and a syntax check of the shell scripts
```

There is deliberately no automated test suite; `./lint.sh` must stay clean. `ruff` and `pyright` are fetched by `uv` on demand, and their settings live in `ruff.toml` and `pyrightconfig.json` so that `pyproject.toml` stays the list of runtime dependencies.

## Layout

| Path | What it is |
|---|---|
| `postit/__main__.py` | Entry point: the startup settings check, `QApplication`, error dialogs. |
| `postit/note.py` | Timestamps, template rendering, the file write. No Qt — runs headless. |
| `postit/config.py` | The config file: load, save, and the one validity rule. No Qt — runs headless. |
| `postit/note_dialog.py` | `NoteDialog`: the text area and its buttons. |
| `postit/settings_dialog.py` | `SettingsDialog`: the notes folder and template, with Browse… buttons. |
| `postit/style.py` | The shared look: button style and the theme-derived field colors. |
| `postit/data/` | `note-template.md` (the bundled template described above) and `postit.png` (the window icon). |
| `packaging/build-deb.sh` | Builds the `.deb` into `dist/`. |
| `packaging/postit.desktop` | Desktop entry template; `build-deb.sh` rewrites `Exec=` and `Icon=`. |
| `packaging/icons/` | `source.png` (the artwork), the generated hicolor PNGs, and `make-icons.py`, which regenerates them: `uv run --no-project --with pillow packaging/icons/make-icons.py`. |
| `docs/` | The User Guide and its screenshot. Not shipped in the package. |
| `start.sh` | Launcher; runs the app via `uv`. |
| `lint.sh` | Static checks. |

See [USER_GUIDE.md](/docs/USER_GUIDE.md) for a walkthrough aimed at using the app rather than working on it.
