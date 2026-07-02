# NERV app shell (interactive) — used ONLY by the terminal embedded in the NERV app.
# It first loads your normal ~/.zshrc (aliases, PATH, keys, everything), then layers the
# NERV MAGI prompt on top. Your regular terminal never sources this file, so it stays clean.
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc"

# NERV MAGI prompt (starship) — app-only. Falls back to your default prompt if starship
# isn't installed. NERV_DASH_DIR is exported by shell-launch/term-launch.
if command -v starship >/dev/null 2>&1; then
  if [ -n "$NERV_DASH_DIR" ] && [ -f "$NERV_DASH_DIR/starship.toml" ]; then
    export STARSHIP_CONFIG="$NERV_DASH_DIR/starship.toml"
  elif [ -f "$HOME/.config/starship.toml" ]; then
    export STARSHIP_CONFIG="$HOME/.config/starship.toml"
  fi
  eval "$(starship init zsh)"
fi
