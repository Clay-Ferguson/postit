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
template: /home/you/Postit/note-template.md
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

## Installing the desktop icon

```bash
./install.sh
```

It asks nothing. It writes `~/.local/share/applications/postit.desktop` pointing at `start.sh` and `postit.png` in this folder; the notes folder and template are chosen in Settings the first time Postit runs.

`./uninstall.sh` removes the desktop entry and leaves the config file where it is.

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

## Layout

| Path | What it is |
|---|---|
| `postit/note.py` | Timestamps, template rendering, the file write. No Qt — runs headless. |
| `postit/config.py` | The config file: load, save, and the one validity rule. No Qt — runs headless. |
| `postit/dialog.py` | `NoteDialog` and its theme-derived styling. |
| `postit/settings.py` | `SettingsDialog`: the notes folder and template, with Browse… buttons. |
| `postit/__main__.py` | Entry point: the startup settings check, `QApplication`, error dialogs. |
| `note-template.md` | The bundled template described above; the default offered in Settings. |
| `start.sh` | Launcher; runs the app via `uv`. |
| `install.sh` / `uninstall.sh` | Desktop entry management. |
| `postit.desktop` | Desktop entry template; `install.sh` rewrites `Exec=` and `Icon=`. |

See [USER_GUIDE.md](/docs/USER_GUIDE.md) for a walkthrough aimed at using the app rather than working on it.
