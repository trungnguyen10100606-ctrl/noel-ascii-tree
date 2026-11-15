"""Silent Christmas cut, with one visual reveal at a time."""
import math

import numpy as np

from greeting_v6 import draw_greeting
from render import CHAR, COLS, ROWS, X, Y
from render_v2 import AXIS, clamp, smoothstep
from render_v3 import main
from render_v4 import ReferencePacedRenderer
from star_v6 import star_burst


class StagedFirRenderer(ReferencePacedRenderer):
    pitch_x, pitch_y, font_size, baseline = 9, 15, 14, 11
    canopy_begins, canopy_rise = .61, 4.11
    trunk_begins, trunk_rise = .10, .71
    sleigh_start, sleigh_end = 13.72, 23.58
    sleigh_width, sleigh_ease, sleigh_light = 776, .102, .91
    red_nose = True
    star_start = 12.71

    def __init__(self, source):
        super().__init__(source)
        # Reduce the blue cast in the sky so fir green reads clearly at phone size.
        self.backdrop = (self.backdrop * np.array([.84, .83, .67])).astype(np.uint16)
        tile = np.sin(X*.823 + Y*.961) + .37*np.cos(X*.57 - Y*.741)
        self.open_spaces = smoothstep((tile-.66)/.67)
        for gem in self.tree.gems:
            gem.starts = 8.08 + (gem.starts-9.15)*.68
            gem.color = clamp(gem.color*1.10, 0, 255)
        for item, start in zip(self.gifts, (10.51, 10.82, 11.16, 11.53, 11.91)):
            item.starts = start
        star = self.tree.star
        star.starts = self.star_start
        intensity = np.max(star.color, axis=2, keepdims=True)
        star.color = clamp(.22*star.color + intensity*np.array([.81,.65,.19]) + [15,10,4], 0, 255)
        self._make_spiral()

    def calm_at(self, t):
        return float(.62 + .38*smoothstep((t-11.1)/2.4))

    def color_canopy(self, color):
        r, g, b = color.transpose(2, 0, 1)
        value = np.max(color, axis=2)
        local = .5 + .5*np.sin(X*.136 + Y*.102 + .7)
        # Keep source facets through luminance while reserving distinct hues for later layers.
        light = clamp((.73*value+.20*g+.07*r)/235)
        leaf = np.stack([
            5 + light*(31 + 22*local),
            11 + light*(211 + 26*local),
            10 + light*(52 + 31*(1-local)) + b*.019,
        ], axis=2)
        branch = 1-smoothstep((Y-165)/3.3)
        return (color*(1-branch[...,None]) + leaf*branch[...,None]).astype(np.float32)

    def paint_foliage(self, rgb, alpha, chars, depth, age, color, glyph, strength):
        middle = np.max(rgb, axis=2)
        shadow = 1 - smoothstep((middle-70)/135)
        settled = smoothstep((age-.28)/.46)
        gaps = .70*self.open_spaces * shadow * settled * (1 - smoothstep((Y-162)/6))
        super().paint_foliage(rgb, alpha*(1-gaps), chars, depth, age, color, glyph, strength)
        return alpha*smoothstep((age+.033)/.145), depth

    def _make_spiral(self):
        self.wrap_progress = u = np.linspace(0, 1, 1500, dtype=np.float32)
        row = 155 - 75*u
        theta = math.tau*(2.58*u + .40)
        y = row - 1.35*np.sin(math.tau*5.16*u)**2
        index = np.arange(ROWS)
        radius_for_y = np.convolve(self.tree.half, [1,2,3,4,5,4,3,2,1], mode='same')/25
        radius = 10.0 + np.interp(row, index, radius_for_y)*1.035
        self.wrap_x = np.interp(row, index, self.tree.middle)-AXIS + radius*np.sin(theta)
        self.wrap_z = np.interp(row, index, self.tree.center_z[:,0]) + radius*.85*np.cos(theta)
        self.wrap_y = y.astype(np.float32)
        amber, gold, pale = np.array([244,138,44]), np.array([255,203,95]), np.array([250,241,190])
        shimmer = .5 + .5*np.sin(theta*2 + u*9)
        palette = amber + (gold-amber)*shimmer[:, None]
        light = shimmer[:, None]**6
        self.wrap_palette = (palette*(1-.25*light) + pale*.25*light).astype(np.float32)

    def draw_garland(self, t, angle, opacity, depth, color, glyph, strength, calm):
        u = self.wrap_progress
        progress = clamp((t - 5.05)/2.85)
        if progress <= 0:
            return
        c, s = math.cos(angle), math.sin(angle)
        sx = AXIS + self.wrap_x*c + self.wrap_z*s
        z = self.wrap_z*c - self.wrap_x*s
        sy = self.wrap_y + .046*z
        drawn = smoothstep((progress-u+.007)/.04)
        leading = np.exp(-((u-progress+.025)/.028)**2) * (1-smoothstep((progress-.957)/.043))
        if progress >= 1:
            drawn = np.ones_like(u)
        rolling = (.5+.5*np.sin(u*46 - t*2.10))**6
        alpha = clamp(drawn*(.81+.15*rolling)+.57*leading)
        warm_lights = self.wrap_palette + rolling[:,None]*[5.0,22.0,29.0]
        lights = warm_lights*(1-leading[:,None]) + np.array([255,252,241])*leading[:,None]

        ink = np.zeros((ROWS,COLS), dtype=np.float32)
        foreground = np.zeros((ROWS,COLS,3), dtype=np.float32)
        hot = np.zeros((ROWS,COLS), dtype=np.float32)
        xi, yi = np.floor(sx).astype(int), np.floor(sy).astype(int)
        for dx, dy in ((0,0),(0,1),(1,0),(1,1)):
            x = clamp(xi+dx, 0, COLS-1)
            y = clamp(yi+dy, 0, ROWS-1)
            in_front = smoothstep((z-depth[y,x]+6.9)/8.0)
            occlusion = smoothstep((opacity[y,x]-.17)/.45)
            footprint = clamp(1-abs(sx-x)*.93)*clamp(1-abs(sy-y)*.82)
            weight = alpha*footprint*(1-occlusion*(1-in_front))
            np.add.at(ink, (y,x), weight)
            np.add.at(foreground, (y,x), lights*weight[:,None])
            np.add.at(hot, (y,x), leading*weight)
        marked = ink > .084
        white = hot[marked]/ink[marked] > .48
        color[marked] = foreground[marked]/ink[marked,None]
        base_char = np.where(ink[marked]>.49, CHAR['='], CHAR['-'])
        glints = np.sin(X[marked]*.46+Y[marked]*.27-t*2.1) > .88
        base_char = np.where(glints & (ink[marked]>.64), CHAR['*'], base_char)
        glyph[marked] = np.where(white, CHAR['#'], base_char)
        strength[marked] = clamp(ink[marked]**.86*1.10, .10, 1)

    def gem_reveal(self, p, strength):
        bright = float(smoothstep(p/.16)*(1 - smoothstep((p-.27)/.44)))
        return strength*1.05, bright

    def assemble_cells(self, t, use_sleigh=True):
        color, glyph, strength = super().assemble_cells(t, use_sleigh)
        star_burst(t, self.star_start, self.tree.star.x, self.tree.star.y,
                   color, glyph, strength)
        return color, glyph, strength

    def assemble(self, t, use_sleigh=True):
        frame = super().assemble(t, use_sleigh)
        # Frame the seed closer to the center and settle on the full tree as it rises.
        offset = round(282*(1-smoothstep(t/4.8)))
        if offset:
            frame = np.roll(frame, -offset, axis=0)
        return self.paint_title(frame, t)

    def paint_title(self, frame, t):
        return draw_greeting(frame, t-2.0)


if __name__ == '__main__':
    main(StagedFirRenderer, review_times=[.43, 1.77, 3.54, 5.78, 7.16,
                                         9.63, 12.98, 16.2, 19.3, 24.8],
         crf='18', duration=26)
