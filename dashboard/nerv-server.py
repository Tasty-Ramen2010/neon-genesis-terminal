#!/usr/bin/env python3
"""NERV dashboard backend — stdlib only (no pip deps).

One background sampler thread runs all system/network/NASA sampling on bounded
cadences and caches results; HTTP handlers only read the cache (polling can never
spawn per-request work). Endpoints:
  GET  /stats   cached system + network-connection + ISS + NEO snapshot (JSON)
  GET  /todo    current to-do list (JSON)
  POST /todo    {action:add|toggle|delete|clear, text?, id?}
  GET  /        the dashboard HTML
"""
import http.server, socketserver, json, subprocess, threading, time, os, sys, re, math
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("NERV_PORT", "8731"))
TTYD_PORT = int(os.environ.get("NERV_TTYD_PORT", "7682"))    # injected into the page so multi-instance works
SHELL_PORT = int(os.environ.get("NERV_SHELL_PORT", "7683"))
PROJECT = os.environ.get("NERV_PROJECT", os.path.expanduser("~"))
TODO_FILE = os.path.expanduser("~/.config/nerv-theme/todo.json")

def _load_config():
    """Settings precedence: env var > ~/.config/nerv-theme/config.json > DEMO_KEY.
    Keeps personal keys out of the committed source."""
    cfg = {}
    for p in (os.path.expanduser("~/.config/nerv-theme/config.json"), os.path.join(HERE, "config.json")):
        try:
            with open(p) as f: cfg.update(json.load(f)); break
        except Exception: pass
    return cfg
_CFG = _load_config()
NASA_KEY = os.environ.get("NASA_API_KEY") or _CFG.get("nasa_api_key") or "DEMO_KEY"

_stats = {"ready": False}
_lock = threading.Lock()

def sh(cmd, timeout=4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""

def get_json(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NERV/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def default_iface():
    for line in sh(["route", "-n", "get", "default"]).splitlines():
        if "interface:" in line:
            return line.split()[-1]
    return "en0"

# ---------------- to-do storage ----------------
_todo_lock = threading.Lock()
def todo_load():
    try:
        with open(TODO_FILE) as f: return json.load(f)
    except Exception:
        return {"items": [], "seq": 0}
def todo_save(d):
    os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)
    with open(TODO_FILE, "w") as f: json.dump(d, f)
def todo_apply(action, text=None, tid=None):
    with _todo_lock:
        d = todo_load()
        if action == "add" and text:
            d["seq"] = d.get("seq", 0) + 1
            d["items"].append({"id": d["seq"], "text": text[:200], "done": False, "t": time.time()})
        elif action == "toggle" and tid is not None:
            for it in d["items"]:
                if it["id"] == tid: it["done"] = not it["done"]
        elif action == "delete" and tid is not None:
            d["items"] = [it for it in d["items"] if it["id"] != tid]
        elif action == "clear":
            d["items"] = [it for it in d["items"] if not it["done"]]
        todo_save(d); return d

PORTSVC = {443:"HTTPS",80:"HTTP",53:"DNS",22:"SSH",993:"IMAPS",587:"SMTP",5223:"APNs",
           8731:"NERV",7682:"TERM",3478:"STUN",123:"NTP",1900:"SSDP",5353:"mDNS"}

class Sampler(threading.Thread):
    daemon = True
    def __init__(self):
        super().__init__()
        self.iface = default_iface()
        self.pagesize = int(sh(["sysctl","-n","hw.pagesize"]).strip() or 16384)
        self.memtotal = int(sh(["sysctl","-n","hw.memsize"]).strip() or 1)
        self.ncpu = int(sh(["sysctl","-n","hw.ncpu"]).strip() or 1)
        self._prev_net = None
        self._prev_np = {}   # per-process cumulative bytes (for rates)
        self.iss = None
        self.neo = []
        self.conns = []
        self.spaceweather = None
        self.sats = []       # real satellites (orbital elements from Celestrak TLE)

    def cpu(self):
        for line in sh(["top","-l","1","-n","0"]).splitlines():
            if "CPU usage" in line:
                try: return max(0.0, min(100.0, 100.0 - float(line.split(",")[-1].strip().split("%")[0])))
                except Exception: return 0.0
        return 0.0
    def mem(self):
        out = sh(["vm_stat"])
        def g(k,i):
            for l in out.splitlines():
                if k in l: return int(l.split()[i].rstrip("."))
            return 0
        used = (g("Pages active:",2)+g("Pages wired down:",3)+g("occupied by compressor:",4))*self.pagesize
        return round(used*100.0/self.memtotal,1), round(used/1073741824,1), round(self.memtotal/1073741824,1)
    def net(self):
        out = sh(["netstat","-ib"]); ib=ob=0
        for l in out.splitlines():
            f=l.split()
            if f and f[0]==self.iface and len(f)>=10 and f[6].isdigit(): ib=int(f[6]);ob=int(f[9]);break
        now=time.time(); down=up=0.0
        if self._prev_net:
            pt,pi,po=self._prev_net; dt=max(0.5,now-pt)
            down=max(0,(ib-pi))/dt; up=max(0,(ob-po))/dt
        self._prev_net=(now,ib,ob); return down,up
    def disk(self):
        for l in sh(["df","-k","/"]).splitlines()[1:]:
            f=l.split()
            if len(f)>=5: return float(f[4].rstrip("%"))
        return 0.0
    def procs(self):
        out=sh(["ps","-Aro","pid,%cpu,%mem,comm"]); res=[]
        for l in out.splitlines()[1:16]:
            p=l.strip().split(None,3)
            if len(p)==4:
                res.append({"pid":p[0],"cpu":float(p[1]),"mem":float(p[2]),"name":os.path.basename(p[3])[:20]})
        return res
    def mem_detail(self):
        out=sh(["vm_stat"]); ps=self.pagesize
        def g(k,i):
            for l in out.splitlines():
                if k in l: return int(l.split()[i].rstrip("."))
            return 0
        gb=lambda pages: round(pages*ps/1073741824,2)
        return {"active":gb(g("Pages active:",2)),"wired":gb(g("Pages wired down:",3)),
                "compressed":gb(g("occupied by compressor:",4)),"free":gb(g("Pages free:",2)+g("Pages inactive:",2))}
    def net_procs(self):
        # per-process bandwidth (iftop/nethogs-style) via nettop cumulative byte diff
        out=sh(["nettop","-P","-x","-n","-L","1"], timeout=3)
        cur={}; res=[]
        for l in out.splitlines()[1:]:
            f=l.split(",")
            if len(f)<6 or not f[1]: continue
            name=f[1]
            try: bi=int(f[4]); bo=int(f[5])
            except Exception: continue
            cur[name]=(bi,bo)
            if name in self._prev_np:
                pi,po=self._prev_np[name]; din=max(0,bi-pi); dout=max(0,bo-po)
                if din+dout>0:
                    proc=name.rsplit(".",1)[0][:18]
                    res.append({"proc":proc,"down":din,"up":dout})
        self._prev_np=cur
        res.sort(key=lambda x:x["down"]+x["up"], reverse=True)
        return res[:12]
    def battery(self):
        out=sh(["pmset","-g","batt"]); pct=100
        m=re.search(r"(\d+)%",out)
        if m: pct=int(m.group(1))
        ch = "AC Power" in out or "charging" in out.lower() or "charged" in out.lower()
        return pct, ch
    def connections(self):
        # real active TCP connections: which app -> which remote host:port
        out=sh(["lsof","-nP","-iTCP","-sTCP:ESTABLISHED"], timeout=3)
        res=[]; seen=set()
        for l in out.splitlines()[1:]:
            f=l.split()
            if len(f)<9: continue
            proc=f[0][:14]; name=f[8]
            if "->" not in name: continue
            remote=name.split("->")[1]
            host,_,port=remote.rpartition(":")
            try: port=int(port)
            except: port=0
            if host.startswith(("127.","::1","*","[::1")): continue
            key=(proc,host,port)
            if key in seen: continue
            seen.add(key)
            res.append({"proc":proc,"host":host,"port":port,"svc":PORTSVC.get(port,str(port))})
            if len(res)>=40: break
        return res
    def git(self):
        d=PROJECT
        if not sh(["git","-C",d,"rev-parse","--git-dir"]).strip(): return {"repo":False}
        porc=sh(["git","-C",d,"status","--porcelain"]).splitlines()
        return {"repo":True,"branch":sh(["git","-C",d,"branch","--show-current"]).strip() or "detached",
                "staged":sum(1 for l in porc if l[:1] not in (" ","?","")),
                "modified":sum(1 for l in porc if l[1:2]=="M"),
                "untracked":sum(1 for l in porc if l.startswith("??")),
                "last":sh(["git","-C",d,"log","-1","--format=%s"]).strip()[:40],
                "age":sh(["git","-C",d,"log","-1","--format=%cr"]).strip()}
    def fetch_spaceweather(self):
        out={}
        kp=get_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json", timeout=6)
        if kp and len(kp)>1:
            last=kp[-1]   # NOAA returns list-of-dicts ({"Kp":4.33,...}); tolerate list-of-lists too
            try:
                if isinstance(last,dict): out["kp"]=float(last.get("Kp")); out["kp_time"]=last.get("time_tag")
                else: out["kp"]=float(last[1]); out["kp_time"]=last[0]
            except Exception: pass
        wind=get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json", timeout=6)
        if wind and len(wind)>1:
            for row in reversed(wind[1:]):
                try: out["wind_speed"]=round(float(row[2])); out["wind_density"]=round(float(row[1]),1); break
                except Exception: pass
        mag=get_json("https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json", timeout=6)
        if mag and len(mag)>1:
            for row in reversed(mag[1:]):
                try: out["bz"]=round(float(row[3]),1); break
                except Exception: pass
        if out:
            kpv=out.get("kp",0)
            out["storm"] = "SEVERE" if kpv>=7 else "STORM" if kpv>=5 else "ACTIVE" if kpv>=4 else "QUIET"
            out["aurora"] = kpv>=5
            self.spaceweather=out
    def fetch_sats(self):
        # real satellites: Celestrak TLE -> mean orbital elements (approx Keplerian)
        groups=[("starlink",900),("gps-ops",60),("oneweb",200),("galileo",40),("glo-ops",40),("stations",40),("weather",60),("geo",80)]
        MU=398600.4418; RE=6371.0
        out=[]
        for grp,cap in groups:
            txt=""
            try:
                req=urllib.request.Request(f"https://celestrak.org/NORAD/elements/gp.php?GROUP={grp}&FORMAT=tle",headers={"User-Agent":"NERV/1.0"})
                with urllib.request.urlopen(req,timeout=10) as r: txt=r.read().decode(errors="ignore")
            except Exception: continue
            lines=txt.splitlines(); n=0
            for i in range(0,len(lines)-2,3):
                if n>=cap: break
                try:
                    name=lines[i].strip(); l2=lines[i+2]
                    if not l2.startswith("2 "): continue
                    inc=float(l2[8:16]); raan=float(l2[17:25])
                    ecc=float("0."+l2[26:33].strip()); argp=float(l2[34:42]); ma=float(l2[43:51])
                    mm=float(l2[52:63])  # revs/day
                    if mm<=0: continue
                    nrad=mm*2*math.pi/86400.0
                    a=(MU/(nrad*nrad))**(1.0/3.0)
                    r=a/RE  # earth radii
                    if r<1.0 or r>8: continue
                    out.append({"n":name[:22],"g":grp,"inc":inc,"raan":raan,"e":ecc,"argp":argp,"ma":ma,"mm":mm,"r":round(r,3)})
                    n+=1
                except Exception: pass
        if out: self.sats=out
    def fetch_iss(self):
        j=get_json("http://api.open-notify.org/iss-now.json", timeout=5)   # fast, keyless, works here
        if j and j.get("iss_position"):
            p=j["iss_position"]
            self.iss={"lat":float(p["latitude"]),"lon":float(p["longitude"]),"alt":420,"vel":27600}; return
        j=get_json("https://api.wheretheiss.at/v1/satellites/25544", timeout=4)  # fallback (richer)
        if j and "latitude" in j:
            self.iss={"lat":float(j["latitude"]),"lon":float(j["longitude"]),
                      "alt":round(j.get("altitude",0)),"vel":round(j.get("velocity",0))}
    def fetch_neo(self):
        from datetime import date, timedelta
        out=[]
        start=date.today()
        for wk in range(3):   # 3 consecutive weeks -> lots more asteroids
            s=start+timedelta(days=wk*7); e=s+timedelta(days=6)
            j=get_json(f"https://api.nasa.gov/neo/rest/v1/feed?start_date={s.isoformat()}&end_date={e.isoformat()}&api_key={NASA_KEY}", timeout=8)
            if not (j and "near_earth_objects" in j): continue
            for day,objs in j["near_earth_objects"].items():
                for o in objs:
                    try:
                        ca=o["close_approach_data"][0]
                        out.append({"name":o["name"].strip("()"),
                            "dia":round(o["estimated_diameter"]["meters"]["estimated_diameter_max"]),
                            "hazard":o["is_potentially_hazardous_asteroid"],
                            "miss_km":round(float(ca["miss_distance"]["kilometers"])),
                            "miss_lunar":round(float(ca["miss_distance"]["lunar"]),1),
                            "vel":round(float(ca["relative_velocity"]["kilometers_per_hour"]))})
                    except Exception: pass
        # de-dup by name, sort by miss distance, keep a big set
        seen=set(); uniq=[]
        for a in sorted(out,key=lambda x:x["miss_km"]):
            if a["name"] in seen: continue
            seen.add(a["name"]); uniq.append(a)
        self.neo=uniq[:120]

    def run(self):
        c=0
        # ISS is fast (~1s) so seed it before the loop; the slower external feeds
        # (neo/spaceweather/sats) fire on early loop iterations so the first
        # system-stats snapshot publishes immediately instead of blocking ~40s.
        try: self.fetch_iss()
        except Exception: pass
        while True:
            try:
                cpu=self.cpu(); mempct,memu,memt=self.mem(); down,up=self.net()
                load=sh(["sysctl","-n","vm.loadavg"]).split()
                load=float(load[1]) if len(load)>1 else 0.0
                u=sh(["uptime"]); upt=u.split("up",1)[1].split(",")[0].strip()[:14] if "up" in u else ""
                bpct,ch=self.battery()
                self.conns=self.connections()
                netprocs=self.net_procs()
                memd=self.mem_detail()
                if c%3==0:
                    try: self.fetch_iss()
                    except Exception: pass
                if c==2 or c%1200==5:    # seed early, then ~ every 30 min
                    try: self.fetch_neo()
                    except Exception: pass
                if c==3 or c%120==20:    # seed early, then ~ every 3 min
                    try: self.fetch_spaceweather()
                    except Exception: pass
                if c==5 or c%2400==40:   # seed early, then ~ every hour (TLE changes slowly)
                    try: self.fetch_sats()
                    except Exception: pass
                snap={"ready":True,"t":time.time(),"cpu":round(cpu,1),"ncpu":self.ncpu,
                    "mem":mempct,"mem_used":memu,"mem_total":memt,
                    "net_down":round(down),"net_up":round(up),"iface":self.iface,
                    "disk":self.disk(),"load":load,"uptime":upt,"procs":self.procs(),
                    "battery":bpct,"charging":ch,"git":self.git(),
                    "project":os.path.basename(PROJECT),"host":sh(["hostname","-s"]).strip(),
                    "user":os.environ.get("USER","operator"),
                    "conns":self.conns,"conn_count":len(self.conns),
                    "net_procs":netprocs,"mem_detail":memd,
                    "iss":self.iss,"neo":self.neo,
                    "spaceweather":self.spaceweather,"sats":self.sats}
                with _lock: _stats.clear(); _stats.update(snap)
            except Exception as e:
                with _lock: _stats["error"]=str(e)
            c+=1; time.sleep(1.5)

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _send(self,code,body,ctype):
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Cache-Control","no-store"); self.end_headers()
        self.wfile.write(body if isinstance(body,bytes) else body.encode())
    def do_GET(self):
        if self.path.startswith("/stats"):
            with _lock: self._send(200,json.dumps(_stats),"application/json")
        elif self.path.startswith("/todo"):
            self._send(200,json.dumps(todo_load()),"application/json")
        elif self.path.startswith("/ping"):
            self._send(200,"ok","text/plain")
        elif self.path=="/" or self.path.startswith("/index"):
            try:
                with open(os.path.join(HERE,"nerv-dashboard.html"),encoding="utf-8") as f: html=f.read()
                inject=f'<script>window.NERV_TTYD_PORT={TTYD_PORT};window.NERV_SHELL_PORT={SHELL_PORT};window.NERV_STATS_PORT={PORT};</script>'
                html=html.replace("</head>",inject+"</head>",1)
                self._send(200,html.encode("utf-8"),"text/html; charset=utf-8")
            except Exception as e: self._send(500,f"missing html: {e}","text/plain")
        else: self._send(404,"not found","text/plain")
    def do_POST(self):
        if self.path.startswith("/todo"):
            try:
                n=int(self.headers.get("Content-Length",0)); body=json.loads(self.rfile.read(n) or b"{}")
                d=todo_apply(body.get("action"),body.get("text"),body.get("id"))
                self._send(200,json.dumps(d),"application/json")
            except Exception as e: self._send(400,json.dumps({"error":str(e)}),"application/json")
        else: self._send(404,"not found","text/plain")

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True; daemon_threads=True

if __name__=="__main__":
    Sampler().start()
    try:
        with Server(("127.0.0.1",PORT),Handler) as httpd:
            print(f"NERV backend on http://127.0.0.1:{PORT}"); httpd.serve_forever()
    except OSError as e:
        print(f"port {PORT} unavailable: {e}",file=sys.stderr); sys.exit(1)
