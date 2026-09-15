#!/usr/bin/env bash
# Build a Debian package (.deb) of Postit.
#
# Usage:  ./build-deb-install.sh
# Output: dist/postit_<version>_all.deb
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
#   /usr/bin/postit                         launcher
#   /usr/lib/postit/postit/                 the app
#   /usr/lib/postit/windowchrome/           copy of ../windowchrome
#   /usr/lib/postit/note-template.md        bundled template  } found through
#   /usr/lib/postit/postit.png              window icon       } config.PROJECT_ROOT
#   /usr/share/applications/postit.desktop  menu entry
#   /usr/share/pixmaps/postit.png           menu icon (symlink)
set -euo pipefail

# Every directory the package creates must be 755 and every file 644 or 755,
# whatever the builder's own umask is (Ubuntu's default 002 would otherwise
# leave /usr, /usr/lib and friends group-writable in the package).
umask 022

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WINDOWCHROME="$HERE/../windowchrome/windowchrome"
DIST="$HERE/dist"
PACKAGE=postit
ARCH=all

die() {
  echo "Error: $*" >&2
  exit 1
}

command -v dpkg-deb >/dev/null 2>&1 || die "dpkg-deb not found (it is part of dpkg, on every Debian-based system)."

VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$HERE/pyproject.toml" | head -n 1)"
[ -n "$VERSION" ] || die "could not read the version from pyproject.toml."

[ -f "$WINDOWCHROME/__init__.py" ] || die "windowchrome not found at $WINDOWCHROME.
Clone it beside this folder:  git clone https://github.com/Clay-Ferguson/windowchrome.git ../windowchrome"

# The Maintainer field is whoever builds the package, taken from git unless
# POSTIT_MAINTAINER="Name <email>" says otherwise.
if [ -z "${POSTIT_MAINTAINER:-}" ]; then
  name="$(git -C "$HERE" config user.name || true)"
  email="$(git -C "$HERE" config user.email || true)"
  [ -n "$name" ] && [ -n "$email" ] || die "set git user.name and user.email, or POSTIT_MAINTAINER=\"Name <email>\"."
  POSTIT_MAINTAINER="$name <$email>"
fi

STAGE="$DIST/${PACKAGE}_${VERSION}_${ARCH}"
DEB="$DIST/${PACKAGE}_${VERSION}_${ARCH}.deb"
LIB="$STAGE/usr/lib/$PACKAGE"
rm -rf "$STAGE" "$DEB"

# -- files -------------------------------------------------------------------

install -d -m 755 \
  "$LIB/postit" "$LIB/windowchrome" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/pixmaps" \
  "$STAGE/usr/share/doc/$PACKAGE" \
  "$STAGE/DEBIAN"

# Both packages are flat directories of modules; __pycache__ is left behind on
# purpose and compiled fresh by postinst.
install -m 644 "$HERE"/postit/*.py "$LIB/postit/"
install -m 644 "$WINDOWCHROME"/*.py "$LIB/windowchrome/"
install -m 644 "$HERE/note-template.md" "$HERE/postit.png" "$LIB/"
ln -s "../../lib/$PACKAGE/postit.png" "$STAGE/usr/share/pixmaps/postit.png"
install -m 644 "$HERE/LICENSE.md" "$STAGE/usr/share/doc/$PACKAGE/copyright"

# -I (isolated mode) keeps PYTHONPATH and ~/.local site-packages out, so the app
# always runs against the distribution's python3-pyqt6 and python3-yaml rather
# than a pip-installed copy that happens to be lying around.
cat > "$STAGE/usr/bin/$PACKAGE" <<'EOF'
#!/bin/sh
# Postit launcher, installed by the postit package.
exec /usr/bin/python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/postit"); from postit.__main__ import main; sys.exit(main())' "$@"
EOF
chmod 755 "$STAGE/usr/bin/$PACKAGE"

# The same desktop entry install.sh uses, pointed at the installed launcher and
# the icon by name (found in /usr/share/pixmaps).
sed \
  -e "s|^Exec=.*|Exec=$PACKAGE|" \
  -e "s|^Icon=.*|Icon=$PACKAGE|" \
  "$HERE/postit.desktop" > "$STAGE/usr/share/applications/postit.desktop"
chmod 644 "$STAGE/usr/share/applications/postit.desktop"

# -- package metadata --------------------------------------------------------

# Compiled as root at install time, since a user running Postit can't write
# __pycache__ under /usr/lib; without it every launch compiles in memory.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
  python3 -m compileall -q /usr/lib/postit >/dev/null 2>&1 || true
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
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm"

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
if [ -f "$HOME/.local/share/applications/postit.desktop" ]; then
  echo ""
  echo "Note: you have a launcher from install.sh in ~/.local/share/applications,"
  echo "which hides the package's. Run ./uninstall.sh before installing the package."
fi
