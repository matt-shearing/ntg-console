#!/usr/bin/env bash
# Per-user install, no root. Puts the app in ~/.local.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
make -C "$ROOT" PREFIX="$PREFIX" install
# Point the wrapper at this tree's installed data
mkdir -p "$HOME/.local/share/applications"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
echo "Installed ntg-console to $PREFIX/bin"
echo "Launch from the menu as NTG Console, or: ntg-console"
