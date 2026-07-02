# NERV app shell — inherit the user's real environment (this profile is used ONLY by the
# embedded terminal inside the NERV app, via ZDOTDIR; the regular terminal is untouched).
[ -f "$HOME/.zshenv" ] && source "$HOME/.zshenv"
