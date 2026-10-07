"""
Generates the profile SVGs (hero card + radar charts).

  python scripts/prepare_portrait.py my_photo.jpg      # once: makes scripts/portrait_cutout.png
  python scripts/generate_assets.py                    # builds assets/*.svg

Hero = flat 2D stipple portrait (serpentine Floyd-Steinberg, ~18k dots) + a looping
particle "VISUAL.MAP":  </> glyph -> window icon -> portrait -> scatter -> </>
"""
import math, random, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
CUTOUT = ROOT / "scripts" / "portrait_cutout.png"

# ----------------------------------------------------------------------------
# EDIT THIS: your details (from your resume)
# ----------------------------------------------------------------------------
GITHUB_USER = "akshat-aetroiddestroyer"
INFO = [
    ("Subject",        "Akshat Balothiya"),
    ("Role",           "AI / ML Engineer \u00b7 Python Dev"),
    ("Origin",         "India"),
    ("Education",      "B.Tech \u00b7 Engineering"),
    ("Status",         "Building + Learning + Shipping"),
    ("ToolChain",      "Git \u00b7 GitHub \u00b7 REST APIs"),
    ("Core.Lang",      "Python \u00b7 Java \u00b7 C \u00b7 JavaScript \u00b7 TypeScript"),
    ("Core.AI",        "ML \u00b7 Deep Learning \u00b7 GenAI \u00b7 XAI"),
    ("Core.LLM",       "Groq \u00b7 LLaMA-3.3 \u00b7 Whisper"),
    ("Core.Frontend",  "React Native \u00b7 HTML \u00b7 CSS"),
    ("Core.Data",      "SQL \u00b7 DSA \u00b7 Graph Anomaly Detection"),
    ("Grid.Mail",      "akahatbalothiya@gmail.com"),
    ("Grid.LinkedIn",  "/in/akshat-balothiya-a552aa360"),
    ("Grid.Instagram", "@holisticaaakshatt"),
    ("Grid.GitHub",    GITHUB_USER),
    ("Grid.X",         "@venom1842924975"),
]
FOOTER_RIGHT = "UTC+5:30 \u00b7 INDIA NODE"

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

BG, PANEL, BORDER = "#0b1220", "#0f1a2e", "#1c2a45"          # (radar charts)
MUTED, TEXT, ACCENT, GREEN = "#6b7a99", "#dbe4f5", "#22d3ee", "#34d399"
CARD, PANEL2, EDGE = "#0b1426", "#0d192e", "#1c2a46"          # (hero card)
DOT = "#AA9BEF"
KEYC, VALC = "#7a8ba8", "#e8eefc"
FONT = "ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------------
# Stipple portrait: serpentine Floyd-Steinberg at a dot budget (~18k)
# ----------------------------------------------------------------------------
def serpentine_fs(tone):
    img = tone.astype(float).copy()
    h, w = img.shape
    out = np.zeros((h, w), bool)
    for y in range(h):
        d = 1 if y % 2 == 0 else -1
        xs = range(w) if d == 1 else range(w - 1, -1, -1)
        for x in xs:
            old = img[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            out[y, x] = new > 0
            e = old - new
            xn = x + d
            if 0 <= xn < w:
                img[y, xn] += e * 7 / 16
            if y + 1 < h:
                if 0 <= x - d < w:
                    img[y + 1, x - d] += e * 3 / 16
                img[y + 1, x] += e * 5 / 16
                if 0 <= xn < w:
                    img[y + 1, xn] += e * 1 / 16
    return out


def build_portrait(cutout, cols=210, target=18000):
    im = Image.open(cutout).convert("L")
    rows = round(cols * im.height / im.width)
    g = np.asarray(im.resize((cols, rows), Image.LANCZOS), float) / 255
    valid = g > 0.03
    lo, hi, best = 0.4, 3.2, None
    for _ in range(12):                      # bisect the tone curve until we hit the dot budget
        gamma = (lo + hi) / 2
        dots = serpentine_fs(np.power(g, gamma)) & valid
        best = dots
        if dots.sum() > target:
            lo = gamma
        else:
            hi = gamma
    ys, xs = np.nonzero(best)
    return np.c_[xs, ys].astype(float), cols, rows


# ----------------------------------------------------------------------------
# Shape scenes (2D): </> glyph, window icon, scatter ring  -- N dots morph between them
# ----------------------------------------------------------------------------
N_SHAPE = 1750
CYCLE = 12.5


def sample_strokes(strokes, n, rng, jitter):
    segs, lens = [], []
    for pl in strokes:
        for a, b in zip(pl[:-1], pl[1:]):
            a, b = np.array(a, float), np.array(b, float)
            segs.append((a, b)); lens.append(np.linalg.norm(b - a))
    lens = np.array(lens)
    idx = rng.choice(len(segs), size=n, p=lens / lens.sum())
    a = np.array([segs[i][0] for i in idx]); b = np.array([segs[i][1] for i in idx])
    return a + (b - a) * rng.random(n)[:, None] + rng.normal(0, jitter, (n, 2))


def scene_glyph(c, n, rng):
    st = [[(-22, -32), (-54, 0), (-22, 32)], [(13, -46), (-13, 46)], [(22, -32), (54, 0), (22, 32)]]
    return sample_strokes([[(c[0] + x, c[1] + y) for x, y in s_] for s_ in st], n, rng, .75)


def scene_window(c, n, rng):
    r = 50
    sq = [(-r, -r), (r, -r), (r, r), (-r, r), (-r, -r)]
    cross = [[(-r, 0), (r, 0)], [(0, -r), (0, r)]]
    strokes = [[(c[0] + x, c[1] + y) for x, y in sq]] + [[(c[0] + x, c[1] + y) for x, y in s_] for s_ in cross]
    main = sample_strokes(strokes, int(n * .88), rng, .7)
    core = np.array(c) + rng.normal(0, 4.5, (n - len(main), 2))
    return np.vstack([main, core])


def scene_ring(c, n, rng):
    a = rng.random(n) * 2 * math.pi
    r = np.abs(rng.normal(64, 24, n))
    return np.c_[c[0] + np.cos(a) * r, c[1] + np.sin(a) * r]


def match(prev, nxt):
    cost = cdist(prev, nxt, "sqeuclidean")
    r, c = linear_sum_assignment(cost)
    out = np.empty_like(nxt); out[r] = nxt[c]
    return out


def path10(arr):
    """integer coords at 10x (the <g> is scaled by .1): compact + precise to 0.1px"""
    return "".join(f"M{int(round(x*10))} {int(round(y*10))}h0" for x, y in arr)


def tl(times):
    return ";".join(f"{t/CYCLE:.4f}" for t in times)


# ----------------------------------------------------------------------------
# Hero card
# ----------------------------------------------------------------------------
def build_hero(cutout):
    W, H = 880, 446
    px, py, pw, ph = 16, 57, 320, 361          # VISUAL.MAP panel
    ix, iw = 352, 512                          # SYSTEM.INFO panel
    rng = np.random.default_rng(21)

    # --- portrait ---------------------------------------------------------
    P, cols, rows = build_portrait(cutout)
    n_pts = len(P)
    box_top, box_h = py + 50, 268
    pitch = box_h / rows
    ox = px + pw / 2 - cols * pitch / 2
    P = np.c_[ox + P[:, 0] * pitch, box_top + P[:, 1] * pitch]
    cy_shape = box_top + box_h / 2
    center = (px + pw / 2, cy_shape)

    # dissolve groups: mostly top->bottom with a noisy edge
    G = 36
    key = 0.68 * (P[:, 1] - P[:, 1].min()) / (np.ptp(P[:, 1]) + 1e-9) + 0.32 * rng.random(n_pts)
    rank = np.argsort(np.argsort(key))
    grp = np.minimum(G - 1, rank * G // n_pts)
    t_in, t_out, fade = 4.2, 8.3, 0.5
    portrait = []
    for g in range(G):
        pts = P[grp == g]
        r = t_in + g / G * 1.0
        d = t_out + (G - 1 - g) / G * 1.0
        kt = [0, r, r + fade, d, d + fade, CYCLE]
        portrait.append(
            f'<path stroke-width="9.6" d="{path10(pts)}"><animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
            f'keyTimes="{tl(kt)}" values="0;0;1;1;0;0"/></path>')

    # --- shapes -----------------------------------------------------------
    A = scene_glyph(center, N_SHAPE, rng)
    A = A[np.argsort(A[:, 1])]
    B = match(A, scene_window(center, N_SHAPE, rng))
    C = match(B, scene_ring(center, N_SHAPE, rng))
    T = [0, 1.8, 2.8, 4.0, 7.5, 11.0, CYCLE]
    seq = [A, A, B, B, C, C, A]
    ease, hold = "0.45 0 0.2 1", "0 0 1 1"
    splines = ";".join([hold, ease, hold, ease, hold, ease])
    shapes = (f'<path stroke-width="14" d="{path10(A)}"><animate attributeName="d" dur="{CYCLE}s" repeatCount="indefinite" '
              f'calcMode="spline" keyTimes="{tl(T)}" keySplines="{splines}" values="{";".join(path10(s_) for s_ in seq)}"/></path>')
    shapes_fade = f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" keyTimes="{tl([0, 4.0, 4.8, 8.7, 9.5, CYCLE])}" values="1;1;0;0;1;1"/>'

    # --- right panel ------------------------------------------------------
    pill_w = int(len(GITHUB_USER) * 5.9 + 24)
    row0, row_h = py + 52, 17.1
    rows_svg = []
    cw = 6.3
    for i, (k, v) in enumerate(INFO):
        y = row0 + i * row_h
        x1 = ix + 16 + len(k) * cw + 8
        x2 = ix + iw - 16 - len(v) * cw - 8
        lead = f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y-3}" y2="{y-3}" class="lead"/>' if x2 > x1 else ""
        rows_svg.append(f'<text x="{ix+16}" y="{y:.1f}" class="k">{esc(k)}</text>{lead}'
                        f'<text x="{ix+iw-16}" y="{y:.1f}" class="v" text-anchor="end">{esc(v)}</text>')

    def bracket(x, y, sx, sy, s=10):
        return f"M{x} {y+sy*s}V{y}H{x+sx*s}"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Animated profile card for Akshat Balothiya">
<style>
  text{{font-family:{FONT}}}
  .t{{fill:#6b7a99;font-size:9.5px}}
  .h{{fill:{ACCENT};font-size:9.5px;font-weight:700;letter-spacing:.07em}}
  .s{{fill:#5d6f94;font-size:8px}}
  .k{{fill:{KEYC};font-size:10.5px}}
  .v{{fill:{VALC};font-size:10.5px}}
  .lead{{stroke:#2a3a5c;stroke-dasharray:1 3}}
  .live{{animation:blink 1.8s ease-in-out infinite}}
  @keyframes blink{{50%{{opacity:.3}}}}
</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{CARD}" stroke="{EDGE}"/>
<circle cx="20" cy="19" r="4.6" fill="#ef4452"/><circle cx="36" cy="19" r="4.6" fill="#f5b324"/><circle cx="52" cy="19" r="4.6" fill="#33c75a"/>
<text x="{W/2}" y="22" class="t" text-anchor="middle">profile.sh --live</text>
<line x1="1" x2="{W-1}" y1="37" y2="37" stroke="{EDGE}"/>

<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="6" fill="{PANEL2}" stroke="{EDGE}"/>
<line x1="{px}" x2="{px+pw}" y1="{py+29}" y2="{py+29}" stroke="{EDGE}"/>
<text x="{px+12}" y="{py+19}" class="h">VISUAL.MAP</text>
<text x="{px+pw-12}" y="{py+19}" class="s" text-anchor="end">{cols}\u00d7{rows} / 1-BIT</text>
<path d="{bracket(px+12, py+40, 1, 1)} {bracket(px+pw-12, py+40, -1, 1)} {bracket(px+12, py+ph-14, 1, -1)} {bracket(px+pw-12, py+ph-14, -1, -1)}" fill="none" stroke="#35506f" stroke-width="1.1"/>
<g transform="scale(.1)" fill="none" stroke="{DOT}" stroke-linecap="round">
  <g opacity="0" stroke-opacity=".85">{shapes}{shapes_fade}</g>
  <g>{''.join(portrait)}</g>
</g>
<text x="{px+16}" y="{py+ph-8}" class="s">PTS {n_pts} \u00b7 FS/SERPENTINE</text>

<rect x="{ix}" y="{py}" width="{iw}" height="{ph}" rx="6" fill="{PANEL2}" stroke="{EDGE}"/>
<line x1="{ix}" x2="{ix+iw}" y1="{py+29}" y2="{py+29}" stroke="{EDGE}"/>
<text x="{ix+12}" y="{py+19}" class="h">SYSTEM.INFO</text>
<circle cx="{ix+iw-pill_w-46}" cy="{py+15}" r="3" fill="#f43f5e" class="live"/>
<text x="{ix+iw-pill_w-39}" y="{py+18.5}" fill="#f43f5e" style="font-size:8px;font-weight:700;letter-spacing:.05em">LIVE</text>
<rect x="{ix+iw-pill_w-10}" y="{py+5}" width="{pill_w}" height="19" rx="9.5" fill="#102a3d"/>
<text x="{ix+iw-10-pill_w/2}" y="{py+18}" text-anchor="middle" fill="{ACCENT}" style="font-size:9.5px;font-weight:700">@{esc(GITHUB_USER)}</text>
{''.join(rows_svg)}
<line x1="{ix+10}" x2="{ix+iw-10}" y1="{py+ph-26}" y2="{py+ph-26}" stroke="{EDGE}"/>
<circle cx="{ix+14}" cy="{py+ph-10}" r="2.2" fill="{GREEN}"/>
<text x="{ix+21}" y="{py+ph-7.5}" fill="{GREEN}" style="font-size:7.5px;letter-spacing:.04em">ALL SYSTEMS NOMINAL</text>
<text x="{ix+iw-12}" y="{py+ph-7.5}" class="s" text-anchor="end">{esc(FOOTER_RIGHT)}</text>
</svg>"""
    (OUT / "hero.svg").write_text(svg, encoding="utf-8")
    return n_pts, cols, rows


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
    cut = Path(sys.argv[1]) if len(sys.argv) > 1 else CUTOUT
    if not cut.exists():
        sys.exit("Missing portrait cut-out. Run: python scripts/prepare_portrait.py my_photo.jpg")
    n, c, r = build_hero(cut)
    build_radar("skill-radar.svg", *SKILL_RADAR)
    build_radar("stack-radar.svg", *STACK_RADAR)
    print(f"hero: {n} dots on a {c}x{r} grid | Generated:", ", ".join(sorted(p.name for p in OUT.glob("*.svg"))))
