#!/usr/bin/env python3
"""Render the v4 one-page newspaper image (1024x1024 PNG) from stories.json.

v4 builds on v3 (same 36 stories, facts, badges, sources, numbers strip,
region colour bar, dark UTC strip, ALSO ON list, map, DATE CHECK, footer
and date masthead) with two changes from the winners' design:
  1. Every illustrated story carries a red topic bar at the top of its
     illustration with the story's main topic in short white caps
     (rank 1 style); the 3 big stories also carry a second white bar
     top-right with a secondary fact.
  2. The 15 illustrated scenes are richer mini-scenes (background,
     ground, subject, props, detail dots), still flat PIL vector with
     one accent colour per scene.
All text is real, legible type (DejaVu) -- no generated imagery. The
renderer prints a TRUNCATED warning for any headline/summary that wraps
past its line budget; v4 renders with none.

Usage: python3 render.py stories.json news.png
"""
import json
import math
import sys
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
BG = (248, 244, 232)
INK = (17, 17, 17)
RED = (163, 18, 18)
SALMON = (232, 110, 100)
MUTED = (90, 84, 70)
RULE = (60, 55, 45)
LIGHT = (226, 219, 198)
NAVY = (24, 32, 56)
MAP_LAND = (206, 214, 196)
MAP_LINE = (120, 118, 108)

BADGE = {
    "CONFIRMED": (46, 125, 50),
    "OFFICIAL": (29, 78, 216),
    "REPORTED": (55, 65, 81),
    "CLAIM": (180, 83, 9),
    "FORECAST": (107, 114, 128),
    "PENDING": (29, 78, 216),
}

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size, fallback=None):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(fallback or SERIF, size)


def wrap(draw, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, x, y, lines, fnt, fill, lh):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def chip(d, x_right, y, text, size=9):
    """Badge chip, right-aligned at x_right. Returns its left edge."""
    f = font(SANS_B, size)
    tw = d.textlength(text, font=f)
    pad_x, pad_y = 5, 2
    h = size + 2 * pad_y + 3
    x0 = x_right - int(tw) - 2 * pad_x
    d.rounded_rectangle([x0, y, x_right, y + h], radius=3,
                        fill=BADGE.get(text, (55, 65, 81)))
    d.text((x0 + pad_x, y + pad_y), text, font=f, fill=(255, 255, 255))
    return x0


def redbar(d, x, y, size, text, h=16, max_w=None):
    """Red topic bar at the top-left of an illustration (rank 1 style).

    White bold caps text centred in a red rectangle; the font shrinks
    until the bar fits max_w. Returns the bar width in pixels.
    """
    f = font(SANS_B, size)
    while max_w is not None and d.textlength(text, font=f) + 12 > max_w and f.size > 6:
        f = font(SANS_B, f.size - 1)
    tw = d.textlength(text, font=f)
    bw = int(tw) + 12
    d.rectangle([x, y, x + bw, y + h], fill=RED)
    d.text((x + 6, y + (h - f.size) // 2 - 1), text, font=f, fill=(255, 255, 255))
    return bw


def whitebar(d, x_right, y, size, text, h=16):
    """White secondary bar at the top-right of a big illustration.

    Dark bold caps text centred in a white rectangle. Returns the bar
    width in pixels.
    """
    f = font(SANS_B, size)
    tw = d.textlength(text, font=f)
    bw = int(tw) + 12
    d.rectangle([x_right - bw, y, x_right, y + h], fill=(255, 255, 255))
    d.text((x_right - bw + 6, y + (h - f.size) // 2 - 1), text, font=f,
           fill=(30, 30, 40))
    return bw


# Rough continent outlines (lon, lat) for the WHERE IT HAPPENED map.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 66), (-75, 62), (-65, 60), (-55, 52), (-60, 47), (-70, 44), (-75, 40), (-80, 32), (-85, 30), (-90, 21), (-95, 19), (-100, 16), (-105, 20), (-110, 23), (-115, 30), (-125, 40), (-125, 49), (-135, 58), (-150, 60), (-165, 60)],
    [(-80, 10), (-75, 7), (-65, 5), (-55, 5), (-50, 0), (-40, -5), (-35, -10), (-40, -20), (-48, -28), (-55, -35), (-65, -45), (-70, -55), (-73, -40), (-72, -20), (-78, -5)],
    [(-10, 36), (-5, 44), (0, 50), (5, 55), (10, 58), (18, 56), (20, 60), (25, 65), (30, 70), (35, 68), (40, 60), (30, 55), (25, 50), (20, 45), (15, 44), (10, 38), (0, 36)],
    [(-10, 35), (0, 36), (10, 37), (20, 32), (30, 31), (35, 28), (40, 20), (48, 11), (51, 10), (45, 0), (40, -10), (35, -20), (30, -30), (20, -35), (15, -28), (12, -18), (10, -5), (5, 5), (-5, 5), (-10, 15), (-15, 25)],
    [(35, 68), (50, 70), (70, 72), (100, 75), (130, 72), (160, 70), (178, 65), (170, 60), (160, 55), (140, 50), (135, 45), (130, 35), (125, 30), (120, 25), (110, 20), (105, 10), (100, 8), (95, 15), (90, 22), (85, 20), (80, 10), (75, 8), (70, 25), (60, 25), (55, 28), (50, 30), (45, 35), (40, 38)],
    [(113, -22), (120, -15), (130, -12), (135, -15), (140, -17), (145, -15), (150, -22), (153, -28), (150, -37), (145, -38), (140, -38), (135, -35), (130, -32), (125, -32), (120, -35), (115, -33), (113, -25)],
]


# ---------------------------------------------------------------- scenes
def scene_cop31(d, x, y, w, h):
    """Antalya at dawn: navy-to-orange sky bands, sun with rays, purple
    mountains, skyline with lit windows, sea with reflection lines."""
    d.rectangle([x, y, x + w, y + int(h * 0.38)], fill=(38, 44, 78))
    d.rectangle([x, y + int(h * 0.38), x + w, y + int(h * 0.66)], fill=(214, 106, 59))
    d.rectangle([x, y + int(h * 0.66), x + w, y + int(h * 0.82)], fill=(240, 180, 90))
    # purple mountain silhouettes behind the skyline
    d.polygon([(x, y + int(h * 0.82)), (x + int(w * 0.22), y + int(h * 0.52)),
               (x + int(w * 0.45), y + int(h * 0.82))], fill=(90, 60, 110))
    d.polygon([(x + int(w * 0.55), y + int(h * 0.82)), (x + int(w * 0.78), y + int(h * 0.58)),
               (x + w, y + int(h * 0.82))], fill=(90, 60, 110))
    # sun with short rays
    cx, cy, r = x + int(w * 0.62), y + int(h * 0.52), int(h * 0.15)
    for ang in range(0, 360, 30):
        ex1 = cx + int((r + 8) * math.cos(math.radians(ang)))
        ey1 = cy + int((r + 8) * math.sin(math.radians(ang)))
        ex2 = cx + int((r + 16) * math.cos(math.radians(ang)))
        ey2 = cy + int((r + 16) * math.sin(math.radians(ang)))
        d.line([(ex1, ey1), (ex2, ey2)], fill=(250, 214, 140), width=2)
    d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=(250, 214, 140))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 233, 168))
    # two birds, clear of the red topic bar (top-left) and the white bar
    for bx, by in [(0.18, 0.22), (0.45, 0.12)]:
        px, py = x + int(w * bx), y + int(h * by)
        d.line([(px - 5, py), (px, py - 3), (px + 5, py)], fill=(30, 30, 40), width=2)
    base = y + int(h * 0.82)
    skyline = [(0, 0.42), (0.10, 0.55), (0.20, 0.34), (0.30, 0.50), (0.40, 0.30),
               (0.50, 0.52), (0.60, 0.38), (0.70, 0.56), (0.80, 0.34), (0.90, 0.48)]
    for fx, fh in skyline:
        bx = x + int(w * fx)
        bw = max(8, int(w * 0.09))
        d.rectangle([bx, base - int(h * fh), bx + bw, base], fill=(28, 28, 34))
        for wy in range(3):
            d.rectangle([bx + 3, base - int(h * fh) + 5 + wy * 9, bx + 6,
                         base - int(h * fh) + 8 + wy * 9], fill=(255, 214, 110))
    d.rectangle([x, base, x + w, y + h], fill=(31, 58, 95))
    d.line([(x + 10, base + 5), (x + w - 40, base + 5)], fill=(150, 190, 220), width=1)
    d.line([(x + 40, base + 11), (x + w - 10, base + 11)], fill=(150, 190, 220), width=1)
    d.line([(x + 70, base + 16), (x + w - 60, base + 16)], fill=(150, 190, 220), width=1)


def scene_drones(d, x, y, w, h):
    """Kyiv at night: dark sky, stars, two real searchlight beams from
    rooftops, lit towers, a church dome, drones with dotted trails."""
    d.rectangle([x, y, x + w, y + h], fill=(16, 22, 44))
    for sx, sy in [(0.08, 0.14), (0.22, 0.08), (0.36, 0.18), (0.52, 0.10),
                   (0.66, 0.16), (0.80, 0.07), (0.92, 0.20), (0.45, 0.26)]:
        d.ellipse([x + int(w * sx) - 1, y + int(h * sy) - 1,
                   x + int(w * sx) + 1, y + int(h * sy) + 1], fill=(255, 255, 255))
    base = y + h
    # searchlight beams: wide faint polygon behind a narrower brighter
    # one, both from the same rooftop. Drawn before the towers so the
    # tower tops cover the beam bases.
    bx1 = x + int(w * 0.22) + int(w * 0.13) // 2
    roof1 = base - int(h * 0.68)
    d.polygon([(bx1 - 8, roof1), (bx1 + 8, roof1),
               (x + int(w * 0.66), y + int(h * 0.10)),
               (x + int(w * 0.56), y + int(h * 0.10))], fill=(70, 72, 90))
    d.polygon([(bx1 - 4, roof1), (bx1 + 4, roof1),
               (x + int(w * 0.63), y + int(h * 0.10)),
               (x + int(w * 0.59), y + int(h * 0.10))], fill=(200, 200, 170))
    bx2 = x + int(w * 0.62) + int(w * 0.14) // 2
    roof2 = base - int(h * 0.60)
    d.polygon([(bx2 - 7, roof2), (bx2 + 7, roof2),
               (x + int(w * 0.76), y + int(h * 0.12)),
               (x + int(w * 0.70), y + int(h * 0.12))], fill=(70, 72, 90))
    d.polygon([(bx2 - 3, roof2), (bx2 + 3, roof2),
               (x + int(w * 0.745), y + int(h * 0.12)),
               (x + int(w * 0.715), y + int(h * 0.12))], fill=(200, 200, 170))
    # lit towers
    for fx, fw, fh in [(0.02, 0.16, 0.52), (0.22, 0.13, 0.68),
                       (0.62, 0.14, 0.60), (0.82, 0.15, 0.40)]:
        bx, bw, bh = x + int(w * fx), int(w * fw), int(h * fh)
        d.rectangle([bx, base - bh, bx + bw, base], fill=(38, 38, 54))
        for wy in range(3):
            for wx in range(3):
                if (wx + wy) % 2 == 0:
                    d.rectangle([bx + 4 + wx * 11, base - bh + 5 + wy * 11,
                                 bx + 8 + wx * 11, base - bh + 9 + wy * 11],
                                fill=(255, 214, 110))
    # church: low block with a dome and a cross, between the towers
    cx0, cx1 = x + int(w * 0.40), x + int(w * 0.57)
    d.rectangle([cx0, base - 28, cx1, base], fill=(38, 38, 54))
    d.pieslice([cx0 + 6, base - 48, cx1 - 6, base - 28], start=180, end=360,
               fill=(38, 38, 54))
    d.line([(x + int(w * 0.485), base - 56), (x + int(w * 0.485), base - 46)],
           fill=(38, 38, 54), width=2)
    d.line([(x + int(w * 0.475), base - 53), (x + int(w * 0.495), base - 53)],
           fill=(38, 38, 54), width=2)
    for wy in (8, 18):
        d.rectangle([cx0 + 8, base - wy - 4, cx0 + 13, base - wy],
                    fill=(255, 214, 110))
    # bright source dots on the two beam rooftops
    d.ellipse([bx1 - 3, roof1 - 3, bx1 + 3, roof1 + 3], fill=(255, 240, 180))
    d.ellipse([bx2 - 3, roof2 - 3, bx2 + 3, roof2 + 3], fill=(255, 240, 180))
    # drones: small X shapes with dotted trails (five now)
    for dx, dy, s in [(0.55, 0.22, 7), (0.74, 0.34, 6), (0.88, 0.16, 5),
                      (0.40, 0.30, 6), (0.68, 0.48, 5)]:
        cx, cy = x + int(w * dx), y + int(h * dy)
        d.line([(cx - s, cy - s), (cx + s, cy + s)], fill=(255, 220, 130), width=2)
        d.line([(cx - s, cy + s), (cx + s, cy - s)], fill=(255, 220, 130), width=2)
        for k in range(1, 5):
            d.ellipse([cx - s - k * 9 - 1, cy + k * 4 - 1,
                       cx - s - k * 9 + 1, cy + k * 4 + 1], fill=(255, 220, 130))
    # one orange burst top right
    bx, by = x + int(w * 0.90), y + int(h * 0.42)
    d.ellipse([bx - 7, by - 7, bx + 7, by + 7], fill=(255, 140, 40))
    for ang in range(0, 360, 60):
        ex = bx + int(12 * math.cos(math.radians(ang)))
        ey = by + int(12 * math.sin(math.radians(ang)))
        d.line([(bx, by), (ex, ey)], fill=(255, 140, 40), width=2)


def scene_bahrain(d, x, y, w, h):
    """Bahrain at night: radar blocks burning with smoke, sea with
    reflection dashes, ship with containers and bridge, missile arc
    with an orange flash at its end."""
    d.rectangle([x, y, x + w, y + h], fill=(18, 26, 52))
    for sx, sy in [(0.10, 0.12), (0.30, 0.08), (0.55, 0.14), (0.75, 0.08), (0.90, 0.18)]:
        d.ellipse([x + int(w * sx) - 1, y + int(h * sy) - 1,
                   x + int(w * sx) + 1, y + int(h * sy) + 1], fill=(255, 255, 255))
    sea = y + int(h * 0.70)
    d.rectangle([x, sea, x + w, y + h], fill=(28, 68, 110))
    # two radar/industrial blocks with flames and smoke clouds
    for fx, fw in [(0.08, 0.20), (0.38, 0.20)]:
        bx, bw = x + int(w * fx), int(w * fw)
        d.rectangle([bx, sea - 34, bx + bw, sea], fill=(125, 130, 140))
        d.ellipse([bx + bw // 2 - 10, sea - 46, bx + bw // 2 + 10, sea - 30],
                  fill=(150, 155, 165))
        cxm = bx + bw // 2
        # flames, tips lowered to stay clear of the red topic bar
        d.polygon([(cxm - 12, sea - 36), (cxm + 12, sea - 36),
                   (cxm, sea - 48)], fill=(255, 140, 40))
        d.polygon([(cxm - 6, sea - 36), (cxm + 6, sea - 36),
                   (cxm, sea - 42)], fill=(255, 214, 110))
        # grey smoke clouds drifting right of the flames
        d.ellipse([cxm + 8, sea - 52, cxm + 28, sea - 42], fill=(120, 125, 135))
        d.ellipse([cxm + 20, sea - 58, cxm + 38, sea - 48], fill=(140, 145, 155))
        # sea reflection dashes under the flames
        d.line([(bx + 4, sea + 6), (bx + bw - 4, sea + 6)], fill=(255, 160, 60), width=2)
        d.line([(bx + 10, sea + 12), (bx + bw - 10, sea + 12)], fill=(255, 160, 60), width=1)
    # ship on the right: hull, containers, bridge block
    sx0 = x + int(w * 0.68)
    d.polygon([(sx0, sea + 4), (sx0 + int(w * 0.24), sea + 4),
               (sx0 + int(w * 0.20), sea + 14), (sx0 + 6, sea + 14)], fill=(20, 20, 28))
    d.rectangle([sx0 + 10, sea - 6, sx0 + 34, sea + 4], fill=(150, 60, 50))
    d.rectangle([sx0 + 38, sea - 6, sx0 + 58, sea + 4], fill=(70, 110, 160))
    d.rectangle([sx0 + 62, sea - 6, sx0 + 82, sea + 4], fill=(150, 150, 140))
    d.rectangle([sx0 + 66, sea - 18, sx0 + 82, sea - 6], fill=(220, 220, 210))
    d.rectangle([sx0 + 69, sea - 15, sx0 + 79, sea - 11], fill=(40, 80, 120))
    # two ship wake lines
    d.line([(sx0 - 20, sea + 16), (sx0 + int(w * 0.24), sea + 16)],
           fill=(150, 190, 220), width=1)
    d.line([(sx0 - 34, sea + 22), (sx0 + int(w * 0.20), sea + 22)],
           fill=(150, 190, 220), width=1)
    # dotted missile arc, starting below the red topic bar, with an
    # orange flash at its end
    for k in range(7):
        t = k / 6.0
        ax = x + int(w * (0.05 + 0.35 * t))
        ay = y + int(h * (0.16 + 0.22 * t * t))
        d.ellipse([ax - 2, ay - 2, ax + 2, ay + 2], fill=(255, 255, 255))
    fxe, fye = x + int(w * 0.40), y + int(h * 0.38)
    d.ellipse([fxe - 6, fye - 6, fxe + 6, fye + 6], fill=(255, 140, 40))


def _small_bg(d, x, y, w, h, color):
    d.rectangle([x, y, x + w, y + h], fill=color)


def scene_ballot(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (233, 227, 204))
    # Hong Kong skyline silhouettes at the back
    for fx, fw, fh in [(0.02, 0.10, 0.30), (0.14, 0.08, 0.42), (0.24, 0.10, 0.26),
                       (0.36, 0.09, 0.36), (0.48, 0.08, 0.28)]:
        d.rectangle([x + int(w * fx), y + int(h * 0.55) - int(h * fh),
                     x + int(w * fx) + int(w * fw), y + int(h * 0.55)],
                    fill=(190, 182, 158))
    d.rectangle([x, y + int(h * 0.55), x + w, y + h], fill=(214, 206, 180))
    # voting booth: white box with a ballot paper and a green check
    d.rectangle([x + 52, y + 12, x + 100, y + 44], fill=(255, 255, 255), outline=(60, 55, 45), width=2)
    d.rectangle([x + 66, y + 12, x + 86, y + 16], fill=(163, 18, 18))
    d.line([(x + 58, y + 34), (x + 68, y + 42), (x + 92, y + 20)], fill=(46, 125, 50), width=3)
    # ballot box with a red slot band
    d.rectangle([x + 12, y + 30, x + 34, y + 44], fill=(255, 255, 255), outline=(60, 55, 45), width=1)
    d.rectangle([x + 12, y + 30, x + 34, y + 34], fill=(163, 18, 18))
    # three voter dots queuing
    for vx, vy in [(112, 40), (124, 42), (136, 40)]:
        d.ellipse([x + vx, y + vy, x + vx + 7, y + vy + 7], fill=(60, 55, 45))
        d.ellipse([x + vx - 1, y + vy + 8, x + vx + 8, y + vy + 13], fill=(60, 55, 45))


def scene_cricket(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (74, 140, 74))
    # white boundary rope arc
    d.arc([x + 8, y + 2, x + w - 8, y + h + 30], start=180, end=360,
          fill=(255, 255, 255), width=2)
    # light pitch strip down the middle
    d.rectangle([x + 64, y + 4, x + 88, y + 50], fill=(222, 200, 150))
    # stumps at both ends
    for wx in range(3):
        d.line([(x + 70 + wx * 5, y + 8), (x + 70 + wx * 5, y + 16)], fill=(255, 255, 255), width=2)
        d.line([(x + 70 + wx * 5, y + 40), (x + 70 + wx * 5, y + 48)], fill=(255, 255, 255), width=2)
    # batsman silhouette mid-swing
    d.ellipse([x + 96, y + 16, x + 104, y + 24], fill=(40, 40, 40))
    d.polygon([(x + 98, y + 24), (x + 104, y + 24), (x + 108, y + 38), (x + 94, y + 38)],
              fill=(40, 40, 40))
    d.line([(x + 104, y + 30), (x + 114, y + 20)], fill=(150, 105, 60), width=3)
    # red ball and a fielder dot
    d.ellipse([x + 116, y + 30, x + 124, y + 38], fill=(180, 30, 30))
    d.ellipse([x + 20, y + 14, x + 28, y + 22], fill=(255, 255, 255))
    # small scoreboard block "720/9"
    d.rectangle([x + 8, y + 36, x + 44, y + 48], fill=(20, 20, 28))
    d.text((x + 12, y + 38), "720/9", font=font(SANS_B, 8), fill=(255, 255, 255))


def scene_race(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (20, 24, 40))
    # checkered start line across the top
    for i in range(15):
        d.rectangle([x + i * 11, y, x + (i + 1) * 11, y + 10],
                    fill=(255, 255, 255) if i % 2 == 0 else (20, 20, 20))
    # grandstand strip with crowd dots
    d.rectangle([x, y + 10, x + w, y + 18], fill=(60, 60, 80))
    for cx in range(6, w - 4, 9):
        d.ellipse([x + cx, y + 12, x + cx + 5, y + 17],
                  fill=(255, 220, 130) if cx % 18 == 6 else (200, 200, 220))
    # two floodlight poles with glow dots
    for px in (10, 138):
        d.line([(x + px, y + 18), (x + px, y + 30)], fill=(180, 180, 180), width=2)
        d.ellipse([x + px - 3, y + 14, x + px + 3, y + 20], fill=(255, 240, 180))
    # red F1 car with speed lines
    d.rectangle([x + 42, y + 30, x + 112, y + 40], fill=(180, 30, 30))
    d.rectangle([x + 62, y + 22, x + 88, y + 30], fill=(180, 30, 30))
    d.polygon([(x + 42, y + 30), (x + 34, y + 34), (x + 42, y + 38)], fill=(120, 20, 20))
    for wx in (52, 96):
        d.ellipse([x + wx, y + 38, x + wx + 12, y + 50], fill=(10, 10, 10),
                  outline=(180, 180, 180), width=1)
    d.line([(x + 14, y + 34), (x + 34, y + 34)], fill=(255, 220, 130), width=2)
    d.line([(x + 20, y + 42), (x + 36, y + 42)], fill=(255, 220, 130), width=2)


def scene_basket(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (222, 160, 90))
    # court lines and centre circle
    d.line([(x, y + 40), (x + w, y + 40)], fill=(255, 255, 255), width=2)
    d.ellipse([x + 52, y + 26, x + 100, y + 54], outline=(255, 255, 255), width=2)
    # crowd strip along the bottom
    d.rectangle([x, y + 48, x + w, y + h], fill=(120, 70, 40))
    for cx in range(4, w - 4, 10):
        d.ellipse([x + cx, y + 49, x + cx + 5, y + 53],
                  fill=(255, 220, 180) if cx % 20 == 4 else (240, 200, 160))
    # hoop: backboard and rim on the right
    d.rectangle([x + 142, y + 8, x + 148, y + 30], fill=(255, 255, 255),
                outline=(60, 55, 45), width=1)
    d.ellipse([x + 132, y + 28, x + 144, y + 36], outline=(200, 60, 20), width=2)
    d.line([(x + 134, y + 36), (x + 138, y + 44)], fill=(255, 255, 255), width=1)
    d.line([(x + 142, y + 36), (x + 138, y + 44)], fill=(255, 255, 255), width=1)
    # orange ball mid-air
    d.ellipse([x + 108, y + 10, x + 132, y + 34], fill=(230, 110, 30),
              outline=(120, 60, 10), width=2)
    d.arc([x + 108, y + 10, x + 132, y + 34], start=200, end=340, fill=(120, 60, 10), width=2)
    d.line([(x + 120, y + 10), (x + 120, y + 34)], fill=(120, 60, 10), width=2)
    # jumping player silhouette
    d.ellipse([x + 60, y + 18, x + 68, y + 26], fill=(40, 40, 40))
    d.polygon([(x + 62, y + 26), (x + 68, y + 26), (x + 72, y + 42), (x + 58, y + 42)],
              fill=(40, 40, 40))
    d.line([(x + 66, y + 28), (x + 78, y + 18)], fill=(40, 40, 40), width=3)


def scene_ship(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (60, 110, 160))
    # gull dots in the sky
    for gx, gy in [(20, 6), (40, 10), (120, 6), (138, 10)]:
        d.line([(x + gx, y + gy), (x + gx + 4, y + gy + 2), (x + gx + 8, y + gy)],
               fill=(255, 255, 255), width=1)
    # sea with white wave arcs
    d.rectangle([x, y + 34, x + w, y + h], fill=(30, 80, 130))
    d.arc([x + 8, y + 38, x + 48, y + 50], start=180, end=360, fill=(255, 255, 255), width=2)
    d.arc([x + 96, y + 40, x + 140, y + 52], start=180, end=360, fill=(255, 255, 255), width=2)
    # ship hull with three coloured containers
    d.polygon([(x + 18, y + 26), (x + 136, y + 26), (x + 126, y + 40), (x + 28, y + 40)],
              fill=(20, 20, 28))
    d.rectangle([x + 30, y + 12, x + 52, y + 26], fill=(180, 60, 50))
    d.rectangle([x + 56, y + 12, x + 78, y + 26], fill=(70, 110, 160))
    d.rectangle([x + 82, y + 12, x + 104, y + 26], fill=(150, 150, 140))
    # flames and smoke above the deck, clear of the red topic bar
    d.polygon([(x + 88, y + 12), (x + 100, y + 12), (x + 94, y + 2)], fill=(255, 140, 40))
    d.polygon([(x + 92, y + 12), (x + 98, y + 12), (x + 95, y + 6)], fill=(255, 214, 110))
    for sx, sy in [(108, 4), (124, 2), (136, 6)]:
        d.ellipse([x + sx, y + sy, x + sx + 14, y + sy + 8], fill=(200, 200, 200))
    # small rescue boat
    d.polygon([(x + 118, y + 44), (x + 146, y + 44), (x + 140, y + 50), (x + 124, y + 50)],
              fill=(200, 60, 40))


def scene_powercut(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (28, 28, 44))
    # dark night skyline of three towers, two windows lit yellow
    for fx, fw, fh in [(0.05, 0.24, 0.62), (0.35, 0.28, 0.78), (0.70, 0.24, 0.55)]:
        bx, bw, bh = x + int(w * fx), int(w * fw), int(h * fh)
        d.rectangle([bx, y + h - bh, bx + bw, y + h], fill=(48, 48, 64))
        for wy in range(3):
            for wx in range(2):
                lit = (fx == 0.35 and wy == 1 and wx == 0) or (fx == 0.05 and wy == 0 and wx == 1)
                col = (255, 214, 110) if lit else (18, 18, 28)
                d.rectangle([bx + 5 + wx * 14, y + h - bh + 6 + wy * 12,
                             bx + 10 + wx * 14, y + h - bh + 11 + wy * 12], fill=col)
    # crescent moon
    d.ellipse([x + 128, y + 6, x + 140, y + 18], fill=(240, 230, 200))
    d.ellipse([x + 132, y + 6, x + 142, y + 18], fill=(28, 28, 44))
    # power-line pole with a broken wire and a small spark star
    d.line([(x + 118, y + 22), (x + 118, y + 46)], fill=(120, 120, 130), width=2)
    d.line([(x + 110, y + 26), (x + 126, y + 26)], fill=(120, 120, 130), width=2)
    d.line([(x + 118, y + 26), (x + 130, y + 34)], fill=(120, 120, 130), width=1)
    d.line([(x + 130, y + 34), (x + 138, y + 32)], fill=(120, 120, 130), width=1)
    sx, sy = x + 130, y + 34
    d.line([(sx - 4, sy), (sx + 4, sy)], fill=(255, 220, 130), width=1)
    d.line([(sx, sy - 4), (sx, sy + 4)], fill=(255, 220, 130), width=1)


def scene_hospital(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (235, 235, 228))
    d.rectangle([x, y + 40, x + w, y + h], fill=(120, 170, 90))
    # white hospital building with a red cross sign and lit windows
    d.rectangle([x + 40, y + 12, x + 112, y + 40], fill=(255, 255, 255),
                outline=(60, 55, 45), width=2)
    d.rectangle([x + 70, y + 16, x + 78, y + 32], fill=(200, 30, 30))
    d.rectangle([x + 64, y + 22, x + 84, y + 28], fill=(200, 30, 30))
    for wx in (48, 90):
        d.rectangle([x + wx, y + 18, x + wx + 8, y + 26], fill=(120, 170, 200))
    # white ambulance with a red cross on the lawn
    d.rectangle([x + 116, y + 34, x + 148, y + 46], fill=(255, 255, 255),
                outline=(60, 55, 45), width=1)
    d.rectangle([x + 128, y + 37, x + 132, y + 43], fill=(200, 30, 30))
    d.rectangle([x + 125, y + 39, x + 135, y + 41], fill=(200, 30, 30))
    d.ellipse([x + 120, y + 44, x + 126, y + 50], fill=(20, 20, 20))
    d.ellipse([x + 138, y + 44, x + 144, y + 50], fill=(20, 20, 20))
    # red ECG line across the bottom
    d.line([(x + 6, y + 50), (x + 20, y + 50), (x + 24, y + 44), (x + 28, y + 52),
            (x + 32, y + 47), (x + 36, y + 50), (x + 60, y + 50)], fill=(200, 30, 30), width=2)


def scene_fbi(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (52, 68, 96))
    # grid of small light rectangles (data rows)
    for r in range(3):
        for c in range(4):
            d.rectangle([x + 10 + c * 13, y + 10 + r * 12, x + 20 + c * 13, y + 19 + r * 12],
                        fill=(160, 180, 210) if (r + c) % 3 else (220, 230, 245))
    # fingerprint: concentric arcs in yellow
    cx, cy = x + 104, y + 24
    for rr in (4, 7, 10):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=200, end=340,
              fill=(255, 214, 110), width=2)
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=20, end=160,
              fill=(255, 214, 110), width=2)
    # large white magnifier ring over the fingerprint
    d.ellipse([x + 84, y + 8, x + 124, y + 40], outline=(255, 255, 255), width=3)
    d.line([(x + 116, y + 34), (x + 136, y + 48)], fill=(255, 255, 255), width=3)
    # small warning triangle, bottom right
    d.polygon([(x + 140, y + 48), (x + 150, y + 48), (x + 145, y + 36)], fill=(255, 200, 40))
    d.text((x + 143, y + 40), "!", font=font(SANS_B, 8), fill=(40, 40, 40))


def scene_strike(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (200, 220, 235))
    # tarmac strip
    d.rectangle([x, y + 42, x + w, y + h], fill=(120, 125, 135))
    # control tower, top below the red topic bar
    d.rectangle([x + 8, y + 20, x + 16, y + 42], fill=(90, 95, 105))
    d.rectangle([x + 4, y + 14, x + 20, y + 20], fill=(70, 75, 85))
    d.rectangle([x + 7, y + 16, x + 17, y + 19], fill=(150, 200, 230))
    # departure board with two red CANCELLED lines
    d.rectangle([x + 118, y + 8, x + 148, y + 22], fill=(20, 20, 28))
    d.line([(x + 121, y + 12), (x + 145, y + 12)], fill=(200, 30, 30), width=2)
    d.line([(x + 121, y + 18), (x + 145, y + 18)], fill=(200, 30, 30), width=2)
    # grounded plane silhouette
    d.ellipse([x + 40, y + 26, x + 110, y + 38], fill=(70, 75, 85))
    d.polygon([(x + 60, y + 28), (x + 84, y + 16), (x + 92, y + 28)], fill=(70, 75, 85))
    d.polygon([(x + 96, y + 28), (x + 108, y + 18), (x + 112, y + 28)], fill=(70, 75, 85))
    # red diagonal cross over the plane, starting below the red bar
    d.line([(x + 18, y + 15), (x + 134, y + 48)], fill=(200, 30, 30), width=3)
    # suitcase on the tarmac
    d.rectangle([x + 118, y + 38, x + 134, y + 48], fill=(150, 60, 50),
                outline=(60, 55, 45), width=1)
    d.line([(x + 123, y + 38), (x + 129, y + 38)], fill=(60, 55, 45), width=2)


def scene_boat(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (70, 120, 170))
    # green bank with two trees, below the red topic bar
    d.rectangle([x, y, x + 24, y + h], fill=(90, 140, 70))
    for tx, ty in [(10, 24), (18, 32)]:
        d.ellipse([x + tx - 4, y + ty, x + tx + 6, y + ty + 10], fill=(50, 110, 50))
        d.line([(x + tx + 1, y + ty + 10), (x + tx + 1, y + ty + 16)], fill=(90, 60, 30), width=2)
    # river with white wave arcs
    d.rectangle([x + 24, y + 34, x + w, y + h], fill=(30, 80, 130))
    d.arc([x + 30, y + 38, x + 70, y + 50], start=180, end=360, fill=(255, 255, 255), width=2)
    d.arc([x + 96, y + 40, x + 140, y + 52], start=180, end=360, fill=(255, 255, 255), width=2)
    # tilted wooden boat with three passenger dots
    d.polygon([(x + 44, y + 18), (x + 112, y + 28), (x + 100, y + 40), (x + 52, y + 32)],
              fill=(120, 85, 50))
    for px, py in [(66, 10), (84, 14), (96, 18)]:
        d.ellipse([x + px, y + py, x + px + 6, y + py + 6], fill=(40, 40, 40))
    # orange lifebuoy ring
    d.ellipse([x + 118, y + 12, x + 134, y + 28], outline=(255, 140, 40), width=3)
    d.ellipse([x + 122, y + 16, x + 130, y + 24], outline=(255, 140, 40), width=2)
    # small rescue boat approaching from the right
    d.polygon([(x + 116, y + 38), (x + 146, y + 38), (x + 140, y + 46), (x + 122, y + 46)],
              fill=(200, 60, 40))
    d.rectangle([x + 126, y + 32, x + 136, y + 38], fill=(255, 255, 255))


def scene_fire(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (40, 30, 26))
    # dark factory: two blocks and a chimney
    d.rectangle([x + 14, y + 26, x + 60, y + h], fill=(70, 70, 78))
    d.rectangle([x + 66, y + 32, x + 112, y + h], fill=(60, 60, 68))
    d.rectangle([x + 116, y + 20, x + 124, y + 40], fill=(70, 70, 78))
    # grey smoke columns above the chimney, clear of the red topic bar
    d.ellipse([x + 118, y + 2, x + 132, y + 12], fill=(180, 180, 180))
    d.ellipse([x + 126, y + 10, x + 140, y + 20], fill=(160, 160, 160))
    # flames at the base, tips starting below the red topic bar
    for fx, fw, fh, col in [(0.14, 0.16, 0.42, (255, 90, 20)), (0.30, 0.13, 0.34, (255, 160, 40)),
                            (0.52, 0.15, 0.40, (255, 120, 30)), (0.68, 0.12, 0.30, (255, 200, 80))]:
        bx = x + int(w * fx)
        d.polygon([(bx, y + h - int(h * fh) + 14), (bx + int(w * fw), y + h - int(h * fh) + 14),
                   (bx + int(w * fw) // 2, y + 14)], fill=col)
    # red fire truck with a ladder, in front of the factory
    d.rectangle([x + 6, y + 42, x + 36, y + 51], fill=(200, 30, 30))
    d.rectangle([x + 28, y + 36, x + 42, y + 42], fill=(200, 30, 30))
    d.line([(x + 8, y + 38), (x + 38, y + 28)], fill=(180, 180, 180), width=2)
    d.ellipse([x + 12, y + 49, x + 18, y + 54], fill=(20, 20, 20))
    d.ellipse([x + 30, y + 49, x + 36, y + 54], fill=(20, 20, 20))
    # two white water-spray arcs from the ladder toward the flames
    d.arc([x + 38, y + 20, x + 70, y + 36], start=270, end=360, fill=(255, 255, 255), width=2)
    d.arc([x + 56, y + 24, x + 88, y + 40], start=270, end=360, fill=(255, 255, 255), width=2)


def scene_pope(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (238, 228, 200))
    # ground strip
    d.rectangle([x, y + 42, x + w, y + h], fill=(150, 140, 110))
    # St Peter's dome, top below the red topic bar, with antenna and cross
    d.pieslice([x + 60, y + 14, x + 108, y + 48], start=180, end=360, fill=(200, 160, 80))
    d.rectangle([x + 80, y + 8, x + 88, y + 16], fill=(200, 160, 80))
    d.line([(x + 84, y + 4), (x + 84, y + 10)], fill=(120, 100, 60), width=2)
    # colonnade blocks flanking the dome
    for cx in (30, 44, 118, 132):
        d.rectangle([x + cx, y + 30, x + cx + 8, y + 42], fill=(220, 205, 160))
    # two white doves
    for dx, dy in [(20, 20), (128, 18)]:
        d.ellipse([x + dx, y + dy, x + dx + 8, y + dy + 4], fill=(255, 255, 255))
        d.polygon([(x + dx + 6, y + dy), (x + dx + 12, y + dy - 3),
                   (x + dx + 10, y + dy + 3)], fill=(255, 255, 255))
    # two lunch tables with plates along the bottom
    for tx in (8, 116):
        d.rectangle([x + tx, y + 48, x + tx + 28, y + 52], fill=(255, 255, 255))
        d.ellipse([x + tx + 5, y + 49, x + tx + 9, y + 51], fill=(200, 160, 80))
        d.ellipse([x + tx + 17, y + 49, x + tx + 21, y + 51], fill=(200, 160, 80))
    # crowd of small dark dots between the tables
    for i in range(5):
        d.ellipse([x + 44 + i * 15, y + 46, x + 50 + i * 15, y + 52], fill=(60, 55, 45))


SCENES_BIG = {"cop31": scene_cop31, "drones": scene_drones, "bahrain": scene_bahrain}
SCENES_SMALL = {"ballot": scene_ballot, "cricket": scene_cricket, "race": scene_race,
                "basket": scene_basket, "ship": scene_ship, "powercut": scene_powercut,
                "hospital": scene_hospital, "fbi": scene_fbi, "strike": scene_strike,
                "boat": scene_boat, "fire": scene_fire, "pope": scene_pope}


def render(data, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    m = 26
    d.rectangle([10, 10, W - 11, H - 11], outline=RULE, width=2)
    d.rectangle([15, 15, W - 16, H - 16], outline=RULE, width=1)
    warnings = []

    # --- kicker + meta -------------------------------------------------
    y = 24
    f_kick = font(SANS_B, 11)
    d.text((m, y), "THE WORLD IN ONE DAY", font=f_kick, fill=RED)
    f_meta = font(SANS, 10)
    meta = data["meta"]
    d.text((W - m - d.textlength(meta, font=f_meta), y), meta, font=f_meta, fill=MUTED)

    # --- masthead: the date --------------------------------------------
    f_mast = font(SERIF_B, 64)
    title = data["date_label"]
    while d.textlength(title, font=f_mast) > W - 2 * m and f_mast.size > 40:
        f_mast = font(SERIF_B, f_mast.size - 2)
    d.text(((W - d.textlength(title, font=f_mast)) / 2, 40), title, font=f_mast, fill=INK)
    f_red = font(SERIF_I, 13, fallback=SERIF)
    red_line = data["red_line"]
    d.text(((W - d.textlength(red_line, font=f_red)) / 2, 108), red_line,
           font=f_red, fill=RED)
    d.line([(m, 130), (W - m, 130)], fill=RULE, width=2)

    # --- numbers strip --------------------------------------------------
    y = 136
    nums = data["numbers"]
    cell_w = (W - 2 * m) // len(nums)
    f_num = font(SERIF_B, 20)
    f_lab = font(SANS, 8.5)
    for i, (num, lab) in enumerate(nums):
        cx = m + i * cell_w + cell_w // 2
        if i:
            d.line([(m + i * cell_w, y + 4), (m + i * cell_w, y + 40)], fill=LIGHT, width=1)
        d.text((cx - d.textlength(num, font=f_num) / 2, y), num, font=f_num, fill=RED)
        lab_lines = wrap(d, lab, f_lab, cell_w - 10)
        ly = y + 26
        for ln in lab_lines[:2]:
            d.text((cx - d.textlength(ln, font=f_lab) / 2, ly), ln, font=f_lab, fill=MUTED)
            ly += 10

    # --- region colour bar ----------------------------------------------
    y = 184
    bar = data["regions_bar"]
    total = sum(c for _, c, _ in bar)
    bx = m
    f_bar = font(SANS_B, 10)
    for name, cnt, color in bar:
        seg_w = int((W - 2 * m) * cnt / total)
        d.rectangle([bx, y, bx + seg_w, y + 20], fill=color)
        label = f"{name} {cnt}"
        tw = d.textlength(label, font=f_bar)
        if tw > seg_w - 8:
            f_bar = font(SANS_B, 8)
            tw = d.textlength(label, font=f_bar)
        d.text((bx + (seg_w - tw) / 2, y + 4), label, font=f_bar, fill=(255, 255, 255))
        bx += seg_w
        f_bar = font(SANS_B, 10)

    # --- dark UTC strip ---------------------------------------------------
    y = 208
    d.rectangle([m, y, W - m, y + 20], fill=NAVY)
    f_utc_l = font(SANS_B, 10)
    f_utc = font(SANS, 10)
    label = "THE DAY IN UTC"
    parts = [(label, f_utc_l, SALMON)]
    for t, ev in data["utc"]:
        parts.append(("  ·  " + t + " ", f_utc_l, SALMON))
        parts.append((ev, f_utc, (255, 255, 255)))
    total_w = sum(d.textlength(t, font=f) for t, f, _ in parts)
    while total_w > W - 2 * m - 8 and f_utc.size > 8:
        f_utc = font(SANS, f_utc.size - 1)
        f_utc_l = font(SANS_B, f_utc_l.size - 1)
        total_w = sum(d.textlength(t, font=f) for t, f, _ in parts)
    tx = m + (W - 2 * m - total_w) / 2
    for t, f, col in parts:
        d.text((tx, y + 4), t, font=f, fill=col)
        tx += d.textlength(t, font=f)

    # --- 3 big illustrated stories ---------------------------------------
    y = 234
    big_w = (W - 2 * m - 2 * 12) // 3
    f_tag = font(SANS_B, 10.5)
    f_bhead = font(SERIF_B, 19)
    f_bsum = font(SANS, 11)
    f_bsrc = font(SANS, 9.5)
    for i, st in enumerate(data["big"]):
        x0 = m + i * (big_w + 12)
        SCENES_BIG[st["scene"]](d, x0, y, big_w, 100)
        # v4: red topic bar top-left + white secondary bar top-right
        wb = whitebar(d, x0 + big_w, y, 10, st["label2"], h=16) if st.get("label2") else 0
        redbar(d, x0, y, 11, st["label"], h=16, max_w=big_w - wb - 8)
        ty = y + 104
        tag = f"{st['num']}  {st['place']} · {st['topic']}"
        d.text((x0, ty), tag, font=f_tag, fill=INK)
        chip(d, x0 + big_w, ty - 1, st["badge"], size=9)
        hy = ty + 18
        hl = wrap(d, st["headline"], f_bhead, big_w)
        if len(hl) > 3:
            warnings.append(f"big {st['num']} headline {len(hl)} lines")
        hy = draw_wrapped(d, x0, hy, hl[:3], f_bhead, INK, 23)
        sm = wrap(d, st["summary"], f_bsum, big_w)
        if len(sm) > 3:
            warnings.append(f"big {st['num']} summary {len(sm)} lines")
        hy = draw_wrapped(d, x0, hy + 1, sm[:3], f_bsum, MUTED, 14.5)
        d.text((x0, hy + 1), f"({st['source']})", font=f_bsrc, fill=MUTED)

    # --- 12 small illustrated stories, 2 rows x 6 ------------------------
    y = 487
    sm_w = (W - 2 * m - 5 * 10) // 6
    f_stag = font(SANS_B, 8.5)
    f_shead = font(SERIF_B, 12.5)
    f_ssum = font(SANS, 9.5)
    for row in range(2):
        for col in range(6):
            st = data["small"][row * 6 + col]
            x0 = m + col * (sm_w + 10)
            sy = y + row * 125
            SCENES_SMALL[st["scene"]](d, x0, sy, sm_w, 54)
            # v4: red topic bar top-left of the illustration
            redbar(d, x0, sy, 8, st["label"], h=13, max_w=sm_w)
            chip(d, x0 + sm_w - 3, sy + 54 - 15, st["badge"], size=7)
            ty = sy + 58
            tag = f"{st['num']} {st['place']} · {st['topic']}"
            tag_lines = wrap(d, tag, f_stag, sm_w)
            ty = draw_wrapped(d, x0, ty, tag_lines[:1], f_stag, INK, 11)
            hy = ty + 2
            hl = wrap(d, st["headline"], f_shead, sm_w)
            if len(hl) > 2:
                warnings.append(f"small {st['num']} headline {len(hl)} lines")
            hy = draw_wrapped(d, x0, hy, hl[:2], f_shead, INK, 15)
            sm = wrap(d, f"{st['summary']} ({st['source']})", f_ssum, sm_w)
            if len(sm) > 2:
                warnings.append(f"small {st['num']} summary {len(sm)} lines")
            draw_wrapped(d, x0, hy + 1, sm[:2], f_ssum, MUTED, 12)

    # --- bottom: map + ALSO ON -------------------------------------------
    y = 749
    f_sect = font(SANS_B, 12)
    d.text((m, y), "WHERE IT HAPPENED", font=f_sect, fill=RED)
    f_cap = font(SANS, 9)
    d.text((m + 300 - d.textlength("pins match story numbers", font=f_cap), y + 2),
           "pins match story numbers", font=f_cap, fill=MUTED)
    map_x, map_y, map_w, map_h = m, y + 16, 300, 84
    d.rectangle([map_x, map_y, map_x + map_w, map_y + map_h],
                fill=(238, 238, 226), outline=MAP_LINE, width=1)

    def proj(lon, lat):
        return (map_x + (lon + 180) / 360.0 * map_w,
                map_y + (90 - lat) / 150.0 * map_h)

    for poly in CONTINENTS:
        d.polygon([proj(lon, lat) for lon, lat in poly], fill=MAP_LAND, outline=MAP_LINE)
    f_pin = font(SANS_B, 7)
    for num, lon, lat in data["pins"]:
        px, py = proj(lon, lat)
        px = min(max(px, map_x + 7), map_x + map_w - 7)
        py = min(max(py, map_y + 7), map_y + map_h - 7)
        d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=RED, outline=(255, 255, 255), width=1)
        lbl = str(num)
        d.text((px - d.textlength(lbl, font=f_pin) / 2, py - 5), lbl,
               font=f_pin, fill=(255, 255, 255))

    ax = m + 300 + 16
    aw = W - m - ax
    d.text((ax, y), "ALSO ON SUNDAY 22 NOVEMBER — 21 MORE STORIES", font=f_sect, fill=RED)
    f_also = font(SANS, 9)
    col_w = (aw - 10) // 2
    items = data["also"]
    for idx, it in enumerate(items):
        col = idx // 11
        row = idx % 11
        ix = ax + col * (col_w + 10)
        iy = y + 18 + row * 11
        line = f"{it['num']} {it['region']}: {it['text']} ({it['source']})"
        if d.textlength(line, font=f_also) > col_w:
            warnings.append(f"also {it['num']} line too long: {len(line)} chars")
        d.text((ix, iy), line, font=f_also, fill=INK)

    # --- DATE CHECK box ----------------------------------------------------
    dy = 890
    dc = data["date_check"]
    f_dc_t = font(SANS_B, 11)
    f_dc = font(SANS, 10)
    dc_lines = wrap(d, dc, f_dc, W - 2 * m - 130)
    dc_h = 12 + len(dc_lines) * 13 + 8
    d.rectangle([m, dy, W - m, dy + dc_h], outline=RED, width=1)
    d.text((m + 8, dy + 6), "DATE CHECK", font=f_dc_t, fill=RED)
    draw_wrapped(d, m + 118, dy + 6, dc_lines, f_dc, INK, 13)

    # --- footer -------------------------------------------------------------
    fy = 942
    d.line([(m, fy), (W - m, fy)], fill=RULE, width=1)
    f_foot = font(SANS, 9.5)
    legend = data["legend"]
    d.text(((W - d.textlength(legend, font=f_foot)) / 2, fy + 4), legend,
           font=f_foot, fill=MUTED)
    foot = data["footer"]
    d.text(((W - d.textlength(foot, font=f_foot)) / 2, fy + 16), foot,
           font=f_foot, fill=MUTED)

    # --- bottom navy bar -----------------------------------------------------
    d.rectangle([15, 984, W - 16, 1004], fill=NAVY)
    f_bar = font(SANS_B, 9)
    d.text((m, 990), "THE WORLD IN ONE DAY", font=f_bar, fill=(255, 255, 255))
    tail = "SUNDAY 22 NOVEMBER 2026  ·  ONE PAGE"
    d.text((W - m - d.textlength(tail, font=f_bar), 990), tail, font=f_bar,
           fill=(255, 255, 255))

    img.save(out_path, "PNG", optimize=True)
    for wmsg in sorted(set(warnings)):
        print("TRUNCATED:", wmsg)
    print("warnings:", len(warnings))
    return out_path


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    render(data, out)
    print("wrote", out, os.path.getsize(out), "bytes")
