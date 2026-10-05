"""
Generates the profile SVGs.

  python scripts/generate_assets.py                 -> uses placeholder silhouette
  python scripts/generate_assets.py my_photo.jpg    -> turns YOUR photo into the dot portrait

Outputs (in ./assets): hero.svg, skill-radar.svg, stack-radar.svg
"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------
# EDIT THIS: your details (taken from your resume)
# ----------------------------------------------------------------------------
GITHUB_USER = "akshat-aetroiddestroyer"
LINKEDIN = "/in/akshat-balothiya-a552aa360"
INFO = [
    ("Subject",       "Akshat Balothiya"),
    ("Role",          "AI / ML Engineer - Python Dev"),
    ("Education",     "B.Tech Engineering"),
    ("Status",        "Building + Learning + Shipping"),
    ("Core.AI",       "ML - Deep Learning - GenAI - XAI"),
    ("Core.LLM",      "Groq - LLaMA-3.3 - Whisper"),
    ("Core.Lang",     "Python - Java - C - JS - TS"),
    ("Core.Web",      "React Native - HTML - CSS"),
    ("Core.Data",     "SQL - DSA - Graph Anomaly Detection"),
    ("Tools",         "Git - GitHub - REST APIs"),
    ("Achievements",  "Hackathon + Ideathon Winner"),
    ("Grid.LinkedIn", LINKEDIN),
    ("Grid.Instagram", "@holisticaaakshatt"),
    ("Grid.X",        "@venom1842924975"),
    ("Grid.GitHub",   GITHUB_USER),
]

# Radar scores are SELF-ASSESSED placeholders (0-100). Edit honestly.
SKILL_RADAR = ("Skill Radar", "AI / Machine Learning", [
    ("Python", 85), ("Machine Learning", 75), ("GenAI / LLMs", 80),
    ("Speech-to-Text", 70), ("Graph Anomaly Det.", 70), ("Explainable AI", 65),
    ("Deep Learning", 65),
])
STACK_RADAR = ("Language & Stack", "", [
    ("Python", 85), ("JavaScript", 70), ("TypeScript", 65),
    ("Java", 68), ("C", 60), ("SQL", 65),
])

BG, PANEL, BORDER = "#0b1220", "#0f1a2e", "#1c2a45"
DOT, MUTED, TEXT, ACCENT, GREEN = "#a78bfa", "#6b7a99", "#dbe4f5", "#22d3ee", "#34d399"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'JetBrains Mono',monospace"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------------
# Portrait -> dithered dots
# ----------------------------------------------------------------------------
def placeholder_portrait(w=240, h=280):
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.30, h * 0.10, w * 0.70, h * 0.52), fill=225)   # head
    d.rectangle((w * 0.43, h * 0.48, w * 0.57, h * 0.62), fill=200)  # neck
    d.ellipse((w * 0.08, h * 0.58, w * 0.92, h * 1.35), fill=190)    # shoulders
    return img.filter(ImageFilter.GaussianBlur(5))


def portrait_points(photo, cols=120, seed=7):
    img = Image.open(photo).convert("L") if photo else placeholder_portrait()
    img = ImageOps.autocontrast(img, cutoff=2)
    ratio = img.height / img.width
    img = img.resize((cols, int(cols * ratio)))
    dith = img.convert("1")  # Floyd-Steinberg dithering
    pts = [(x, y) for y in range(dith.height) for x in range(dith.width) if dith.getpixel((x, y))]
    return pts, dith.width, dith.height


# ----------------------------------------------------------------------------
# Hero card
# ----------------------------------------------------------------------------
def build_hero(photo=None):
    W, H = 860, 410
    px, py, pw, ph = 24, 52, 270, 330   # left panel
    ix, iw = 312, 524                   # right panel
    pill_w = int(len(GITHUB_USER) * 6.3 + 24)
    pts, gw, gh = portrait_points(photo)
    scale = min((pw - 40) / gw, (ph - 70) / gh)
    ox = px + (pw - gw * scale) / 2
    oy = py + 34 + (ph - 70 - gh * scale) / 2

    BANDS = 26
    bands = [[] for _ in range(BANDS)]
    for x, y in pts:
        b = min(BANDS - 1, int(y / gh * BANDS))
        bands[b].append(f"M{ox + x*scale:.1f} {oy + y*scale:.1f}h0")
    dot_w = round(scale * 0.8, 2)
    dots = [
        f'<path class="d" stroke-width="{dot_w}" style="animation-delay:{b*0.11:.2f}s" d="{"".join(seg)}"/>'
        for b, seg in enumerate(bands) if seg
    ]

    rows = []
    row_h = 17.5
    for k, v in INFO:
        i = len(rows)
        y = py + 56 + i * row_h
        x1 = ix + 18 + len(k) * 7.2 + 8
        x2 = ix + iw - 18 - len(v) * 7.2 - 8
        lead = f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y-3}" y2="{y-3}" class="lead"/>' if x2 > x1 else ""
        rows.append(
            f'<g class="row" style="animation-delay:{0.2 + i*0.12:.2f}s">'
            f'<text x="{ix+18}" y="{y}" class="k">{esc(k)}</text>{lead}'
            f'<text x="{ix+iw-18}" y="{y}" class="v" text-anchor="end">{esc(v)}</text></g>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Profile card for Akshat Balothiya">
<style>
  text{{font-family:{FONT};}}
  .t{{fill:{MUTED};font-size:11px}}
  .h{{fill:{ACCENT};font-size:11px;font-weight:700;letter-spacing:.08em}}
  .s{{fill:{MUTED};font-size:9px}}
  .k{{fill:{MUTED};font-size:12px}}
  .v{{fill:{TEXT};font-size:12px}}
  .lead{{stroke:{BORDER};stroke-dasharray:2 4}}
  .d{{fill:none;stroke:{DOT};stroke-linecap:round;opacity:0;animation:pop .6s ease-out forwards}}
  .live{{animation:blink 1.6s ease-in-out infinite}}
  .row{{opacity:0;animation:fade .6s ease-out forwards}}
  @keyframes pop{{to{{opacity:.85}}}}
  @keyframes fade{{to{{opacity:1}}}}
  @keyframes blink{{50%{{opacity:.25}}}}
  @media (prefers-reduced-motion:reduce){{.d{{opacity:.85;animation:none}}.row{{opacity:1;animation:none}}.live{{animation:none}}}}
</style>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{BORDER}"/>
<circle cx="24" cy="24" r="6" fill="#ff5f57"/><circle cx="44" cy="24" r="6" fill="#febc2e"/><circle cx="64" cy="24" r="6" fill="#28c840"/>
<text x="{W/2}" y="28" class="t" text-anchor="middle">profile.sh --live</text>

<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
<text x="{px+14}" y="{py+22}" class="h">VISUAL.MAP</text>
<text x="{px+pw-14}" y="{py+22}" class="s" text-anchor="end">{gw}x{gh} / 1-BIT</text>
<g>{''.join(dots)}</g>
<text x="{px+14}" y="{py+ph-12}" class="s">PTS {len(pts)} / FLOYD-STEINBERG</text>

<rect x="{ix}" y="{py}" width="{iw}" height="{ph}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
<text x="{ix+18}" y="{py+22}" class="h">SYSTEM.INFO</text>
<circle cx="{ix+iw-pill_w-60}" cy="{py+18}" r="3.5" fill="#f43f5e" class="live"/>
<text x="{ix+iw-pill_w-50}" y="{py+22}" fill="#f43f5e" style="font-size:10px;font-weight:700">LIVE</text>
<rect x="{ix+iw-pill_w-14}" y="{py+8}" width="{pill_w}" height="20" rx="10" fill="#16304f"/>
<text x="{ix+iw-14-pill_w/2}" y="{py+22}" text-anchor="middle" fill="{ACCENT}" style="font-size:10px">@{esc(GITHUB_USER)}</text>
{''.join(rows)}
<circle cx="{ix+18}" cy="{py+ph-14}" r="3" fill="{GREEN}"/>
<text x="{ix+28}" y="{py+ph-10}" class="s">ALL SYSTEMS NOMINAL</text>
<text x="{ix+iw-18}" y="{py+ph-10}" class="s" text-anchor="end">UTC+5:30 / INDIA NODE</text>
</svg>'''
    (OUT / "hero.svg").write_text(svg, encoding="utf-8")


# ----------------------------------------------------------------------------
# Radar charts
# ----------------------------------------------------------------------------
def build_radar(path, title, subtitle, data, size=(430, 330)):
    W, H = size
    cx, cy, R = W / 2, H / 2 + 14, 105
    n = len(data)
    ang = lambda i: -math.pi / 2 + 2 * math.pi * i / n
    pt = lambda i, r: (cx + r * math.cos(ang(i)), cy + r * math.sin(ang(i)))

    grid = []
    for lvl in (0.25, 0.5, 0.75, 1.0):
        poly = " ".join(f"{pt(i, R*lvl)[0]:.1f},{pt(i, R*lvl)[1]:.1f}" for i in range(n))
        grid.append(f'<polygon points="{poly}" fill="none" stroke="{BORDER}"/>')
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{pt(i,R)[0]:.1f}" y2="{pt(i,R)[1]:.1f}" stroke="{BORDER}"/>'
        for i in range(n)
    )
    shape = " ".join(f"{pt(i, R*v/100)[0]:.1f},{pt(i, R*v/100)[1]:.1f}" for i, (_, v) in enumerate(data))
    dots = "".join(
        f'<circle cx="{pt(i,R*v/100)[0]:.1f}" cy="{pt(i,R*v/100)[1]:.1f}" r="3" fill="{GREEN}"/>'
        for i, (_, v) in enumerate(data)
    )
    labels = []
    for i, (name, v) in enumerate(data):
        x, y = pt(i, R + 20)
        c = math.cos(ang(i))
        anchor = "middle" if abs(c) < 0.2 else ("start" if c > 0 else "end")
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="l">{esc(name)}</text>'
            f'<text x="{x:.1f}" y="{y+11:.1f}" text-anchor="{anchor}" class="n">{v}</text>'
        )
    sub = f'<text x="{cx}" y="36" text-anchor="middle" class="n">{esc(subtitle)}</text>' if subtitle else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">
<style>text{{font-family:{FONT}}}.l{{fill:{TEXT};font-size:10.5px}}.n{{fill:{MUTED};font-size:9.5px}}.ti{{fill:#fff;font-size:12px;font-weight:700}}
.shape{{transform-origin:{cx}px {cy}px;animation:grow 1.2s ease-out}}@keyframes grow{{from{{transform:scale(.1);opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.shape{{animation:none}}}}</style>
<rect width="{W}" height="{H}" fill="{BG}"/>
<text x="{cx}" y="22" text-anchor="middle" class="ti">{esc(title)}</text>{sub}
{''.join(grid)}{axes}
<g class="shape"><polygon points="{shape}" fill="#6d4fd6" fill-opacity=".35" stroke="{GREEN}" stroke-width="1.8"/>{dots}</g>
{''.join(labels)}
</svg>'''
    (OUT / path).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    photo = sys.argv[1] if len(sys.argv) > 1 else None
    build_hero(photo)
    build_radar("skill-radar.svg", *SKILL_RADAR)
    build_radar("stack-radar.svg", *STACK_RADAR)
    print("Generated:", ", ".join(sorted(p.name for p in OUT.glob("*.svg"))))
