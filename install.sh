#!/bin/bash
# Install Postit desktop entry
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

read -rp "Path to the Postit program directory [$SCRIPT_DIR]: " PROGRAM_DIR
PROGRAM_DIR="${PROGRAM_DIR:-$SCRIPT_DIR}"
PROGRAM_DIR="${PROGRAM_DIR/#\~/$HOME}"
PROGRAM_DIR="$(cd "$PROGRAM_DIR" && pwd)"  # normalize; fails if it doesn't exist

DEFAULT_NOTES_DIR="$HOME/ferguson"
read -rp "Directory to save notes into [$DEFAULT_NOTES_DIR]: " NOTES_DIR
NOTES_DIR="${NOTES_DIR:-$DEFAULT_NOTES_DIR}"
NOTES_DIR="${NOTES_DIR/#\~/$HOME}"  # expand ~ without requiring the folder to exist yet
case "$NOTES_DIR" in
  /*) ;;
  *) NOTES_DIR="$PWD/$NOTES_DIR" ;;
esac

chmod +x "$PROGRAM_DIR/start.sh"

mkdir -p ~/.local/share/applications
DESKTOP_TARGET="$HOME/.local/share/applications/postit.desktop"

sed \
  -e "s|^Exec=.*|Exec=\"$PROGRAM_DIR/start.sh\" \"$NOTES_DIR\"|" \
  -e "s|^Icon=.*|Icon=$PROGRAM_DIR/postit.png|" \
  "$SCRIPT_DIR/postit.desktop" > "$DESKTOP_TARGET"
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true

echo "Postit desktop entry installed."
echo "  Program:   $PROGRAM_DIR"
echo "  Notes dir: $NOTES_DIR"
if [ ! -d "$NOTES_DIR" ]; then
  echo "  (that folder doesn't exist yet - Postit will create it when you save your first note)"
fi
echo ""
echo "'Postit' should now appear in your application launcher. Search for it in"
echo "Activities, then right-click the icon to pin it to your dock."
