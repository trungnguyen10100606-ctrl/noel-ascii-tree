# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow"]
# ///
"""Generate assets/tree-source.png: an original 1200x2000 pixel-block tree on a blue sky.

The renderer only needs this picture for the tree's shape and rough colours, so it is drawn
procedurally here instead of shipping someone else's artwork.
    uv run tools/make_source.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from render import CANOPY, GEMS, GROUND_STREAK, ORBIT_LOW, ORBIT_TOP, STAR_OUTLINE, TRUNK  # noqa: E402

W, H = 1200, 2000
rng = np.random.default_rng(2026)

# Sky: electric blue that brightens toward the ground.
y = np.arange(H, dtype=np.float32)[:, None]
g = np.interp(y, [0, 500, 900, 1250, 1550, 1850], [74, 79, 85, 104, 135, 165])
b = np.interp(y, [0, 750, 1200, 1600, 1950], [241, 246, 249, 251, 246])
r = np.interp(y, [0, 1000, 2000], [18, 22, 30])
sky = np.stack(np.broadcast_arrays(r, g, b), axis=-1)
sky = np.broadcast_to(sky, (H, W, 3)).copy()
image = Image.fromarray(sky.astype(np.uint8))

# Tree body: dark teal pixel blocks, some painted yellow / red / orange / cyan / magenta.
PAINT = np.array([[250, 205, 40], [235, 55, 50], [250, 140, 30], [40, 210, 250],
                  [245, 50, 185], [90, 225, 120]], dtype=np.float32)
mask = Image.new('L', (W, H))
d = ImageDraw.Draw(mask)
d.polygon(CANOPY, fill=255)
d.polygon(TRUNK, fill=255)
d.line([(606, 286), (605, 337)], fill=255, width=22)
mask = np.asarray(mask) > 0
BLOCK = 26
blocks = Image.new('RGB', (W, H))
bp = ImageDraw.Draw(blocks)
for by in range(0, H, BLOCK):
    for bx in range(0, W, BLOCK):
        if rng.random() < .30:
            c = PAINT[rng.integers(len(PAINT))] * rng.uniform(.75, 1.05)
        else:
            c = np.array([8, 40, 58]) + rng.uniform(0, 1)*np.array([10, 45, 40])
        bp.rectangle([bx, by, bx+BLOCK-1, by+BLOCK-1], fill=tuple(int(v) for v in np.clip(c, 0, 255)))
# Thin horizontal "code" bars for texture.
for _ in range(260):
    by, bx = int(rng.integers(300, 1900)), int(rng.integers(100, 1100))
    bp.rectangle([bx, by, bx+int(rng.integers(60, 240)), by+int(rng.integers(5, 9))],
                 fill=tuple(int(v) for v in PAINT[rng.integers(len(PAINT))]*.9))
image.paste(blocks, (0, 0), Image.fromarray((mask*255).astype(np.uint8)))

paint = ImageDraw.Draw(image)

# Ground streaks and glowing rings.
paint.line(GROUND_STREAK, fill=(120, 215, 255), width=8, joint='curve')
glow = Image.new('RGB', (W, H))
gp = ImageDraw.Draw(glow)
for pts in (ORBIT_TOP, ORBIT_LOW):
    gp.line(pts, fill=(255, 150, 225), width=26, joint='curve')
glow = glow.filter(ImageFilter.GaussianBlur(10))
image = Image.fromarray(np.clip(np.asarray(image, dtype=np.float32) + np.asarray(glow)*.45, 0, 255).astype(np.uint8))
paint = ImageDraw.Draw(image)
for pts in (ORBIT_TOP, ORBIT_LOW):
    paint.line(pts, fill=(255, 245, 255), width=8, joint='curve')

# Crystal diamonds.
plume = [(0, -1), (.72, -.44), (1, .21), (.58, .63), (0, 1), (-.64, .62), (-1, .20), (-.60, -.42)]
for i, (cx, cy, rx, ry) in enumerate(GEMS):
    tint = [(150, 240, 255), (255, 175, 235), (200, 180, 255), (170, 255, 225)][i % 4]
    pts = [(cx+dx*rx, cy+dy*ry) for dx, dy in plume]
    paint.polygon(pts, fill=tint)
    paint.polygon([(cx, cy-ry), (cx+.72*rx, cy-.44*ry), (cx, cy+.1*ry), (cx-.6*rx, cy-.42*ry)],
                  fill=(255, 255, 255))
    paint.line(pts + [pts[0]], fill=(235, 250, 255), width=3)

# Star.
paint.polygon(STAR_OUTLINE, fill=(235, 248, 255), outline=(255, 255, 255))
paint.polygon([(601, 160), (625, 200), (606, 235), (585, 205)], fill=(255, 190, 240))

out = Path(__file__).resolve().parent.parent / 'assets' / 'tree-source.png'
image.save(out)
print('wrote', out)
