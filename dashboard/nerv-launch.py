#!/usr/bin/env python3
"""Cross-platform NERV launcher (macOS · Linux · Windows).

Finds a free port, starts the stdlib backend (nerv-server.py), and opens the
console. With --app it opens a chromeless standalone window (Chrome/Edge/Chromium
in --app mode) so it feels like a native app; otherwise it opens your browser.

  python3 nerv-launch.py [PROJECT_DIR]           # open in your default browser
  python3 nerv-launch.py --app [PROJECT_DIR]     # open a standalone app window

On Windows use  nerv-app-windows.bat ; on Linux use  nerv-app-linux.sh  (or the
NERV Console desktop entry). The bash `nerv-dash` launcher (macOS/Linux) has more
subcommands; this is the portable path that works everywhere.
"""
import os, sys, socket, subprocess, time, webbrowser, urllib.request, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))

def free_triplet():
    def used(p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: s.bind(("127.0.0.1", p)); return False
        except OSError: return True
        finally: s.close()
    for i in range(0, 21):
        s, t, h = 8731 + i*10, 7682 + i*10, 7683 + i*10
        if not used(s) and not used(t) and not used(h): return s, t, h
    raise SystemExit("no free port triplet found")

def find_chromium():
    """Locate a Chromium-family browser for --app window mode. Returns a path or None."""
    if sys.platform.startswith("win"):
        pf   = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        la   = os.environ.get("LocalAppData", "")
        cands = [
            os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf,   r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf,   r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(la,   r"Google\Chrome\Application\chrome.exe") if la else "",
            os.path.join(pf,   r"BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
    elif sys.platform == "darwin":
        cands = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:  # linux / bsd
        names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "microsoft-edge-stable", "brave-browser"]
        cands = [shutil.which(n) for n in names]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None

def open_app_window(url):
    """Open a chromeless standalone window if possible; else fall back to the browser."""
    exe = find_chromium()
    if not exe:
        webbrowser.open(url); return None
    profile = os.path.join(tempfile.gettempdir(), "nerv-app-profile")
    args = [exe, "--app=" + url, "--new-window",
            "--user-data-dir=" + profile,
            "--window-size=1600,1000", "--no-first-run", "--no-default-browser-check"]
    try:
        return subprocess.Popen(args)
    except Exception:
        webbrowser.open(url); return None

def main():
    app_mode = False
    args = []
    for a in sys.argv[1:]:
        if a == "--app": app_mode = True
        else: args.append(a)
    project = args[0] if args else os.getcwd()

    stats, ttyd, shell = free_triplet()
    env = os.environ.copy()
    env["NERV_PORT"], env["NERV_TTYD_PORT"], env["NERV_SHELL_PORT"] = str(stats), str(ttyd), str(shell)
    env["NERV_PROJECT"] = project
    url = "http://127.0.0.1:%d/" % stats
    print("NERV starting on %s  (project: %s)" % (url, project))
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "nerv-server.py")], env=env)
    # wait until the server answers, then open the window/browser
    for _ in range(60):
        try:
            urllib.request.urlopen(url + "ping", timeout=1); break
        except Exception:
            if proc.poll() is not None: raise SystemExit("server exited early")
            time.sleep(0.25)
    win = open_app_window(url) if app_mode else (webbrowser.open(url) or None)
    print("NERV console -> %s   (Ctrl-C to stop)" % url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()
