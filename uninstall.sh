#!/bin/bash
# Uninstall Postit desktop entry

DESKTOP_TARGET="$HOME/.local/share/applications/postit.desktop"

if [ -f "$DESKTOP_TARGET" ]; then
  rm -f "$DESKTOP_TARGET"
  update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null
  echo "Postit desktop entry removed."
else
  echo "Postit desktop entry not found."
fi

CONFIG_DIR="$HOME/.config/postit"
if [ -d "$CONFIG_DIR" ]; then
  echo "Your settings in $CONFIG_DIR were left in place; delete that folder to remove them too."
fi
