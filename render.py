#!/usr/bin/env python3
"""Render a one-page dense newspaper image (1024x1024 PNG) from stories.json.

v2: numbered stories with CONFIRMED/OFFICIAL/REPORTED/CLAIM/FORECAST badges
+ per-story source, THE DAY IN NUMBERS strip, labelled UTC strip, DATE CHECK
box, drawn lead illustration (Antalya at dawn) and a WHERE IT HAPPENED world
map with numbered pins in the shortest column. All text is real, legible
type (DejaVu) -- no generated imagery. Summaries/headlines are kept short so
nothing is ever cut mid-sentence: the renderer prints a TRUNCATED warning for
any story whose headline or summary wraps past 2 lines.

Usage: python3 render.py stories22.json news-20261122-v2.png
"""
import json
import sys
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
BG = (248, 244, 232)
INK = (17, 17, 17)
RED = (163, 18, 18)
MUTED = (90, 84, 70)
RULE = (60, 55, 45)
LIGHT = (226, 219, 198)
MAP_LAND = (206, 214, 196)
MAP_LINE = (120, 118, 108)

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


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


# Rough continent outlines (lon, lat) for the WHERE IT HAPPENED map.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 66), (-75, 62), (-65, 60), (-55, 52), (-60, 47), (-70, 44), (-75, 40), (-80, 32), (-85, 30), (-90, 21), (-95, 19), (-100, 16), (-105, 20), (-110, 23), (-115, 30), (-125, 40), (-125, 49), (-135, 58), (-150, 60), (-165, 60)],
    [(-80, 10), (-75, 7), (-65, 5), (-55, 5), (-50, 0), (-40, -5), (-35, -10), (-40, -20), (-48, -28), (-55, -35), (-65, -45), (-70, -55), (-73, -40), (-72, -20), (-78, -5)],
    [(-10, 36), (-5, 44), (0, 50), (5, 55), (10, 58), (18, 56), (20, 60), (25, 65), (30, 70), (35, 68), (40, 60), (30, 55), (25, 50), (20, 45), (15, 44), (10, 38), (0, 36)],
    [(-10, 35), (0, 36), (10, 37), (20, 32), (30, 31), (35, 28), (40, 20), (48, 11), (51, 10), (45, 0), (40, -10), (35, -20), (30, -30), (20, -35), (15, -28), (12, -18), (10, -5), (5, 5), (-5, 5), (-10, 15), (-15, 25)],
    [(35, 68), (50, 70), (70, 72), (100, 75), (130, 72), (160, 70), (178, 65), (170, 60), (160, 55), (140, 50), (135, 45), (130, 35), (125, 30), (120, 25), (110, 20), (105, 10), (100, 8), (95, 15), (90, 22), (85, 20), (80, 10), (75, 8), (70, 25), (60, 25), (55, 28), (50, 30), (45, 35), (40, 38)],
    [(113, -22), (120, -15), (130, -12), (135, -15), (140, -17), (145, -15), (150, -22), (153, -28), (150, -37), (145, -38), (140, -38), (135, -35), (130, -32), (125, -32), (120, -35), (115, -33), (113, -25)],
]


def draw_sunrise(d, x0, y0, w, h):
    """Small drawn dawn scene: sky bands, sun, skyline, sea. Labelled."""
    # sky bands
    d.rectangle([x0, y0, x0 + w, y0 + int(h * 0.38)], fill=(38, 44, 78))
    d.rectangle([x0, y0 + int(h * 0.38), x0 + w, y0 + int(h * 0.66)], fill=(214, 106, 59))
    d.rectangle([x0, y0 + int(h * 0.66), x0 + w, y0 + int(h * 0.82)], fill=(240, 180, 90))
    # sun + halo
    cx, cy, r = x0 + int(w * 0.62), y0 + int(h * 0.52), int(h * 0.16)
    d.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=(250, 214, 140))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 233, 168))
    # skyline
    base = y0 + int(h * 0.82)
    skyline = [(0, 0.42), (0.10, 0.55), (0.20, 0.34), (0.30, 0.50), (0.40, 0.30),
               (0.50, 0.52), (0.60, 0.38), (0.70, 0.56), (0.80, 0.34), (0.90, 0.48)]
    for fx, fh in skyline:
        bx = x0 + int(w * fx)
        bw = max(6, int(w * 0.09))
        d.rectangle([bx, base - int(h * fh), bx + bw, base], fill=(28, 28, 34))
        for wy in range(2):
            d.rectangle([bx + 2, base - int(h * fh) + 4 + wy * 8, bx + 5,
                         base - int(h * fh) + 7 + wy * 8], fill=(255, 214, 110))
    # sea
    d.rectangle([x0, base, x0 + w, y0 + h], fill=(31, 58, 95))
    d.line([(x0 + 8, base + 5), (x0 + w - 30, base + 5)], fill=(150, 190, 220), width=1)
    d.line([(x0 + 30, base + 10), (x0 + w - 8, base + 10)], fill=(150, 190, 220), width=1)
    d.text((x0 + 6, y0 + h - 13), "ANTALYA AT DAWN", font=font(SANS_B, 8), fill=(255, 255, 255))


def story_texts(num, st):
    head = f"{num}. {st['headline']} [{st.get('badge', 'REPORTED')}]"
    summ = f"{st['summary']} ({st.get('source', '')})"
    return head, summ


def measure_story(draw, num, st, f_head, f_sum, col_w, hl_lh, sm_lh):
    head, summ = story_texts(num, st)
    hl = wrap(draw, head, f_head, col_w)
    sm = wrap(draw, summ, f_sum, col_w)
    trunc = len(hl) > 2 or len(sm) > 2
    return len(hl[:2]) * hl_lh + len(sm[:2]) * sm_lh + 4, hl[:2], sm[:2], trunc


def render(data, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    m = 26
    d.rectangle([10, 10, W - 11, H - 11], outline=RULE, width=2)
    d.rectangle([15, 15, W - 16, H - 16], outline=RULE, width=1)

    y = 24
    f_kick = font(SANS_B, 12)
    kick = "THE DAILY PICTURE  •  WORLD NEWS IN ONE IMAGE"
    d.text(((W - d.textlength(kick, font=f_kick)) / 2, y), kick, font=f_kick, fill=RED)
    y += 20
    f_mast = font(SERIF_B, 52)
    title = "THE WORLD IN ONE DAY"
    d.text(((W - d.textlength(title, font=f_mast)) / 2, y), title, font=f_mast, fill=INK)
    y += 64
    d.line([(m, y), (W - m, y)], fill=RULE, width=2)
    y += 6
    f_date = font(SANS_B, 14)
    date_line = (f"{data['date_label']}  •  {data['story_count']} STORIES  •  "
                 f"{data['region_count']} REGIONS  •  ALL STORIES DATED 22 NOVEMBER 2026")
    d.text(((W - d.textlength(date_line, font=f_date)) / 2, y), date_line, font=f_date, fill=INK)
    y += 22
    d.line([(m, y), (W - m, y)], fill=RULE, width=2)
    y += 10

    # lead banner + drawn dawn illustration on the right
    lead = data["lead"]
    ILL_W = 190
    f_lead_h = font(SERIF_B, 27)
    f_lead_s = font(SANS, 14)
    lead_w = W - 2 * m - 18 - ILL_W - 12
    lh_lines = wrap(d, lead["headline"], f_lead_h, lead_w)
    ls_lines = wrap(d, lead["summary"], f_lead_s, lead_w)
    lead_h = len(lh_lines) * 33 + len(ls_lines) * 18 + 12
    d.rectangle([m, y, W - m, y + lead_h], fill=(243, 236, 216), outline=RED, width=1)
    d.rectangle([m, y, m + 6, y + lead_h], fill=RED)
    ly = y + 6
    ly = draw_wrapped(d, m + 14, ly, lh_lines, f_lead_h, INK, 33)
    ly = draw_wrapped(d, m + 14, ly + 2, ls_lines, f_lead_s, MUTED, 18)
    draw_sunrise(d, W - m - ILL_W, y, ILL_W, lead_h)
    y += lead_h + 8

    # UTC strip, labelled events
    utc = data.get("utc_strip", "")
    utc_size = 11
    while utc_size > 8 and d.textlength(utc, font=font(SANS, utc_size)) > W - 2 * m:
        utc_size -= 0.5
    f_utc = font(SANS, int(utc_size))
    d.text(((W - d.textlength(utc, font=f_utc)) / 2, y), utc, font=f_utc, fill=MUTED)
    y += 18
    d.line([(m, y), (W - m, y)], fill=LIGHT, width=1)
    y += 8

    # THE DAY IN NUMBERS strip
    nums = data.get("numbers", {}).get("items", [])
    if nums:
        nb_h = 40
        d.rectangle([m, y, W - m, y + nb_h], outline=RULE, width=1)
        f_nb_t = font(SANS_B, 9)
        d.text((m + 8, y + 4), "THE DAY IN NUMBERS", font=f_nb_t, fill=RED)
        cell_w = (W - 2 * m - 150) // len(nums)
        f_num = font(SERIF_B, 18)
        f_lab = font(SANS, 8.5)
        for i, (num, lab) in enumerate(nums):
            cx = m + 150 + i * cell_w + cell_w // 2
            if i:
                d.line([(m + 150 + i * cell_w, y + 6), (m + 150 + i * cell_w, y + nb_h - 6)],
                       fill=LIGHT, width=1)
            d.text((cx - d.textlength(num, font=f_num) / 2, y + 4), num, font=f_num, fill=INK)
            lab_lines = wrap(d, lab, f_lab, cell_w - 8)
            ly = y + 26
            for ln in lab_lines[:1]:
                d.text((cx - d.textlength(ln, font=f_lab) / 2, ly), ln, font=f_lab, fill=MUTED)
                ly += 11
        y += nb_h + 8

    # DATE CHECK box height (computed now, drawn after the grid)
    dc = data.get("date_check", "")
    f_dc_t = font(SANS_B, 11)
    f_dc = font(SANS, 10)
    dc_lines = wrap(d, dc, f_dc, W - 2 * m - 130)
    dc_h = 14 + len(dc_lines) * 12 + 10

    # flowing column layout: balance regions across columns by story count
    cols = data.get("cols", 4)
    regions = data["regions"]
    col_w = (W - 2 * m - (cols - 1) * 16) // cols
    grid_top = y
    grid_bottom = H - 42 - 8 - dc_h - 8
    avail = grid_bottom - grid_top

    order = sorted(range(len(regions)), key=lambda i: -len(regions[i]["stories"]))
    col_assign = [[] for _ in range(cols)]
    col_counts = [0] * cols
    for i in order:
        c = col_counts.index(min(col_counts))
        col_assign[c].append(i)
        col_counts[c] += len(regions[i]["stories"])
    for c in range(cols):
        col_assign[c].sort()

    # story numbers in reading order (left column first, top to bottom)
    numbers = {}
    pins = []
    n = 0
    for c in range(cols):
        for i in col_assign[c]:
            for si, st in enumerate(regions[i]["stories"]):
                n += 1
                numbers[(i, si)] = n
                if st.get("pin"):
                    pins.append((n, st["pin"][0], st["pin"][1]))
    print(f"total stories numbered: {n}")

    # auto-fit type sizes so the tallest column fits
    trunc_warnings = []
    for head_size, sum_size in [(12, 10), (11.5, 10), (11, 9.5), (10.5, 9)]:
        f_head = font(SERIF_B, head_size)
        f_sum = font(SANS, sum_size)
        hl_lh = int(head_size * 1.22)
        sm_lh = int(sum_size * 1.25)
        heights = []
        trunc_warnings = []
        for c in range(cols):
            h = 0
            for i in col_assign[c]:
                h += 20  # region header
                for si, st in enumerate(regions[i]["stories"]):
                    hh, _, _, trunc = measure_story(d, numbers[(i, si)], st,
                                                     f_head, f_sum, col_w, hl_lh, sm_lh)
                    if trunc:
                        trunc_warnings.append(f"story {numbers[(i, si)]}: {st['headline']}")
                    h += hh
                h += 6  # gap after region
            heights.append(h)
        if max(heights) <= avail:
            break
    print(f"cols={cols} type head={head_size} sum={sum_size} col_heights={heights} avail={avail}")
    for wmsg in sorted(set(trunc_warnings)):
        print("TRUNCATED:", wmsg)

    f_reg = font(SANS_B, 13)
    col_end = []
    for c in range(cols):
        x0 = m + c * (col_w + 16)
        sy = grid_top
        for i in col_assign[c]:
            region = regions[i]
            d.text((x0, sy), region["name"], font=f_reg, fill=RED)
            d.line([(x0, sy + 16), (x0 + col_w, sy + 16)], fill=RED, width=1)
            sy += 20
            for si, st in enumerate(region["stories"]):
                _, hl, sm, _ = measure_story(d, numbers[(i, si)], st,
                                              f_head, f_sum, col_w, hl_lh, sm_lh)
                sy = draw_wrapped(d, x0, sy, hl, f_head, INK, hl_lh)
                sy = draw_wrapped(d, x0, sy, sm, f_sum, MUTED, sm_lh)
                sy += 4
            sy += 6
        col_end.append(sy)
        if c < cols - 1:
            d.line([(x0 + col_w + 8, grid_top), (x0 + col_w + 8, grid_bottom)], fill=LIGHT, width=1)

    # WHERE IT HAPPENED map in the shortest column, if room
    c = col_end.index(min(col_end))
    free = grid_bottom - col_end[c]
    if free >= 130 and pins:
        x0 = m + c * (col_w + 16)
        sy = col_end[c] + 4
        d.text((x0, sy), "WHERE IT HAPPENED", font=f_reg, fill=RED)
        d.line([(x0, sy + 18), (x0 + col_w, sy + 18)], fill=RED, width=1)
        sy += 24
        map_h = min(free - 30, 170)
        map_w = col_w
        d.rectangle([x0, sy, x0 + map_w, sy + map_h], fill=(238, 238, 226), outline=MAP_LINE, width=1)

        def proj(lon, lat):
            return (x0 + (lon + 180) / 360.0 * map_w,
                    sy + (90 - lat) / 150.0 * map_h)

        for poly in CONTINENTS:
            pts = [proj(lon, lat) for lon, lat in poly]
            d.polygon(pts, fill=MAP_LAND, outline=MAP_LINE)
        f_pin = font(SANS_B, 8)
        for num, lon, lat in pins:
            px, py = proj(lon, lat)
            px = min(max(px, x0 + 7), x0 + map_w - 7)
            py = min(max(py, sy + 7), sy + map_h - 7)
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=RED, outline=(255, 255, 255), width=1)
            lbl = str(num)
            d.text((px - d.textlength(lbl, font=f_pin) / 2, py - 5), lbl,
                   font=f_pin, fill=(255, 255, 255))
        d.text((x0, sy + map_h + 4), "Pins match story numbers.",
               font=font(SANS, 9), fill=MUTED)

    # DATE CHECK box
    dy = grid_bottom + 8
    d.rectangle([m, dy, W - m, dy + dc_h], outline=RED, width=1)
    d.text((m + 8, dy + 5), "DATE CHECK", font=f_dc_t, fill=RED)
    draw_wrapped(d, m + 118, dy + 5, dc_lines, f_dc, INK, 12)

    # footer: tags legend + sources
    fy = H - 42
    d.line([(m, fy), (W - m, fy)], fill=RULE, width=1)
    f_foot = font(SANS, 9.5)
    legend = ("TAGS — CONFIRMED 2+ outlets  •  OFFICIAL attributed, not verified  •  "
              "REPORTED one source  •  CLAIM one side's account  •  FORECAST still to happen")
    d.text(((W - d.textlength(legend, font=f_foot)) / 2, fy + 4), legend,
           font=f_foot, fill=MUTED)
    foot = ("Sources: Reuters, BBC, Al Jazeera, AP, AFP, SCMP, FIA, ESPN, Detiknews, Vatican News, "
            "EMSC, IANS, Guardian, Anadolu  •  Scenes drawn in code, not photographs")
    d.text(((W - d.textlength(foot, font=f_foot)) / 2, fy + 16), foot,
           font=f_foot, fill=MUTED)

    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    render(data, out)
    print("wrote", out, os.path.getsize(out), "bytes")
