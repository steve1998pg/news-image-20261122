#!/usr/bin/env python3
"""Render a one-page dense newspaper image (1024x1024 PNG) from stories.json.

Usage: python3 render.py stories21.json news-20261121.png
Layout: masthead + lead banner + UTC strip + flowing multi-column region
layout (regions balanced across columns by story count) + footer.
All text is real, legible type (DejaVu) -- no generated imagery.
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


def measure_story(draw, st, f_head, f_sum, col_w, hl_lh, sm_lh):
    hl = wrap(draw, st["headline"], f_head, col_w)[:2]
    sm = wrap(draw, st["summary"], f_sum, col_w)[:2]
    return len(hl) * hl_lh + len(sm) * sm_lh + 5, hl, sm


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
                 f"{data['region_count']} REGIONS  •  ALL STORIES DATED {data['date_label'].split(',')[-1].strip()}")
    d.text(((W - d.textlength(date_line, font=f_date)) / 2, y), date_line, font=f_date, fill=INK)
    y += 22
    d.line([(m, y), (W - m, y)], fill=RULE, width=2)
    y += 10

    # lead banner
    lead = data["lead"]
    f_lead_h = font(SERIF_B, 27)
    f_lead_s = font(SANS, 14)
    lead_w = W - 2 * m - 18
    lh_lines = wrap(d, lead["headline"], f_lead_h, lead_w)
    ls_lines = wrap(d, lead["summary"], f_lead_s, lead_w)
    lead_h = len(lh_lines) * 33 + len(ls_lines) * 18 + 12
    d.rectangle([m, y, W - m, y + lead_h], fill=(243, 236, 216), outline=RED, width=1)
    d.rectangle([m, y, m + 6, y + lead_h], fill=RED)
    ly = y + 6
    ly = draw_wrapped(d, m + 14, ly, lh_lines, f_lead_h, INK, 33)
    ly = draw_wrapped(d, m + 14, ly + 2, ls_lines, f_lead_s, MUTED, 18)
    y += lead_h + 8

    # UTC strip (auto-fit font so it never overflows)
    utc = ("UTC 00:00   •   LONDON 00:00   •   PARIS 01:00   •   CAIRO 02:00   •   MOSCOW 03:00   •   "
           "DUBAI 04:00   •   DELHI 05:30   •   BEIJING 08:00   •   TOKYO 09:00   •   SYDNEY 11:00")
    utc_size = 11
    while utc_size > 8 and d.textlength(utc, font=font(SANS, utc_size)) > W - 2 * m:
        utc_size -= 0.5
    f_utc = font(SANS, int(utc_size))
    d.text(((W - d.textlength(utc, font=f_utc)) / 2, y), utc, font=f_utc, fill=MUTED)
    y += 18
    d.line([(m, y), (W - m, y)], fill=LIGHT, width=1)
    y += 8

    # flowing column layout: balance regions across columns by story count
    cols = data.get("cols", 3)
    regions = data["regions"]
    col_w = (W - 2 * m - (cols - 1) * 16) // cols
    grid_top = y
    grid_bottom = H - 44
    avail = grid_bottom - grid_top

    # greedy balance: biggest regions first, into shortest column
    order = sorted(range(len(regions)), key=lambda i: -len(regions[i]["stories"]))
    col_assign = [[] for _ in range(cols)]
    col_counts = [0] * cols
    for i in order:
        c = col_counts.index(min(col_counts))
        col_assign[c].append(i)
        col_counts[c] += len(regions[i]["stories"])
    for c in range(cols):
        col_assign[c].sort()

    # auto-fit type sizes so the tallest column fits
    for head_size, sum_size in [(13, 11), (12.5, 10.5), (12, 10), (11.5, 10), (11, 9.5)]:
        f_head = font(SERIF_B, head_size)
        f_sum = font(SANS, sum_size)
        hl_lh = int(head_size * 1.22)
        sm_lh = int(sum_size * 1.25)
        heights = []
        for c in range(cols):
            h = 0
            for i in col_assign[c]:
                h += 24  # region header
                for st in regions[i]["stories"]:
                    hh, _, _ = measure_story(d, st, f_head, f_sum, col_w, hl_lh, sm_lh)
                    h += hh
                h += 6  # gap after region
            heights.append(h)
        if max(heights) <= avail:
            break
    print(f"cols={cols} type head={head_size} sum={sum_size} col_heights={heights} avail={avail}")

    f_reg = font(SANS_B, 13)
    col_end = []
    for c in range(cols):
        x0 = m + c * (col_w + 16)
        sy = grid_top
        for i in col_assign[c]:
            region = regions[i]
            d.text((x0, sy), region["name"], font=f_reg, fill=RED)
            d.line([(x0, sy + 18), (x0 + col_w, sy + 18)], fill=RED, width=1)
            sy += 24
            for st in region["stories"]:
                _, hl, sm = measure_story(d, st, f_head, f_sum, col_w, hl_lh, sm_lh)
                sy = draw_wrapped(d, x0, sy, hl, f_head, INK, hl_lh)
                sy = draw_wrapped(d, x0, sy, sm, f_sum, MUTED, sm_lh)
                sy += 5
            sy += 6
        col_end.append(sy)
        if c < cols - 1:
            d.line([(x0 + col_w + 8, grid_top), (x0 + col_w + 8, grid_bottom)], fill=LIGHT, width=1)

    # fact box fills the shortest column (if any)
    if data.get("factbox"):
        c = col_end.index(min(col_end))
        x0 = m + c * (col_w + 16)
        sy = col_end[c] + 4
        fb = data["factbox"]
        d.text((x0, sy), fb["title"], font=f_reg, fill=RED)
        d.line([(x0, sy + 18), (x0 + col_w, sy + 18)], fill=RED, width=1)
        sy += 26
        f_num = font(SERIF_B, 20)
        f_lab = font(SANS, 10.5)
        for num, lab in fb["items"]:
            d.text((x0, sy), num, font=f_num, fill=INK)
            lab_lines = wrap(d, lab, f_lab, col_w - 92)
            ly = sy + 2
            ly = draw_wrapped(d, x0 + 92, ly, lab_lines, f_lab, MUTED, 13)
            sy = max(sy + 30, ly + 4)

    # footer
    fy = H - 34
    d.line([(m, fy), (W - m, fy)], fill=RULE, width=1)
    f_foot = font(SANS, 10)
    foot = ("Sources: Reuters, AP, AFP, Al Jazeera, UKMTO  •  Every story dated "
            f"{data['date_label'].split(',')[-1].strip()}  •  Compiled by an AI picture editor")
    d.text(((W - d.textlength(foot, font=f_foot)) / 2, fy + 6), foot, font=f_foot, fill=MUTED)

    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    render(data, out)
    print("wrote", out, os.path.getsize(out), "bytes")
