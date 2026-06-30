#!/usr/bin/env python3
"""Generate the NERV 'Hex MAGI core' app icon.
Renders at high resolution then downscales for clean edges; writes NERV-icon.png
(1024) which install.sh turns into NERV.icns. Pure-PIL, no external assets."""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter

S = 2048                      # supersample canvas; final icon is S//2
C = S // 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "NERV-icon.png")

AMBER=(232,161,60); RED=(255,59,59); GREEN=(70,232,138); ORANGE=(255,140,58)
BG0=(8,11,16); BG1=(2,4,7)

def hexagon(cx, cy, r, rot=math.pi/2):
    return [(cx + r*math.cos(rot + i*math.pi/3), cy + r*math.sin(rot + i*math.pi/3)) for i in range(6)]

# ---- background squircle ----
base = Image.new("RGBA", (S, S), (0,0,0,0))
bd = ImageDraw.Draw(base)
rad = int(S*0.225)
# radial gradient fill
grad = Image.new("RGBA", (S, S), (0,0,0,0))
gp = grad.load()
for y in range(S):
    for x in range(0, S, 4):
        d = math.hypot(x-C, y-C) / (S*0.72)
        t = min(1.0, d)
        col = tuple(int(BG0[i]*(1-t)+BG1[i]*t) for i in range(3))
        for dx in range(4):
            if x+dx < S: gp[x+dx, y] = col + (255,)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([S*0.06, S*0.06, S*0.94, S*0.94], radius=rad, fill=255)
base.paste(grad, (0,0), mask)
bd = ImageDraw.Draw(base)

glow = Image.new("RGBA", (S, S), (0,0,0,0))      # everything bright goes here too, then blurred
gd = ImageDraw.Draw(glow)

def dark(color, f=0.16): return tuple(int(c*f) for c in color)
def stroke_hex(draw, cx, cy, r, color, w, darkfill=False, inner=True):
    pts = hexagon(cx, cy, r)
    if darkfill:
        draw.polygon(pts, fill=dark(color)+(235,))      # dark-tinted interior so the rim reads as neon
    draw.line(pts+[pts[0]], fill=color+(255,), width=w, joint="curve")

# ---- three MAGI satellite hexes + links ----
core_r = int(S*0.150)
sat_r  = int(S*0.072)
ring   = int(S*0.235)
sats = [(math.pi/2, RED), (math.pi/2+2*math.pi/3, GREEN), (math.pi/2+4*math.pi/3, ORANGE)]
for ang, col in sats:
    sx, sy = C + ring*math.cos(ang), C - ring*math.sin(ang)
    for d in (bd, gd):
        d.line([(C,C),(sx,sy)], fill=col+(170,), width=max(3,S//340))
    stroke_hex(bd, sx, sy, sat_r, col, max(6,S//185), darkfill=True)
    stroke_hex(gd, sx, sy, sat_r, col, max(6,S//185))     # glow rim

# ---- core hexagon ----
stroke_hex(bd, C, C, core_r, AMBER, max(9,S//140), darkfill=True)
stroke_hex(gd, C, C, core_r, AMBER, max(9,S//140))
stroke_hex(bd, C, C, int(core_r*0.82), AMBER, max(3,S//360))   # inner ring accent

# ---- center '>_' prompt (font-independent) ----
def prompt(draw, glowpass=False):
    a = AMBER+(255,)
    w = max(10, S//120)
    ax, ay = C - int(S*0.052), C
    ch = int(S*0.060)
    draw.line([(ax-ch*0.5, ay-ch), (ax+ch*0.5, ay), (ax-ch*0.5, ay+ch)], fill=a, width=w, joint="curve")
    # blinking-block cursor
    bx0, by0 = C + int(S*0.012), C - int(S*0.052)
    bx1, by1 = C + int(S*0.085), C + int(S*0.052)
    draw.rectangle([bx0,by0,bx1,by1], fill=AMBER+(235,))
prompt(bd); prompt(gd)

# ---- composite glow under crisp ----
glow_blur = glow.filter(ImageFilter.GaussianBlur(S//120))
out = Image.alpha_composite(base, glow_blur)
out = Image.alpha_composite(out, base)   # crisp on top of glow

# faint scanlines inside the squircle
sl = Image.new("RGBA", (S, S), (0,0,0,0))
sd = ImageDraw.Draw(sl)
for y in range(0, S, 6):
    sd.line([(0,y),(S,y)], fill=(0,0,0,40), width=2)
slm = Image.new("RGBA", (S,S),(0,0,0,0)); slm.paste(sl,(0,0),mask)
out = Image.alpha_composite(out, slm)

# subtle inner border ring on the squircle
bord = Image.new("RGBA",(S,S),(0,0,0,0))
ImageDraw.Draw(bord).rounded_rectangle([S*0.06,S*0.06,S*0.94,S*0.94], radius=rad, outline=AMBER+(90,), width=max(3,S//300))
out = Image.alpha_composite(out, bord)

final = out.resize((S//2, S//2), Image.LANCZOS)
final.save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT), final.size)
