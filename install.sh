#!/usr/bin/env bash
# ============================================================================
#  NEON GENESIS TERMINAL — installer
#  Builds the NERV.app native shell, installs the dashboard + launcher,
#  and (optionally) wires in your personal NASA API key.
# ============================================================================
set -euo pipefail

CYAN=$'\033[36m'; GRN=$'\033[32m'; AMB=$'\033[33m'; RED=$'\033[31m'; DIM=$'\033[2m'; RST=$'\033[0m'
say(){ printf "%s\n" "$1"; }
ok(){ printf "${GRN}  ✓ %s${RST}\n" "$1"; }
warn(){ printf "${AMB}  ! %s${RST}\n" "$1"; }
die(){ printf "${RED}  ✗ %s${RST}\n" "$1"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$HOME/.config/nerv-theme"
DASH="$CFG/dashboard"
BIN="$HOME/.local/bin"

printf "${RED}"
cat <<'BANNER'
   _   _ _____ ___  _   _    ___ _____ _  _ ___ ___ ___ ___
  | \ | | ____/ _ \| \ | |  / __| ____| \| / __| __/ __|_ _|
  |  \| |  _|| | | |  \| | | (_ |  _| | .` \__ \ _|\__ \| |
  |_|\__|_____\___/|_|\__|  \___|_____|_|\_|___/___|___/___|
                  N E O N   G E N E S I S   T E R M I N A L
BANNER
printf "${RST}\n"

# ---- 1. platform check --------------------------------------------------
[ "$(uname)" = "Darwin" ] || die "This app is macOS-only (it builds a native WKWebView app)."
ok "macOS detected"

# ---- 2. dependency check ------------------------------------------------
say "${CYAN}▸ Checking dependencies…${RST}"
MISSING=()
command -v python3 >/dev/null 2>&1 && ok "python3" || MISSING+=("python3")
command -v swiftc  >/dev/null 2>&1 && ok "swiftc (Xcode CLT)" || MISSING+=("xcode-select")
command -v ttyd    >/dev/null 2>&1 && ok "ttyd" || MISSING+=("ttyd")

if [ ${#MISSING[@]} -gt 0 ]; then
  warn "Missing: ${MISSING[*]}"
  for m in "${MISSING[@]}"; do
    case "$m" in
      ttyd)         say "    install with: ${DIM}brew install ttyd${RST}";;
      xcode-select) say "    install with: ${DIM}xcode-select --install${RST}";;
      python3)      say "    install with: ${DIM}brew install python3${RST}";;
    esac
  done
  die "Install the missing dependencies above, then re-run ./install.sh"
fi

# ---- 3. install dashboard + launcher ------------------------------------
say "${CYAN}▸ Installing dashboard → ${DASH}${RST}"
mkdir -p "$DASH"
cp "$HERE/dashboard/nerv-dashboard.html" "$DASH/"
cp "$HERE/dashboard/nerv-server.py"      "$DASH/"
cp "$HERE/dashboard/nerv-dash"           "$DASH/"
cp "$HERE/dashboard/term-launch"         "$DASH/"
cp "$HERE/dashboard/shell-launch"        "$DASH/"
chmod +x "$DASH/nerv-dash" "$DASH/term-launch" "$DASH/shell-launch" "$DASH/nerv-server.py"
ok "dashboard files copied"

mkdir -p "$BIN"
ln -sf "$DASH/nerv-dash" "$BIN/nerv-dash"
ok "launcher linked → $BIN/nerv-dash"
case ":$PATH:" in *":$BIN:"*) :;; *) warn "$BIN is not on your PATH — add it to use 'nerv-dash' directly";; esac

# ---- 4. build NERV.app --------------------------------------------------
say "${CYAN}▸ Building NERV.app…${RST}"
APP="/Applications/NERV.app"
TMP="$(mktemp -d)"
swiftc -O -framework Cocoa -framework WebKit "$HERE/dashboard/nerv-app.swift" -o "$TMP/NERV" 2>/dev/null \
  || die "swiftc build failed (is Xcode Command Line Tools installed?)"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$TMP/NERV" "$APP/Contents/MacOS/NERV"
# app icon (Hex MAGI core). Use the committed .icns; regenerate from source if Pillow is present.
if [ -f "$HERE/tools/make-icon.py" ] && python3 -c "import PIL" >/dev/null 2>&1; then
  python3 "$HERE/tools/make-icon.py" >/dev/null 2>&1 || true
fi
if [ -f "$HERE/NERV.icns" ]; then cp "$HERE/NERV.icns" "$APP/Contents/Resources/AppIcon.icns" && ok "app icon installed"
else warn "NERV.icns not found — app will use the default icon"; fi
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>NERV</string>
  <key>CFBundleDisplayName</key><string>NERV</string>
  <key>CFBundleIdentifier</key><string>com.nerv.console</string>
  <key>CFBundleExecutable</key><string>NERV</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
codesign --force --deep --sign - "$APP" 2>/dev/null && ok "NERV.app built + signed (ad-hoc)" || warn "NERV.app built (codesign skipped)"
touch "$APP"   # nudge Finder/Dock to refresh the icon
rm -rf "$TMP"

# ---- 5. NASA API key ----------------------------------------------------
say "${CYAN}▸ NASA API key${RST}"
say "    The geocentric map pulls real near-earth-asteroid data from NASA NeoWs."
say "    Grab a ${GRN}free${RST} key in ~30s at ${CYAN}https://api.nasa.gov${RST} (no email confirmation needed)."
if [ -f "$CFG/config.json" ]; then
  ok "config.json already present — leaving it untouched"
else
  printf "    Paste your NASA API key (or press Enter to use the shared DEMO_KEY): "
  read -r KEY || KEY=""
  KEY="${KEY:-DEMO_KEY}"
  printf '{\n  "nasa_api_key": "%s"\n}\n' "$KEY" > "$CFG/config.json"
  [ "$KEY" = "DEMO_KEY" ] && warn "Using DEMO_KEY (rate-limited). Edit $CFG/config.json anytime." \
                          || ok "Saved your key → $CFG/config.json (gitignored, stays local)"
fi

# ---- done ---------------------------------------------------------------
printf "\n${GRN}══════════════════════════════════════════════════════════════${RST}\n"
ok "Installation complete."
say ""
say "  Launch the app:        ${CYAN}open /Applications/NERV.app${RST}"
say "  Or run headless:       ${CYAN}nerv-dash${RST}        ${DIM}(opens in your browser)${RST}"
say "  Stop everything:       ${CYAN}nerv-dash stop${RST}"
say ""
say "  ${DIM}Tip: double-click any panel to make it the main view; ⤢ for fullscreen.${RST}"
printf "${GRN}══════════════════════════════════════════════════════════════${RST}\n"
