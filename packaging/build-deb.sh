#!/usr/bin/env bash
# Build a Debian package (.deb) of Postit.
#
# Usage:  packaging/build-deb.sh          (from anywhere)
# Output: dist/postit_<version>_all.deb   (dist/ at the top of the checkout)
# Then:   sudo apt install ./dist/postit_<version>_all.deb
#
# Built by hand with dpkg-deb rather than with debhelper: Postit is pure Python
# with no build step, so all the package has to do is put files in the right
# places and name its dependencies. PyQt6 and PyYAML come from the distribution
# (python3-pyqt6, python3-yaml) rather than being bundled, which keeps the
# package architecture-independent and tiny. windowchrome isn't packaged
# anywhere, so its source is copied in from the sibling checkout.
#
# Installed layout:
#   /usr/bin/postit                              launcher
#   /usr/lib/postit/postit/                      the app, including data/
#                                                (the bundled note template
#                                                and the window icon)
#   /usr/lib/postit/windowchrome/                copy of ../windowchrome
#   /usr/share/applications/postit.desktop       menu entry
#   /usr/share/icons/hicolor/*/apps/postit.png   themed icon, every size
#
# __main__ calls setDesktopFileName("postit") to tie the window to the desktop
# entry, so renaming either one breaks the icon in the dock.
set -euo pipefail

# Every directory the package creates must be 755 and every file 644 or 755,
# whatever the builder's own umask is (Ubuntu's default 002 would otherwise
# leave /usr, /usr/lib and friends group-writable in the package).
umask 022

# HERE is packaging/, which holds what only the package needs (this script, the
# desktop entry template, the icons); ROOT is the checkout, which holds the app.
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname -- "$HERE")"
WINDOWCHROME="$ROOT/../windowchrome/windowchrome"
DIST="$ROOT/dist"
PACKAGE=postit
ARCH=all

die() {
  echo "Error: $*" >&2
  exit 1
}

command -v dpkg-deb >/dev/null 2>&1 || die "dpkg-deb not found (it is part of dpkg, on every Debian-based system)."

VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$ROOT/pyproject.toml" | head -n 1)"
[ -n "$VERSION" ] || die "could not read the version from pyproject.toml."

[ -f "$WINDOWCHROME/__init__.py" ] || die "windowchrome not found at $WINDOWCHROME.
Clone it beside the Postit checkout:  git clone https://github.com/Clay-Ferguson/windowchrome.git ../windowchrome"

# The Maintainer field is whoever builds the package, taken from git unless
# POSTIT_MAINTAINER="Name <email>" says otherwise.
if [ -z "${POSTIT_MAINTAINER:-}" ]; then
  name="$(git -C "$ROOT" config user.name || true)"
  email="$(git -C "$ROOT" config user.email || true)"
  [ -n "$name" ] && [ -n "$email" ] || die "set git user.name and user.email, or POSTIT_MAINTAINER=\"Name <email>\"."
  POSTIT_MAINTAINER="$name <$email>"
fi

STAGE="$DIST/${PACKAGE}_${VERSION}_${ARCH}"
DEB="$DIST/${PACKAGE}_${VERSION}_${ARCH}.deb"
LIB="$STAGE/usr/lib/$PACKAGE"
rm -rf "$STAGE" "$DEB"

# -- files -------------------------------------------------------------------

install -d -m 755 \
  "$LIB" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/doc/$PACKAGE" \
  "$STAGE/DEBIAN"

# Copy every file of a directory tree into the stage: files 644, and the
# directories `install -D` creates for them 755 (the umask above). Whole trees
# rather than a glob per directory, so a new module, subpackage or data file
# ships without anyone having to remember a line here — a per-directory copy
# would leave it out of a package that installs cleanly and fails on first
# use. __pycache__ is left behind on purpose and compiled fresh by postinst.
copy_tree() {
  local src="$1" dest="$2" file
  while IFS= read -r -d '' file; do
    install -D -m 644 "$src/$file" "$dest/$file"
  done < <(cd "$src" && find . -name __pycache__ -prune -o -type f -print0)
}

copy_tree "$ROOT/postit" "$LIB/postit"
copy_tree "$WINDOWCHROME" "$LIB/windowchrome"

install -m 644 "$ROOT/LICENSE.md" "$STAGE/usr/share/doc/$PACKAGE/copyright"

# Icon=postit in the desktop entry is a *theme* name, not a path, so the PNGs
# have to land in the hicolor theme for it to resolve. They are checked in at
# every size rather than converted here, which keeps this script free of
# Pillow and ImageMagick; regenerate them with packaging/icons/make-icons.py if
# the artwork changes. (icons/source.png is that artwork and is not installed.)
for icon in "$HERE"/icons/hicolor/*/apps/postit.png; do
  size_dir="$(basename "$(dirname "$(dirname "$icon")")")"
  install -d -m 755 "$STAGE/usr/share/icons/hicolor/$size_dir/apps"
  install -m 644 "$icon" "$STAGE/usr/share/icons/hicolor/$size_dir/apps/postit.png"
done

# -I (isolated mode) keeps PYTHONPATH and ~/.local site-packages out, so the app
# always runs against the distribution's python3-pyqt6 and python3-yaml rather
# than a pip-installed copy that happens to be lying around.
cat > "$STAGE/usr/bin/$PACKAGE" <<'EOF'
#!/bin/sh
# Postit launcher, installed by the postit package.
exec /usr/bin/python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/postit"); from postit.__main__ import main; sys.exit(main())' "$@"
EOF
chmod 755 "$STAGE/usr/bin/$PACKAGE"

# The desktop entry, pointed at the installed launcher. Icon= is already the
# theme name and is rewritten only to keep it pinned to $PACKAGE. The
# template's comment lines are dropped, since they only describe the template.
sed \
  -e '/^#/d' \
  -e "s|^Exec=.*|Exec=$PACKAGE|" \
  -e "s|^Icon=.*|Icon=$PACKAGE|" \
  "$HERE/postit.desktop" > "$STAGE/usr/share/applications/postit.desktop"
chmod 644 "$STAGE/usr/share/applications/postit.desktop"

# -- smoke test ----------------------------------------------------------------

# A file the copy missed installs cleanly and fails on first launch, so the
# staged tree is checked before it is packed, with the launcher's own flags
# (-I) plus -B so nothing is written into the stage. Three checks, the first
# two needing nothing but Python and PyYAML, so they run on a build machine
# with no Qt:
#
#   - every import inside the staged packages names a file that was staged;
#   - the data files are there, and the bundled template renders with all
#     three placeholders substituted;
#   - the modules import: all of them where the system python3 has PyQt6, and
#     otherwise the Qt-free ones (note, config).
command -v python3 >/dev/null 2>&1 || die "python3 not found; it is needed to check the staged files."
python3 -I -B - "$LIB" <<'PY' || die "the staged files failed the smoke test (above); nothing was packaged."
import ast
import datetime
import importlib
import pathlib
import sys

lib = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(lib))
problems = []


def is_module(path):
    return path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()


for package in ("postit", "windowchrome"):
    for source in sorted((lib / package).rglob("*.py")):
        where = source.relative_to(lib)
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level:
                base = source.parent
                for _ in range(node.level - 1):
                    base = base.parent
                if node.module:
                    if not is_module(base.joinpath(*node.module.split("."))):
                        problems.append(f"{where}: from {'.' * node.level}{node.module}")
                elif not (base / "__init__.py").is_file():
                    problems.append(f"{where}: from {'.' * node.level} (no package)")
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                for name in names:
                    top = name.split(".")[0]
                    if top in ("postit", "windowchrome") and not is_module(lib.joinpath(*name.split("."))):
                        problems.append(f"{where}: import {name}")

data = lib / "postit" / "data"
for name in ("note-template.md", "postit.png"):
    if not (data / name).is_file():
        problems.append(f"postit/data/{name} is missing (config/__main__ read it)")

from postit import note

template = data / "note-template.md"
if template.is_file():
    when = datetime.datetime(2026, 8, 21, 13, 5)
    rendered = note.render(note.read_template(str(template)), "smoke test", when)
    for placeholder in (note.DATE_PLACEHOLDER, note.TIME_PLACEHOLDER, note.CONTENT_PLACEHOLDER):
        if placeholder in rendered:
            problems.append(f"note-template.md: {placeholder} was not substituted")

try:
    import PyQt6.QtWidgets  # noqa: F401
    modules = [p.stem for p in (lib / "postit").glob("*.py") if p.stem != "__init__"]
    scope = "every module"
except ImportError:
    modules = ["note", "config"]
    scope = "the Qt-free modules (no PyQt6 for this python3)"
for name in sorted(modules):
    try:
        importlib.import_module(f"postit.{name}")
    except Exception as exc:
        problems.append(f"import postit.{name}: {exc!r}")

if problems:
    print("\n".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"Smoke test passed: imports resolve, the template renders, {scope} import.")
PY

# -- package metadata --------------------------------------------------------

# Compiled as root at install time, since a user running Postit can't write
# __pycache__ under /usr/lib; without it every launch compiles in memory.
# The two cache refreshes are what make the icon and the menu entry appear
# without a logout; both are absent on a bare system and harmless when they are.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
  python3 -m compileall -q /usr/lib/postit >/dev/null 2>&1 || true
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
EOF

# Removes what postinst compiled, so dpkg can remove the directories it
# installed (it only deletes files it knows about). Runs before upgrades too;
# the new version's postinst compiles again.
cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
find /usr/lib/postit -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
EOF

# The icon is gone by now, so the cache has to be rebuilt again or the desktop
# keeps showing it in menus until something else refreshes it.
cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
EOF
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm" "$STAGE/DEBIAN/postrm"

INSTALLED_SIZE="$(du -sk --exclude=DEBIAN "$STAGE" | cut -f1)"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PACKAGE
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.11), python3-pyqt6, python3-yaml
Recommends: qt6-wayland
Maintainer: $POSTIT_MAINTAINER
Installed-Size: $INSTALLED_SIZE
Homepage: https://github.com/Clay-Ferguson/postit
Description: jot a quick note into a timestamped markdown file
 Postit pops up a single dialog with a text area. Click Save and what you
 typed is written to a timestamped markdown file, built from a template,
 in a notes folder chosen in its Settings dialog.
EOF

# -- build -------------------------------------------------------------------

# --root-owner-group: files owned by root without needing fakeroot.
# -Zxz: every dpkg can read xz; Ubuntu's default zstd is not readable by
# older Debian dpkg releases.
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB" >/dev/null
rm -rf "$STAGE"

echo "Built $DEB"
echo ""
echo "Install:  sudo apt install $DEB"
echo "Remove:   sudo apt remove $PACKAGE"
# A leftover from the old install.sh, which this package replaced. Its entry in
# ~/.local/share/applications takes precedence over the package's, so it would
# keep launching the checkout after the package is installed.
if [ -f "$HOME/.local/share/applications/postit.desktop" ]; then
  echo ""
  echo "Note: a per-user launcher in ~/.local/share/applications hides the"
  echo "package's. Remove it with:"
  echo "  rm ~/.local/share/applications/postit.desktop"
fi
