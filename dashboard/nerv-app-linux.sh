#!/usr/bin/env bash
# NERV Console — Linux "app" launcher.
# Starts the stdlib backend and opens a chromeless standalone window (Chrome/Chromium/Edge
# in --app mode). Falls back to your default browser if no Chromium-family browser is found.
#
#   ./nerv-app-linux.sh [PROJECT_DIR]
#
# Install a desktop entry with:  ./install.sh   (adds "NERV Console" to your app menu)
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "python3 is required" >&2; exit 1; }
exec "$PY" "$HERE/nerv-launch.py" --app "$@"
