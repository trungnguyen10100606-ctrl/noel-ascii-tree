"""Draw a two-line greeting built from printable ASCII glyphs."""
from functools import lru_cache
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from render import FONT_BOLD

LETTER_ROWS = {
    "M": ("10001","11011","10101","10101","10001","10001","10001"),
    "E": ("11111","10000","10000","11110","10000","10000","11111"),
    "R": ("11110","10001","10001","11110","10100","10010","10001"),
    "Y": ("10001","10001","01010","00100","00100","00100","00100"),
    "C": ("01111","10000","10000","10000","10000","10000","01111"),
    "H": ("10001","10001","10001","11111","10001","10001","10001"),
    "I": ("11111","00100","00100","00100","00100","00100","11111"),
    "S": ("01111","10000","10000","01110","00001","00001","11110"),
    "T": ("11111","00100","00100","00100","00100","00100","00100"),
    "A": ("01110","10001","10001","11111","10001","10001","10001"),
}

TILE_WIDTH, TILE_HEIGHT = 14, 16
PATCH_TOP = 38
PATCH_WIDTH, PATCH_HEIGHT = 798, 315
ACTIVE = "#0X%&@"
SCANNING = "#0X%&@{}+<>:"
CHAMPAGNE = np.array([255,209,115], dtype=np.float32)
AMBER = np.array([250,165,62], dtype=np.float32)
LIGHT = np.array([255,250,219], dtype=np.float32)
ICE = np.array([113,238,210], dtype=np.float32)
BLOOM_COLOR = np.array([85,47,12], dtype=np.float32)


def easing(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


@lru_cache(maxsize=1)
def glyph_layout():
    cells = []
    font = ImageFont.truetype(FONT_BOLD, 21)
    for line, (text, y0, beat) in enumerate((
        ("MERRY", 46, 22.72),
        ("CHRISTMAS", 180, 22.99),
    )):
        width = (len(text)*6-1)*TILE_WIDTH
        x0 = (PATCH_WIDTH-width)//2
        for letter, spelling in enumerate(text):
            for row, bits in enumerate(LETTER_ROWS[spelling]):
                for col, on in enumerate(bits):
                    if on == "0":
                        continue
                    index = letter*6+col
                    hash_id = (index*67+row*151+line*29) % 997
                    starts = beat + .0105*index + .016*row + (hash_id%19)*.0029
                    x = x0+index*TILE_WIDTH+1
                    y = y0+row*TILE_HEIGHT+13
                    char = ACTIVE[(hash_id+row+index//3)%len(ACTIVE)]
                    gold = CHAMPAGNE*(.71-.017*row) + AMBER*(.29+.017*row)
                    cells.append((x, y, starts, hash_id, char, gold))
    return font, cells


def paint_code_greeting(frame, time):
    if time < 22.55:
        return frame

    font, layout = glyph_layout()
    ink = Image.new("RGBA", (PATCH_WIDTH, PATCH_HEIGHT))
    painter = ImageDraw.Draw(ink)
    ticks = int(time*24)
    ray = ((time-24.00)/1.16)*(PATCH_WIDTH+200)-100
    for x, y, start, key, final, gold in layout:
        age = time-start
        if age < -.16:
            continue
        land = easing((age+.13)/.36)
        strength = easing((age+.15)/.22)
        set_ink = easing((age-.018)/.28)
        glyph = final if age >= .27 else SCANNING[(key+ticks+int(y/16))%len(SCANNING)]
        y_display = y - round(24*(1-land))
        hit = .96*math.exp(-.5*((x+(y-145)*.28-ray)/48)**2)
        current = gold*(1-hit)+LIGHT*hit
        current = current*set_ink+ICE*(1-set_ink)
        painter.text((x,y_display), glyph, fill=(*map(int, current), round(strength*247)),
                     font=font, anchor="ls")
        if -.065 < age < .14 and key%5==0:
            trail = .35*(1-easing((age+.065)/.20))
            painter.text((x,y_display-15), ":", fill=(59,158,133,round(255*trail)),
                         font=font, anchor="ls")

    layer = np.asarray(ink, dtype=np.float32)
    alpha = layer[...,3:4]/255
    glow = np.asarray(ink.getchannel("A").filter(ImageFilter.GaussianBlur(3.3)), dtype=np.float32)/255
    x0 = (frame.shape[1]-PATCH_WIDTH)//2
    y0 = PATCH_TOP
    dst = frame[y0:y0+PATCH_HEIGHT, x0:x0+PATCH_WIDTH]
    backdrop = dst.astype(np.float32)+glow[...,None]*BLOOM_COLOR
    dst[:] = np.clip(backdrop*(1-alpha)+layer[...,:3]*alpha, 0, 255).astype(np.uint8)
    return frame
