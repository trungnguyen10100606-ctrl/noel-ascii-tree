# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Vivid, Reels-safe cut: saturated glyph colours, glow, and a layout that keeps the tree and
greeting clear of Instagram's top bar, caption area and right-hand buttons."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_v3
import render_v10 as base
from greeting_v8 import paint_code_greeting
from render import FONT_BOLD, HEIGHT, WIDTH
from render_v2 import clamp, smoothstep
from render_v3 import main

render_v3.FONT = FONT_BOLD            # heavier glyphs read brighter at phone size

# Tuning knobs -------------------------------------------------------------
SCENE_SCALE = .68        # size of the whole scene inside the 1080x1920 frame
STAR_Y = 545             # where the tree's star lands (below the greeting)
TITLE_SCALE = .72        # greeting size
TITLE_Y = 285            # greeting top; Reels' top bar covers roughly y < 250
GAIN = 1.0               # colour intensity
SATURATION = .55         # extra colour punch on lit glyphs
GLOW = .42               # bloom strength

base.PATCH_SHARE = .52
base.PATCH_MIX = .82
base.SWATCH = np.array([[255,222,30],[40,225,255],[255,50,200],[255,130,20],
                        [255,60,60],[150,255,60],[255,255,255]], dtype=np.float32)

# Original scene geometry (tree star top at y=419 in the 1920px frame).
SRC_STAR_Y = 419


def sparkle_field():
    rng = np.random.default_rng(77)
    pts = []
    for _ in range(190):
        pts.append((rng.uniform(10, WIDTH-10), rng.uniform(20, HEIGHT-20), rng.uniform(0, math.tau),
                    rng.choice(['+', '*', '.', '+', '·']), rng.uniform(1.4, 3.2),
                    [(255,255,255), (255,240,170), (170,235,255), (255,190,235)][int(rng.integers(4))]))
    return pts


def feather(width, height, margin):
    ramp_x = smoothstep(np.minimum(np.arange(width), np.arange(width)[::-1])/margin)
    ramp_y = smoothstep(np.minimum(np.arange(height), np.arange(height)[::-1])/margin)
    return (ramp_y[:, None]*ramp_x[None, :])[..., None].astype(np.float32)


class VividSafeRenderer(base.SoftGlitchRenderer):
    def __init__(self, source):
        super().__init__(source)
        self.sparkles = sparkle_field()
        self.sparkle_font = ImageFont.truetype(FONT_BOLD, 20)
        self.scene_w, self.scene_h = round(WIDTH*SCENE_SCALE), round(HEIGHT*SCENE_SCALE)
        self.scene_x = (WIDTH-self.scene_w)//2
        self.scene_y = round(STAR_Y - SRC_STAR_Y*SCENE_SCALE)
        self.scene_mask = feather(self.scene_w, self.scene_h, 46)

    def paint_title(self, frame, t):
        return frame           # greeting is placed separately, after the scene is scaled

    @staticmethod
    def punch(frame):
        f = frame.astype(np.float32)
        peak = f.max(axis=2, keepdims=True)
        lit = clamp((peak-26)/70)
        mean = f.mean(axis=2, keepdims=True)
        f = mean + (f-mean)*(1+SATURATION*lit)
        f = f*(1+.75*lit*GAIN)
        return np.clip(f, 0, 255)

    def sky(self, t):
        sky = Image.fromarray(self.backdrop.astype(np.uint8))
        paint = ImageDraw.Draw(sky)
        for x, y, phase, char, rate, color in self.sparkles:
            tw = (.5+.5*math.sin(t*rate+phase))**2
            k = .25+.75*tw
            paint.text((x, y), char, fill=tuple(int(c*k) for c in color), font=self.sparkle_font, anchor='mm')
        return np.asarray(sky, dtype=np.float32)

    def assemble(self, t, use_sleigh=True):
        raw = super().assemble(t, use_sleigh).astype(np.float32)
        offset = round(282*(1-smoothstep(t/4.8)))
        sky_under = np.roll(self.backdrop.astype(np.float32), -offset, axis=0) if offset else self.backdrop.astype(np.float32)
        # Keep only what the scene drew on top of its own sky, so no rectangle shows around it.
        scene = self.punch(np.clip(raw - sky_under, 0, 255))
        small = Image.fromarray(scene.astype(np.uint8)).resize((self.scene_w, self.scene_h), Image.Resampling.LANCZOS)
        canvas = self.sky(t)
        x, y, w, h = self.scene_x, self.scene_y, self.scene_w, self.scene_h
        y0, y1 = max(y, 0), min(y+h, HEIGHT)
        piece = np.asarray(small, dtype=np.float32)[y0-y:y1-y]
        mask = self.scene_mask[y0-y:y1-y]
        canvas[y0:y1, x:x+w] += piece*mask
        if t >= 22.55:
            strip = np.zeros((360, WIDTH, 3), dtype=np.uint8)
            paint_code_greeting(strip, t)
            title = Image.fromarray(strip[38:353, 141:939]).resize(
                (round(798*TITLE_SCALE), round(315*TITLE_SCALE)), Image.Resampling.LANCZOS)
            title = self.punch(np.asarray(title))
            tx = (WIDTH-title.shape[1])//2
            canvas[TITLE_Y:TITLE_Y+title.shape[0], tx:tx+title.shape[1]] += title
        # Bloom on the brightest pixels makes the colours glow.
        bright = np.clip((canvas-110)*1.6, 0, 255).astype(np.uint8)
        halo = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(7))
        canvas = canvas + np.asarray(halo, dtype=np.float32)*GLOW
        return np.clip(canvas, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    main(VividSafeRenderer, review_times=[8.5, 10.7, 13.08, 15.5, 17.2, 19.8, 22.1, 23.19, 24.22, 25.7],
         crf='18', duration=26)
