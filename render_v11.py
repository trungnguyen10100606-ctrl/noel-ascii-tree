# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""Vivid, Reels-safe cut with large, crisp glyphs.

The tree is laid out to sit between Instagram's top bar and caption area. Instead of shrinking
the finished picture (which blurs the text), the scene is zoomed while it is sampled into the
character grid, so every glyph keeps the same large size.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_v3
import render_v10 as base
from greeting_v8 import paint_code_greeting
from render import COLS, FONT_BOLD, HEIGHT, ROWS, WIDTH
from render_v2 import clamp, smoothstep
from render_v3 import main

render_v3.FONT = FONT_BOLD            # heavier glyphs read brighter at phone size

# Tuning knobs -------------------------------------------------------------
GLYPH_W, GLYPH_H = 9, 15   # glyph cell in pixels (1080/9 = 120 columns); bigger = chunkier code
GLYPH_FONT, GLYPH_BASE = 14, 11
SCENE_SCALE = .80          # tree layout size (glyphs stay the same size)
STAR_Y = 520               # where the tree's star lands, below the greeting
TITLE_SCALE = .75          # greeting size
TITLE_Y = 262              # greeting top; Reels' top bar covers roughly y < 250
GAIN = .62                # colour intensity
SATURATION = .30           # extra colour punch on lit glyphs
GLOW = .26                 # bloom strength

base.PATCH_SHARE = .15
base.PATCH_MIX = .60
base.SWATCH = np.array([[255,222,30],[40,225,255],[255,50,200],[255,130,20],
                        [255,60,60]], dtype=np.float32)

SRC_STAR_X, SRC_STAR_Y = 540, 419   # tree star in the unzoomed 1080x1920 scene


def sparkle_field():
    rng = np.random.default_rng(77)
    pts = []
    for _ in range(190):
        pts.append((rng.uniform(10, WIDTH-10), rng.uniform(20, HEIGHT-20), rng.uniform(0, math.tau),
                    rng.choice(['+', '*', '+', '·']), rng.uniform(1.4, 3.2),
                    [(255,255,255), (255,240,170), (170,235,255), (255,190,235)][int(rng.integers(4))]))
    return pts


class VividSafeRenderer(base.SoftGlitchRenderer):
    pitch_x, pitch_y, font_size, baseline = GLYPH_W, GLYPH_H, GLYPH_FONT, GLYPH_BASE

    def __init__(self, source):
        super().__init__(source)
        self.thin_gems()
        self.zoom_lookup()
        self.sparkles = sparkle_field()
        self.sparkle_font = ImageFont.truetype(FONT_BOLD, 20)

    def zoom_lookup(self):
        """Re-map screen glyph cells onto the scene so the tree lands at SCENE_SCALE / STAR_Y."""
        grid_cols, grid_rows = WIDTH//self.pitch_x, HEIGHT//self.pitch_y
        sx = (np.arange(grid_cols, dtype=np.float32)+.5)*self.pitch_x
        sy = (np.arange(grid_rows, dtype=np.float32)+.5)*self.pitch_y
        src_x = SRC_STAR_X + (sx-SRC_STAR_X)/SCENE_SCALE
        src_y = SRC_STAR_Y + (sy-STAR_Y)/SCENE_SCALE
        tx, ty = src_x/6-.5, src_y/10-.5          # 6x10 px scene cells
        # Fade the scene out toward its border so nothing pops in at the edge.
        fx = smoothstep(np.minimum(tx+.5, COLS-.5-tx)/9)
        fy = smoothstep(np.minimum(ty+.5, ROWS-.5-ty)/9)
        self.fade = (fy[:, None]*fx[None, :]).astype(np.float32)
        bx = np.clip(np.floor(tx).astype(int), 0, COLS-2)
        by = np.clip(np.floor(ty).astype(int), 0, ROWS-2)
        wx, wy = np.clip(tx-bx, 0, 1), np.clip(ty-by, 0, 1)
        self.lookup_x = np.stack(np.broadcast_arrays(bx[None, :], (bx+1)[None, :], bx[None, :], (bx+1)[None, :]))
        self.lookup_y = np.stack(np.broadcast_arrays(by[:, None], by[:, None], (by+1)[:, None], (by+1)[:, None]))
        self.mix = np.stack([(1-wy[:, None])*(1-wx[None, :]), (1-wy[:, None])*wx[None, :],
                             wy[:, None]*(1-wx[None, :]), wy[:, None]*wx[None, :]]).astype(np.float32)

    def read_cells(self, color, glyph, strength, calm=0.0):
        rgb, char, coverage = super().read_cells(color, glyph, strength, calm)
        return rgb, char, coverage*self.fade

    def thin_gems(self):
        """Keep every other crystal/bauble group (a front piece plus its rear twin)."""
        groups = []
        for gem in self.tree.gems:
            if not gem.rear or not groups:
                groups.append([gem])
            else:
                groups[-1].append(gem)
        self.tree.gems = [gem for i, group in enumerate(groups) if i % 2 == 0 for gem in group]

    def paint_title(self, frame, t):
        return frame           # greeting is placed separately

    @staticmethod
    def punch(frame):
        f = frame.astype(np.float32)
        peak = f.max(axis=2, keepdims=True)
        lit = clamp((peak-26)/70)
        mean = f.mean(axis=2, keepdims=True)
        f = mean + (f-mean)*(1+SATURATION*lit)
        f = f*(1+.75*lit*GAIN)
        return np.clip(f, 0, 255)

    def sparkle_layer(self, t):
        layer = Image.new('RGB', (WIDTH, HEIGHT))
        paint = ImageDraw.Draw(layer)
        for x, y, phase, char, rate, color in self.sparkles:
            k = .25+.75*(.5+.5*math.sin(t*rate+phase))**2
            paint.text((x, y), char, fill=tuple(int(c*k) for c in color), font=self.sparkle_font, anchor='mm')
        return np.asarray(layer, dtype=np.float32)

    def assemble(self, t, use_sleigh=True):
        frame = super().assemble(t, use_sleigh).astype(np.float32)
        frame = self.punch(frame)
        # Twinkles only where the scene is dark, so they never muddy the tree.
        frame += self.sparkle_layer(t)*(1-clamp(frame.max(axis=2, keepdims=True)/110))
        if t >= 22.55:
            strip = np.zeros((360, WIDTH, 3), dtype=np.uint8)
            paint_code_greeting(strip, t)
            title = Image.fromarray(strip[38:353, 141:939]).resize(
                (round(798*TITLE_SCALE), round(315*TITLE_SCALE)), Image.Resampling.LANCZOS)
            title = self.punch(np.asarray(title))
            tx = (WIDTH-title.shape[1])//2
            frame[TITLE_Y:TITLE_Y+title.shape[0], tx:tx+title.shape[1]] += title
        bright = np.clip((frame-110)*1.6, 0, 255).astype(np.uint8)
        halo = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(7))
        frame = frame + np.asarray(halo, dtype=np.float32)*GLOW
        return np.clip(frame, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    main(VividSafeRenderer, review_times=[8.5, 10.7, 13.08, 15.5, 17.2, 19.8, 22.1, 23.19, 24.22, 25.7],
         crf='16', duration=26)
