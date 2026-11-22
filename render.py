#!/usr/bin/env python3
"""Render the v3 one-page newspaper image (1024x1024 PNG) from stories.json.

v3 follows the winners' design (see DESIGN-STUDY-22.md): the date is the
masthead, a big red numbers strip, a region colour bar, a dark UTC bar,
3 big illustrated stories + 12 small illustrated stories (flat PIL vector
scenes, one accent colour per scene), an ALSO ON list for the rest, a
WHERE IT HAPPENED map with numbered pins, a DATE CHECK box, and a footer
with the tag legend. All 35 v2 stories are kept (same facts, badges and
sources); the COP31 lead is promoted to numbered story 1, so the page
carries 36 numbered items. All text is real, legible type (DejaVu) -- no
generated imagery. The renderer prints a TRUNCATED warning for any
headline/summary that wraps past its line budget; v3 renders with none.

Usage: python3 render.py stories.json news.png
"""
import json
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
    """Antalya at dawn: navy-to-orange sky bands, sun, skyline, sea."""
    d.rectangle([x, y, x + w, y + int(h * 0.38)], fill=(38, 44, 78))
    d.rectangle([x, y + int(h * 0.38), x + w, y + int(h * 0.66)], fill=(214, 106, 59))
    d.rectangle([x, y + int(h * 0.66), x + w, y + int(h * 0.82)], fill=(240, 180, 90))
    cx, cy, r = x + int(w * 0.62), y + int(h * 0.52), int(h * 0.15)
    d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=(250, 214, 140))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 233, 168))
    base = y + int(h * 0.82)
    skyline = [(0, 0.42), (0.10, 0.55), (0.20, 0.34), (0.30, 0.50), (0.40, 0.30),
               (0.50, 0.52), (0.60, 0.38), (0.70, 0.56), (0.80, 0.34), (0.90, 0.48)]
    for fx, fh in skyline:
        bx = x + int(w * fx)
        bw = max(8, int(w * 0.09))
        d.rectangle([bx, base - int(h * fh), bx + bw, base], fill=(28, 28, 34))
        for wy in range(2):
            d.rectangle([bx + 3, base - int(h * fh) + 5 + wy * 9, bx + 6,
                         base - int(h * fh) + 8 + wy * 9], fill=(255, 214, 110))
    d.rectangle([x, base, x + w, y + h], fill=(31, 58, 95))
    d.line([(x + 10, base + 5), (x + w - 40, base + 5)], fill=(150, 190, 220), width=1)
    d.line([(x + 40, base + 11), (x + w - 10, base + 11)], fill=(150, 190, 220), width=1)


def scene_drones(d, x, y, w, h):
    """Kyiv at night: dark sky, stars, lit towers, searchlight, drones."""
    d.rectangle([x, y, x + w, y + h], fill=(16, 22, 44))
    for sx, sy in [(0.08, 0.14), (0.22, 0.08), (0.36, 0.18), (0.52, 0.10),
                   (0.66, 0.16), (0.80, 0.07), (0.92, 0.20), (0.45, 0.26)]:
        d.ellipse([x + int(w * sx) - 1, y + int(h * sy) - 1,
                   x + int(w * sx) + 1, y + int(h * sy) + 1], fill=(255, 255, 255))
    # searchlight beam from a rooftop
    d.polygon([(x + int(w * 0.18), y + h), (x + int(w * 0.30), y + h),
               (x + int(w * 0.62), y + int(h * 0.12))], fill=(96, 96, 78))
    base = y + h
    for fx, fw, fh in [(0.02, 0.16, 0.52), (0.22, 0.13, 0.68), (0.40, 0.17, 0.45),
                       (0.62, 0.14, 0.60), (0.82, 0.15, 0.40)]:
        bx, bw, bh = x + int(w * fx), int(w * fw), int(h * fh)
        d.rectangle([bx, base - bh, bx + bw, base], fill=(38, 38, 54))
        for wy in range(3):
            for wx in range(3):
                if (wx + wy) % 2 == 0:
                    d.rectangle([bx + 4 + wx * 11, base - bh + 5 + wy * 11,
                                 bx + 8 + wx * 11, base - bh + 9 + wy * 11],
                                fill=(255, 214, 110))
    # drones: small X shapes with dotted trails
    for dx, dy, s in [(0.55, 0.22, 7), (0.74, 0.34, 6), (0.88, 0.16, 5)]:
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
        import math
        ex = bx + int(12 * math.cos(math.radians(ang)))
        ey = by + int(12 * math.sin(math.radians(ang)))
        d.line([(bx, by), (ex, ey)], fill=(255, 140, 40), width=2)


def scene_bahrain(d, x, y, w, h):
    """Bahrain at night: radar blocks burning, sea, ship, missile arc."""
    d.rectangle([x, y, x + w, y + h], fill=(18, 26, 52))
    for sx, sy in [(0.10, 0.12), (0.30, 0.08), (0.55, 0.14), (0.75, 0.08), (0.90, 0.18)]:
        d.ellipse([x + int(w * sx) - 1, y + int(h * sy) - 1,
                   x + int(w * sx) + 1, y + int(h * sy) + 1], fill=(255, 255, 255))
    sea = y + int(h * 0.70)
    d.rectangle([x, sea, x + w, y + h], fill=(28, 68, 110))
    # two radar/industrial blocks with flames
    for fx, fw in [(0.08, 0.20), (0.38, 0.20)]:
        bx, bw = x + int(w * fx), int(w * fw)
        d.rectangle([bx, sea - 34, bx + bw, sea], fill=(125, 130, 140))
        d.ellipse([bx + bw // 2 - 10, sea - 46, bx + bw // 2 + 10, sea - 30],
                  fill=(150, 155, 165))
        d.polygon([(bx + bw // 2 - 12, sea - 44), (bx + bw // 2 + 12, sea - 44),
                   (bx + bw // 2, sea - 62)], fill=(255, 140, 40))
        d.polygon([(bx + bw // 2 - 6, sea - 44), (bx + bw // 2 + 6, sea - 44),
                   (bx + bw // 2, sea - 54)], fill=(255, 214, 110))
    # ship on the right
    sx0 = x + int(w * 0.68)
    d.polygon([(sx0, sea + 4), (sx0 + int(w * 0.24), sea + 4),
               (sx0 + int(w * 0.20), sea + 14), (sx0 + 6, sea + 14)], fill=(20, 20, 28))
    d.rectangle([sx0 + 10, sea - 6, sx0 + 34, sea + 4], fill=(150, 60, 50))
    d.rectangle([sx0 + 38, sea - 6, sx0 + 58, sea + 4], fill=(70, 110, 160))
    # dotted missile arc
    for k in range(7):
        t = k / 6.0
        ax = x + int(w * (0.05 + 0.35 * t))
        ay = y + int(h * (0.10 + 0.28 * t * t))
        d.ellipse([ax - 2, ay - 2, ax + 2, ay + 2], fill=(255, 255, 255))


def _small_bg(d, x, y, w, h, color):
    d.rectangle([x, y, x + w, y + h], fill=color)


def scene_ballot(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (233, 227, 204))
    d.rectangle([x + 52, y + 12, x + 100, y + 44], fill=(255, 255, 255), outline=(60, 55, 45), width=2)
    d.rectangle([x + 66, y + 12, x + 86, y + 16], fill=(163, 18, 18))
    d.line([(x + 58, y + 34), (x + 68, y + 42), (x + 92, y + 20)], fill=(46, 125, 50), width=3)
    d.rectangle([x + 12, y + 30, x + 34, y + 44], fill=(255, 255, 255), outline=(60, 55, 45), width=1)


def scene_cricket(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (74, 140, 74))
    d.rectangle([x + 64, y + 4, x + 88, y + 50], fill=(222, 200, 150))
    for wx in range(3):
        d.line([(x + 70 + wx * 5, y + 8), (x + 70 + wx * 5, y + 16)], fill=(255, 255, 255), width=2)
    d.polygon([(x + 100, y + 18), (x + 108, y + 14), (x + 112, y + 30), (x + 104, y + 34)],
              fill=(150, 105, 60))
    d.ellipse([x + 116, y + 30, x + 124, y + 38], fill=(180, 30, 30))
    d.ellipse([x + 20, y + 14, x + 28, y + 22], fill=(255, 255, 255))


def scene_race(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (20, 24, 40))
    for i in range(15):
        d.rectangle([x + i * 11, y, x + (i + 1) * 11, y + 10],
                    fill=(255, 255, 255) if i % 2 == 0 else (20, 20, 20))
    d.rectangle([x + 42, y + 30, x + 112, y + 40], fill=(180, 30, 30))
    d.rectangle([x + 62, y + 22, x + 88, y + 30], fill=(180, 30, 30))
    for wx in (52, 96):
        d.ellipse([x + wx, y + 38, x + wx + 12, y + 50], fill=(10, 10, 10),
                  outline=(180, 180, 180), width=1)
    d.line([(x + 14, y + 34), (x + 34, y + 34)], fill=(255, 220, 130), width=2)
    d.line([(x + 20, y + 42), (x + 36, y + 42)], fill=(255, 220, 130), width=2)


def scene_basket(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (222, 160, 90))
    d.line([(x, y + 40), (x + w, y + 40)], fill=(255, 255, 255), width=2)
    d.ellipse([x + 52, y + 26, x + 100, y + 54], outline=(255, 255, 255), width=2)
    d.ellipse([x + 108, y + 10, x + 132, y + 34], fill=(230, 110, 30),
              outline=(120, 60, 10), width=2)
    d.arc([x + 108, y + 10, x + 132, y + 34], start=200, end=340, fill=(120, 60, 10), width=2)
    d.line([(x + 120, y + 10), (x + 120, y + 34)], fill=(120, 60, 10), width=2)


def scene_ship(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (60, 110, 160))
    d.rectangle([x, y + 34, x + w, y + h], fill=(30, 80, 130))
    d.polygon([(x + 18, y + 26), (x + 136, y + 26), (x + 126, y + 40), (x + 28, y + 40)],
              fill=(20, 20, 28))
    d.rectangle([x + 30, y + 12, x + 52, y + 26], fill=(180, 60, 50))
    d.rectangle([x + 56, y + 12, x + 78, y + 26], fill=(70, 110, 160))
    d.rectangle([x + 82, y + 12, x + 104, y + 26], fill=(150, 150, 140))
    d.polygon([(x + 40, y + 12), (x + 52, y + 12), (x + 46, y - 2)], fill=(255, 140, 40))
    d.polygon([(x + 66, y + 12), (x + 78, y + 12), (x + 72, y - 2)], fill=(255, 214, 110))
    for sx, sy in [(30, 8), (60, 4), (96, 8)]:
        d.ellipse([x + sx, y + sy, x + sx + 14, y + sy + 8], fill=(200, 200, 200))


def scene_powercut(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (28, 28, 44))
    for fx, fw, fh in [(0.05, 0.24, 0.62), (0.35, 0.28, 0.78), (0.70, 0.24, 0.55)]:
        bx, bw, bh = x + int(w * fx), int(w * fw), int(h * fh)
        d.rectangle([bx, y + h - bh, bx + bw, y + h], fill=(48, 48, 64))
        for wy in range(3):
            for wx in range(2):
                lit = (fx == 0.35 and wy == 1 and wx == 0) or (fx == 0.05 and wy == 0 and wx == 1)
                col = (255, 214, 110) if lit else (18, 18, 28)
                d.rectangle([bx + 5 + wx * 14, y + h - bh + 6 + wy * 12,
                             bx + 10 + wx * 14, y + h - bh + 11 + wy * 12], fill=col)
    d.ellipse([x + 128, y + 6, x + 140, y + 18], fill=(240, 230, 200))


def scene_hospital(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (235, 235, 228))
    d.rectangle([x, y + 40, x + w, y + h], fill=(120, 170, 90))
    d.rectangle([x + 40, y + 12, x + 112, y + 40], fill=(255, 255, 255),
                outline=(60, 55, 45), width=2)
    d.rectangle([x + 70, y + 16, x + 78, y + 32], fill=(200, 30, 30))
    d.rectangle([x + 64, y + 22, x + 84, y + 28], fill=(200, 30, 30))
    for wx in (48, 90):
        d.rectangle([x + wx, y + 18, x + wx + 8, y + 26], fill=(120, 170, 200))
    d.line([(x + 12, y + 46), (x + 30, y + 46)], fill=(255, 255, 255), width=1)


def scene_fbi(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (52, 68, 96))
    for r in range(3):
        for c in range(4):
            d.rectangle([x + 10 + c * 13, y + 10 + r * 12, x + 20 + c * 13, y + 19 + r * 12],
                        fill=(160, 180, 210) if (r + c) % 3 else (220, 230, 245))
    d.ellipse([x + 84, y + 8, x + 124, y + 40], outline=(255, 255, 255), width=3)
    d.line([(x + 116, y + 34), (x + 136, y + 48)], fill=(255, 255, 255), width=3)
    d.ellipse([x + 96, y + 18, x + 112, y + 30], fill=(255, 214, 110))


def scene_strike(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (200, 220, 235))
    d.ellipse([x + 40, y + 22, x + 110, y + 34], fill=(70, 75, 85))
    d.polygon([(x + 60, y + 24), (x + 84, y + 10), (x + 92, y + 24)], fill=(70, 75, 85))
    d.polygon([(x + 96, y + 24), (x + 108, y + 12), (x + 112, y + 24)], fill=(70, 75, 85))
    d.line([(x + 14, y + 8), (x + 138, y + 48)], fill=(200, 30, 30), width=3)


def scene_boat(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (70, 120, 170))
    d.rectangle([x, y + 34, x + w, y + h], fill=(30, 80, 130))
    d.arc([x + 8, y + 30, x + 48, y + 46], start=180, end=360, fill=(255, 255, 255), width=2)
    d.arc([x + 96, y + 34, x + 140, y + 50], start=180, end=360, fill=(255, 255, 255), width=2)
    d.polygon([(x + 44, y + 18), (x + 112, y + 28), (x + 100, y + 40), (x + 52, y + 32)],
              fill=(120, 85, 50))
    d.ellipse([x + 66, y + 10, x + 72, y + 16], fill=(40, 40, 40))
    d.ellipse([x + 84, y + 14, x + 90, y + 20], fill=(40, 40, 40))


def scene_fire(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (40, 30, 26))
    d.rectangle([x + 14, y + 26, x + 60, y + h], fill=(70, 70, 78))
    d.rectangle([x + 66, y + 32, x + 112, y + h], fill=(60, 60, 68))
    d.rectangle([x + 116, y + 20, x + 124, y + 40], fill=(70, 70, 78))
    for fx, fw, fh, col in [(0.14, 0.16, 0.42, (255, 90, 20)), (0.30, 0.13, 0.34, (255, 160, 40)),
                            (0.52, 0.15, 0.40, (255, 120, 30)), (0.68, 0.12, 0.30, (255, 200, 80))]:
        bx = x + int(w * fx)
        d.polygon([(bx, y + h - int(h * fh) + 14), (bx + int(w * fw), y + h - int(h * fh) + 14),
                   (bx + int(w * fw) // 2, y + 8)], fill=col)
    d.ellipse([x + 118, y + 4, x + 134, y + 14], fill=(180, 180, 180))


def scene_pope(d, x, y, w, h):
    _small_bg(d, x, y, w, h, (238, 228, 200))
    d.rectangle([x, y + 42, x + w, y + h], fill=(150, 140, 110))
    d.pieslice([x + 52, y + 6, x + 100, y + 44], start=180, end=360, fill=(200, 160, 80))
    d.rectangle([x + 72, y + 2, x + 80, y + 12], fill=(200, 160, 80))
    d.line([(x + 76, y - 2), (x + 76, y + 4)], fill=(120, 100, 60), width=2)
    for cx in (30, 44, 118, 132):
        d.rectangle([x + cx, y + 30, x + cx + 8, y + 42], fill=(220, 205, 160))
    for i in range(9):
        d.ellipse([x + 12 + i * 15, y + 46, x + 18 + i * 15, y + 52], fill=(60, 55, 45))


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
