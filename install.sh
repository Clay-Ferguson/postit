#!/bin/bash
# Install Postit desktop entry
#
# Nothing to ask: the notes folder and template live in
# ~/.config/postit/postit-config.yaml, and Postit opens its Settings dialog to
# fill them in the first time it runs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

chmod +x "$SCRIPT_DIR/start.sh"

mkdir -p ~/.local/share/applications
DESKTOP_TARGET="$HOME/.local/share/applications/postit.desktop"

sed \
  -e "s|^Exec=.*|Exec=\"$SCRIPT_DIR/start.sh\"|" \
  -e "s|^Icon=.*|Icon=$SCRIPT_DIR/postit.png|" \
  "$SCRIPT_DIR/postit.desktop" > "$DESKTOP_TARGET"
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true

echo "Postit desktop entry installed."
echo "  Program: $SCRIPT_DIR"
echo ""
echo "The first time Postit runs it opens its Settings, where you choose the folder"
echo "notes are saved into and the template they're built from. Both are stored in"
echo "~/.config/postit/postit-config.yaml and can be changed later with the"
echo "Settings button."
echo ""
echo "'Postit' should now appear in your application launcher. Search for it in"
echo "Activities, then right-click the icon to pin it to your dock."
