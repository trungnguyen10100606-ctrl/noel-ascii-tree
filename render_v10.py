# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow", "imageio-ffmpeg"]
# ///
"""v8 scene untouched (sky, garland, star, greeting); fir and baubles get a light pixel-glitch tint."""
import numpy as np

import render_v7
from render import X, Y
from render_v2 import clamp, smoothstep
from render_v3 import main
from render_v8 import CodeGreetingRenderer

# Swatches from the reference: yellow, cyan, magenta, orange, pink.
SWATCH = np.array([[255,214,40],[40,214,255],[255,60,200],[255,138,28],[255,100,170]], dtype=np.float32)
PATCH_SHARE = .30     # fraction of 5x3-cell blocks that get a tint
PATCH_MIX = .55       # how far a tinted block moves toward the swatch

# Baubles: keep scarlet / gold / cobalt, swap two for crystal cyan and pink.
render_v7.HOLIDAY_COLORS[:] = np.array([[248,48,54],[250,177,46],[57,126,249],
                                        [120,226,255],[255,140,214]], dtype=np.float32)


def block_hash(a, b, salt):
    return np.abs(np.sin(a*127.1 + b*311.7 + salt*74.7)*43758.5453) % 1.0


class SoftGlitchRenderer(CodeGreetingRenderer):
    def color_canopy(self, color):
        green = super().color_canopy(color)
        bx, by = np.floor(X/5.0), np.floor(Y/3.0)
        painted = block_hash(bx, by, 1) > 1-PATCH_SHARE
        bar = (block_hash(np.floor(Y/2.0), 0, 3) > .90) & (block_hash(np.floor(X/12.0), np.floor(Y/2.0), 4) > .5)
        swatch = SWATCH[np.floor(block_hash(bx, by, 2)*len(SWATCH)).astype(int)]
        luma = np.max(green, axis=2, keepdims=True)/255
        tint = swatch*(.45 + .75*luma)
        amount = np.where(painted | bar, PATCH_MIX, 0)[...,None]
        # Only the fir itself, not the trunk base or ground, to keep the silhouette recognisable.
        amount = amount*(1-smoothstep((Y-165)/3.3))[...,None]
        return (green*(1-amount) + tint*amount).astype(np.float32)


if __name__ == '__main__':
    main(SoftGlitchRenderer, review_times=[8.5, 10.7, 13.08, 15.5, 17.2, 19.8, 22.1, 23.19, 24.22, 25.7],
         crf='18', duration=26)
