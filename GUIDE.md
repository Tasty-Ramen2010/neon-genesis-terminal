# NEON GENESIS TERMINAL — Command Guide

Everything you can do with the console, in one place.

Repo: <https://github.com/Tasty-Ramen2010/neon-genesis-terminal>

---

## Install

```bash
git clone https://github.com/Tasty-Ramen2010/neon-genesis-terminal.git
cd neon-genesis-terminal
./install.sh            # checks deps; builds NERV.app on macOS; prompts for a NASA key
```

The installer puts the dashboard in `~/.config/nerv-theme/dashboard/` and links the
launcher to `~/.local/bin/nerv-dash`.

---

## Launching the console

| Platform | Command |
|----------|---------|
| **macOS (native app)** | `open /Applications/NERV.app` |
| **macOS / Linux (browser)** | `nerv-dash` |
| **Any OS (portable)** | `python3 ~/.config/nerv-theme/dashboard/nerv-launch.py` |
| **Windows** | `python dashboard\nerv-launch.py` (from the repo) — or use WSL for the full terminal |

---

## Second window (two monitors)

The console supports **multiple independent instances** — each picks its own free
ports and runs its own backend, so nothing collides.

```bash
# macOS — the -n flag forces a NEW instance (without it, macOS just refocuses the existing window)
open -n /Applications/NERV.app

# one console per project (each pointed at a different working directory)
cd ~/project-a && nerv-dash new .     # window 1  -> ports 8731 / 7682 / 7683
cd ~/project-b && nerv-dash new .     # window 2  -> ports 8741 / 7692 / 7693
```

Then drag one window to each monitor. Open as many as you like — ports step by 10 each time.

---

## `nerv-dash` — the launcher

| Command | What it does |
|---------|--------------|
| `nerv-dash` | Start services + open the console in your browser (default ports) |
| `nerv-dash new [DIR]` | **New instance** on auto-picked free ports, project root = `DIR` (or `$PWD`) |
| `nerv-dash serve` | Start services only, no browser (this is what `NERV.app` runs) |
| `nerv-dash status` | Show what's running on the active ports |
| `nerv-dash restart-term` | (Legacy) — the terminal is now in-server; use the in-app `⟳ RESTART` |
| `nerv-dash stop` | Stop this instance (the one on `$NERV_PORT`, default 8731) |
| `nerv-dash kill` | Panic: hard-stop everything + clear stray audio |
| `nerv-dash ports` | Print the next free `{stats ttyd shell}` port triplet |
| `nerv-dash term` | Open a standalone cool-retro-term / Terminal window |

---

## In-app controls

| Action | How |
|--------|-----|
| Make a panel the main view | double-click it, or use the `VIEW` bar (`TERM · GLOBE · TODO · MONITOR · SPACE WX · FEED`) |
| Fullscreen a panel | `⤢` button · double-click its title bar · `Esc` to exit |
| Orbit / zoom the globe | drag / scroll (when the globe is the main view) |
| Identify an object | hover it (asteroid, satellite, ISS, Hubble, Moon, Sun, quake, your location) |
| Toggle shell ↔ Claude Code | `SHELL` / `CLAUDE` in the bottom bar (opens a plain shell by default) |
| Restart the terminal | `⟳ RESTART` |
| Toggle heavy-CRT mode | `▦ CRT` (phosphor burn-in, scanlines, flicker — remembered across launches) |
| Mute / unmute sound | `♪ SOUND` |
| Resize UI | `A−` / `A+` |
| Skip the boot sequence | click / press any key |

---

## What's on the globe

- **Real continents** with a real **day/night terminator** (tracks the true sub-solar
  point from UTC — the shadow sits at the correct real position and drifts slowly).
- **Your location** — a green NERV beacon at your approximate city/state (IP-based).
- **1,300+ satellites** (Celestrak TLEs), **Hubble**, and the **ISS**, all real.
- **Real asteroids** (NASA NeoWs), the **real Moon** (real position + phase), the **Sun**, and the **planets** (Mercury–Neptune at their real geocentric sky positions).
- **Live aurora oval** (scaled by the real Kp index) and **earthquake shockwaves**
  (real USGS quakes; great-circle wavefronts at seismic velocity).

## Header telemetry (rotating)

Kardashev civilization type · age of the universe · Hubble altitude · next launch
countdown · deep-space fleet distances (Voyager 1 & 2, New Horizons, Pioneer 10).

---

## NASA API key

The asteroid feed uses NASA's free [NeoWs](https://api.nasa.gov) API. The installer
asks for a key and saves it to `~/.config/nerv-theme/config.json` (gitignored — it
never leaves your machine). Resolution order:

```
NASA_API_KEY env var  →  ~/.config/nerv-theme/config.json  →  DEMO_KEY (rate-limited fallback)
```

Get your own free key in ~30 seconds at <https://api.nasa.gov>.

---

## Environment overrides

| Variable | Purpose |
|----------|---------|
| `NASA_API_KEY` | your NASA NeoWs key (overrides config.json) |
| `NERV_PORT` | dashboard/stats port (default 8731) |
| `NERV_TTYD_PORT` / `NERV_SHELL_PORT` | terminal ports (default 7682 / 7683) |
| `NERV_PROJECT` | working directory the embedded terminal opens in |

Example — run an extra instance manually:

```bash
NERV_PORT=8741 NERV_TTYD_PORT=7692 NERV_SHELL_PORT=7693 NERV_PROJECT=~/code nerv-dash
```

---

## Files

```
~/.config/nerv-theme/
├── config.json                 # your NASA key (gitignored)
└── dashboard/
    ├── nerv-server.py          # stdlib backend (data sampler + HTTP + PTY terminal)
    ├── nerv-dashboard.html     # the whole frontend (vanilla JS + Canvas + xterm.js)
    ├── nerv-dash               # bash launcher (macOS/Linux)
    ├── nerv-launch.py          # portable launcher (any OS)
    ├── term-launch / shell-launch   # what the terminal runs
    └── vendor/                 # vendored xterm.js
/Applications/NERV.app          # native macOS app (WKWebView)
```

---

## Troubleshooting

- **Space weather / terminal blank** → the backend server was killed. Relaunch:
  `open -n /Applications/NERV.app` (or `nerv-dash`).
- **Panic / stuck audio** → `nerv-dash kill`.
- **Asteroid panel quiet** → you're on `DEMO_KEY` (rate-limited). Add your own free NASA
  key to `~/.config/nerv-theme/config.json`.
- **Windows terminal is basic** → native Windows uses a pipe shell (no full-screen apps).
  Run under **WSL** for the full PTY terminal.
