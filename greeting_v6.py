"""Warm gold monospaced greeting for the final seconds of the ASCII video."""

from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


GREETING = "MERRY CHRISTMAS"
APPEAR = 20.70
TYPE_INTERVAL = 0.092
Y_CENTER = 268
PADDING = 26
from render import FONT_BOLD as FONT_PATH


@lru_cache(maxsize=1)
def _layout():
    font = ImageFont.truetype(FONT_PATH, 58)
    glyph_advance = round(font.getlength("M"))
    spacing = glyph_advance + 5
    height = 104
    width = (len(GREETING) - 1) * spacing + glyph_advance + 2 * PADDING
    mask = Image.new("L", (width, height))
    painter = ImageDraw.Draw(mask)
    for i, letter in enumerate(GREETING):
        painter.text((PADDING + i * spacing, 73), letter, anchor="ls", font=font, fill=255)
    x = np.arange(width, dtype=np.float32)
    column_letter = np.clip(((x - PADDING) // spacing).astype(int), 0, len(GREETING) - 1)
    return np.asarray(mask), x, column_letter


def draw_greeting(frame: np.ndarray, t: float) -> np.ndarray:
    """Type in the greeting and sweep a soft highlight along its letters."""
    if t < APPEAR:
        return frame

    mask, x, column_letter = _layout()
    height, width = mask.shape
    age = t - APPEAR - column_letter * TYPE_INTERVAL
    reveal = np.clip(age / 0.14, 0, 1)
    reveal = reveal * reveal * (3 - 2 * reveal)
    coverage = np.rint(mask * reveal).astype(np.uint8)

    shimmer_x = ((t - 21.96) / 1.30) * (width + 144) - 72
    sweep = np.exp(-0.5 * ((x - shimmer_x) / 64) ** 2)
    flicker = np.sin(x * 0.029 - t * 3.1) * 0.025
    shine = np.clip(0.05 + 0.81 * sweep + flicker, 0, 1)
    gold = np.array([255, 202, 114], dtype=np.float32)
    highlight = np.array([255, 247, 212], dtype=np.float32)
    text_color = gold + (highlight - gold) * shine[:, None]

    glow_image = Image.fromarray(coverage).filter(ImageFilter.GaussianBlur(6))
    glow_strength = np.asarray(glow_image, dtype=np.float32) / 255
    bloom = glow_strength[..., None] * np.array([116, 65, 19], dtype=np.float32)
    alpha = coverage[..., None].astype(np.float32) / 255

    x0 = (frame.shape[1] - width) // 2
    y0 = Y_CENTER - height // 2
    result = frame if frame.flags.writeable else frame.copy()
    region = result[y0:y0 + height, x0:x0 + width]
    composed = (region.astype(np.float32) + bloom) * (1 - alpha) + text_color[None] * alpha
    region[:] = np.clip(composed, 0, 255).astype(np.uint8)
    return result
