# Postit User Guide

## What Postit Is

Postit is for the thought you need to get out of your head in the next five seconds — a phone number, a thing to look up later, a task you don't want to lose. You click the icon, a box appears, you type, you click **Save**, and it's gone from your screen and safely in a file.

That's the entire application. There's no window that stays open, no list of past notes to browse, no settings screen. Every note becomes a separate markdown file in one folder, named after the moment you wrote it, and you read them back with whatever you already use for markdown files.

![](img/postit-screenshot.png)

## Installing

You need two things already on your machine: Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/). If you don't have `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, from the Postit folder:

```bash
./install.sh
```

It asks you two questions, and pressing Enter accepts the default for either:

1. **Path to the Postit program directory** — where these files live. The default is almost always right.
2. **Directory to save notes into** — the folder your notes go in. Defaults to `~/ferguson`. It doesn't have to exist yet; Postit creates it when you save your first note.

After that, "Postit" appears in your application launcher. Search for it in Activities, then right-click the icon and pin it to your dock — the whole point of the app is being one click away.

To point Postit at a different notes folder later, run `./install.sh` again and give the new path.

To remove the launcher entry, run `./uninstall.sh`. That only removes the icon; your notes are untouched.

## Launching

Click the Postit icon. There's no splash screen and no main window — the note box comes straight up, focused and ready for typing.

You can also run it from a terminal, which is handy for sending notes somewhere other than your usual folder:

```bash
./start.sh                    # notes go to ~/ferguson
./start.sh ~/work/scratch     # notes go to ~/work/scratch
```

The first launch after installing takes a couple of seconds longer while `uv` builds the virtual environment. Every launch after that is immediate.

## Writing a Note

The dialog is a text area with **Save** and **Cancel** at the bottom.

Type anything you like — it's a plain text box, so multiple lines, blank lines, indentation and pasted text all work. Notes are saved as markdown, so if you write markdown (a `- ` list, a `**bold**` word, a `# heading`) it will render as markdown wherever you read your notes later. If you don't, it's just text.

**Enter always inserts a newline.** There's no keyboard shortcut for saving, deliberately — in a note box, Enter needs to mean "new line" every single time, without you having to think about it.

### Saving

Click **Save**. The note is written and the dialog closes. Nothing else happens — no confirmation popup and no desktop notification. If the dialog went away, the note was saved.

**Save is greyed out until you've typed something.** Spaces and blank lines don't count, so you can't accidentally create an empty note by clicking Save on a box you didn't type in.

### Cancelling

Click **Cancel**, or press `Esc`. The dialog closes and nothing is written — no file is created, and the notes folder isn't even created if it didn't already exist. There is no "are you sure?" prompt, so anything you'd typed is gone.

## What Gets Saved

Say it's 1:05 PM on August 21st, 2026, and you type:

```
Call the dentist about rescheduling
Ask about the Thursday slot
```

You get a file called `note-2026-08-21--13-05-07.md` containing:

```markdown
---
tags:
  - p3
  - todo
due: 8/21/2026
start: 1:05 PM
---
Call the dentist about rescheduling
Ask about the Thursday slot
```

The block between the `---` lines is YAML frontmatter — metadata that markdown tools read and usually don't display. The `p3`/`todo` tags and the `due`/`start` times are there so notes show up as tasks in tools that look for them.

### Filenames

`note-YYYY-MM-DD--HH-MM-SS.md`, using a 24-hour clock. There are no spaces or colons in the name, so the files sort into chronological order in any file manager and are easy to type at a terminal.

Save two notes within the same second and the second one becomes `note-2026-08-21--13-05-07-2.md`. Your first note is never overwritten.

### Why the dates inside look different from the filename

The filename uses `2026-08-21` because it sorts correctly. The `due:` and `start:` fields use `8/21/2026` and `1:05 PM` because that's the format the Timex Extension reads. They're describing the same moment in two formats, on purpose.

## Customizing the Template

Every note is built from `note-template.md` in the Postit folder. Open it in any editor:

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

The three words in braces get replaced when a note is saved:

| Placeholder | Becomes |
|---|---|
| `{date}` | `8/21/2026` |
| `{time}` | `1:05 PM` |
| `{content}` | What you typed in the box |

Everything else is copied through exactly as written. So you can change the tags, add fields of your own, move `{content}` above the frontmatter, or delete the frontmatter entirely and leave just `{content}` for plain notes with no metadata.

The template is read fresh every time you save, so edits take effect on your very next note — there's nothing to restart or reinstall.

A couple of things worth knowing:

- You don't have to use all three placeholders. A template of just `{content}` is perfectly valid.
- Your note text is inserted literally. Characters like `&` and `\` come through exactly as typed, and if you literally type `{date}` in a note it stays as `{date}` rather than turning into today's date.

## When Something Goes Wrong

Postit tells you with an error dialog rather than failing silently. The two things that can go wrong:

- **"Template not found"** — `note-template.md` was moved, renamed or deleted from the Postit folder. Restore it and the file will save on your next try; the note you'd typed is not recovered, so re-type it.
- **A permissions or path error** — Postit couldn't create the notes folder or write into it. Check that the path you gave `install.sh` is somewhere you can write to, and run `./install.sh` again to correct it if not.

In both cases nothing was written, so there's no half-saved file to clean up.
