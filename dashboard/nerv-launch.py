#!/usr/bin/env python3
"""Cross-platform NERV launcher (macOS · Linux · Windows).

Finds a free port, starts the stdlib backend (nerv-server.py), and opens the
console in your browser. Use this on Windows, or anywhere you don't have bash.

  python3 nerv-launch.py [PROJECT_DIR]

The bash `nerv-dash` launcher (macOS/Linux) has more subcommands; this is the
portable minimum that works everywhere.
"""
import os, sys, socket, subprocess, time, webbrowser, urllib.request

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

def main():
    project = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    stats, ttyd, shell = free_triplet()
    env = os.environ.copy()
    env["NERV_PORT"], env["NERV_TTYD_PORT"], env["NERV_SHELL_PORT"] = str(stats), str(ttyd), str(shell)
    env["NERV_PROJECT"] = project
    url = "http://127.0.0.1:%d/" % stats
    print("NERV starting on %s  (project: %s)" % (url, project))
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "nerv-server.py")], env=env)
    # wait until the server answers, then open the browser
    for _ in range(60):
        try:
            urllib.request.urlopen(url + "ping", timeout=1); break
        except Exception:
            if proc.poll() is not None: raise SystemExit("server exited early")
            time.sleep(0.25)
    webbrowser.open(url)
    print("NERV console -> %s   (Ctrl-C to stop)" % url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()
