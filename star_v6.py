"""A brief ASCII flare around the finished tree topper."""

import math

import numpy as np

from render import CELL_HEIGHT, CELL_WIDTH, CHAR


# Angles are clockwise in screen pixels. Sizes are distances from the star center.
RAYS = (
    (-90, 65, 147, '+', .92),
    (-56, 62, 132, '/', .78),
    (-25, 70, 164, '/', .95),
    (-3,  91, 179, '-', .79),
    (37,  64, 121, '\\', .70),
    (142, 70, 123, '/', .77),
    (183, 92, 175, '-', .86),
    (211, 66, 154, '\\', .89),
    (239, 64, 121, '\\', .76),
)
SPARKS = ((-112, 111), (-70, 122), (-39, 117), (13, 147),
          (151, 118), (197, 147), (227, 119), (257, 128))
ICE = np.array([255, 249, 239], dtype=np.float32)
GOLD = np.array([255, 193, 94], dtype=np.float32)


def _ease(value):
    value = max(0.0, min(value, 1.0))
    return value * value * (3.0 - 2.0 * value)


def star_burst(t, begins, center_x, center_y, color, glyph, strength):
    """Draw the short topper flare into the compositor's cell arrays."""
    elapsed = t - begins
    if not .09 < elapsed < .65:
        return

    rise = _ease((elapsed - .09) / .15)
    fade = 1 - _ease((elapsed - .32) / .33)
    expansion = _ease((elapsed - .09) / .29)
    cool_to_warm = _ease((elapsed - .22) / .25)
    tint = ICE * (1 - cool_to_warm) + GOLD * cool_to_warm
    rows, cols = strength.shape

    def place(theta, distance, char, opacity, ink):
        x = round(center_x + math.cos(theta) * distance / CELL_WIDTH)
        y = round(center_y + math.sin(theta) * distance / CELL_HEIGHT)
        if 0 <= x < cols and 0 <= y < rows and strength[y, x] < min(.59, opacity):
            glyph[y, x] = CHAR[char]
            color[y, x] = ink
            strength[y, x] = opacity

    amplitude = rise * fade
    for degrees, start, finish, char, weight in RAYS:
        angle = math.radians(degrees)
        length = (finish - start) * expansion
        for step in range(0, round(length), 12):
            position = step / max(length, 1.0)
            opacity = amplitude * weight * (1 - .55 * position)
            mark = char if position < .61 else '.'
            place(angle, start + step, mark, opacity, tint)
        if expansion > .20:
            place(angle, start + length + 7, '*', amplitude * weight * .69, tint)

    sparkle = _ease((elapsed - .20) / .16) * (1 - _ease((elapsed - .42) / .23))
    for i, (degrees, distance) in enumerate(SPARKS):
        opacity = sparkle * (.62 if i % 3 == 0 else .46)
        char = '+' if i % 3 == 0 and sparkle > .66 else '.'
        place(math.radians(degrees), distance + 37 * expansion, char, opacity,
              ICE if i % 3 == 0 else GOLD)
