"""Round Christmas ornaments with continuous rotation and steady illumination."""
from dataclasses import dataclass
import math

import numpy as np

from render import CELL_HEIGHT, CELL_WIDTH, CHAR, COLS, ROWS, X, Y
from render_v2 import AXIS, clamp, smoothstep
from render_v3 import main
from render_v6 import StagedFirRenderer

HOLIDAY_COLORS = np.array([
    [248, 48, 54],    # Scarlet
    [250, 177, 46],   # Gold
    [57, 126, 249],   # Cobalt
    [222, 43, 66],    # Cranberry
    [144, 174, 218],  # Cool silver
], dtype=np.float32)


@dataclass(frozen=True)
class Ornament:
    x: float
    z: float
    y: float
    offset_x: float
    offset_z: float
    orbit: float
    diameter: float
    starts: float
    hue: int

    def project(self, c, s):
        front = (self.z-self.offset_z)*c - (self.x-self.offset_x)*s
        facing = smoothstep((front/self.orbit + .19)/.35)
        depth = self.z*c-self.x*s
        return AXIS+self.x*c+self.z*s, self.y+depth*.028, depth, facing


class ColoredOrnamentRenderer(StagedFirRenderer):
    def __init__(self, source):
        super().__init__(source)
        self.ornaments = self.make_ornaments()

    def make_ornaments(self):
        rng = np.random.default_rng(8019)
        rows = (68, 82, 95, 108, 122, 136, 150, 160)
        counts = (3, 4, 5, 6, 7, 8, 9, 10)
        sizes = (37, 40, 43, 47, 49, 51, 54, 53)
        smooth_profile = np.convolve(self.tree.half, [1,2,3,4,3,2,1], mode='same')/16
        lamps = []
        for tier, (row, count, size) in enumerate(zip(rows, counts, sizes)):
            for slot in range(count):
                phase = math.tau*(slot/count + (tier*.367)%1) + rng.uniform(-.12, .12)
                y = row+rng.uniform(-2.25, 2.25)
                i = round(y)
                center_x = self.tree.middle[i]-AXIS
                center_z = self.tree.center_z[i,0]
                radius = smooth_profile[i]*.94+3.9
                ratio = self.tree.ratio[i,0]
                x = center_x+radius*math.sin(phase)
                z = center_z+radius*ratio*math.cos(phase)
                starts = 8.05 + .265*tier + rng.uniform(0, .39)
                hue = (slot+(2*tier)+slot//4)%len(HOLIDAY_COLORS)
                lamps.append(Ornament(x, z, y, center_x, center_z, radius, size+rng.uniform(-3.8,5), starts, hue))
        return lamps

    def draw_ornaments(self, t, angle, effective_alpha, depth, color, glyph, strength, calm):
        if t < 8.05:
            return
        c, s = math.cos(angle), math.sin(angle)
        visible = []
        for bulb in self.ornaments:
            x, y, near, facing = bulb.project(c, s)
            born = smoothstep((t-bulb.starts)/.46)
            opacity = facing*born
            if opacity > .006:
                visible.append((near, x, y, bulb, born, opacity))
        # Paint distant spheres first, so one ball can pass smoothly in front of another.
        for _, x, y, bulb, born, opacity in sorted(visible, key=lambda item: item[0]):
            diameter = bulb.diameter*(.80+.20*born)
            stamp_round_ball(x, y, diameter, HOLIDAY_COLORS[bulb.hue], opacity, color, glyph, strength)


def stamp_round_ball(x, y, diameter, base, opacity, color, glyph, strength):
    radius = diameter*.5
    margin_x = radius/CELL_WIDTH+1.3
    margin_y = radius/CELL_HEIGHT+1.7
    x0, x1 = max(0, math.floor(x-margin_x)), min(COLS, math.ceil(x+margin_x+1))
    y0, y1 = max(0, math.floor(y-margin_y)), min(ROWS, math.ceil(y+margin_y+1))
    region = np.s_[y0:y1, x0:x1]
    dx = (X[region]-x)*CELL_WIDTH
    dy = (Y[region]-y)*CELL_HEIGHT
    xx, yy = dx/radius, dy/radius
    distance = np.sqrt(xx*xx+yy*yy)
    sphere = np.sqrt(clamp(1-distance**2))
    coverage = smoothstep((1.09-distance)/.26)
    lamp = clamp(.62*sphere - .39*xx - .46*yy)
    sheen = np.exp(-((xx+.29)**2 + (yy+.33)**2)*15)
    body = base*(.50+.59*lamp)[...,None]
    body = clamp(body + sheen[...,None]*np.array([70, 83, 86]), 0, 255)
    ink = np.where(distance>.80, CHAR['o'], CHAR['0'])
    ink = np.where(sheen > .51, CHAR['@'], ink)

    # A small brass cap makes the spheres read as hanging ornaments.
    cap = clamp((radius*.35+2.0-abs(dx))/5.5) * clamp((5.3-abs(dy+radius+2.8))/4.8)
    metal = (cap > coverage) & (cap > .05)
    body[metal] = [225, 174, 76]
    ink[metal] = CHAR['+']
    a = np.maximum(coverage, cap*.83)*opacity
    layer = a[...,None]
    color[region] = color[region]*(1-layer) + body*layer
    strength[region] = strength[region]*(1-a) + a
    use_ornament = a > .22
    glyph[region][use_ornament] = ink[use_ornament]


if __name__ == '__main__':
    main(ColoredOrnamentRenderer,
         review_times=[8.5, 9.4, 10.7, 11.8, 13.08, 14.8, 17.2, 19.8, 22.1, 24.7],
         crf='18', duration=26)
