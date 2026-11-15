from __future__ import annotations

import argparse
import math
import subprocess
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ground_gifts import draw_ground_gifts
from render import (
    CANOPY, TRUNK, GEMS, ORBIT_TOP, ORBIT_LOW, STAR_OUTLINE, GROUND_STREAK,
    WIDTH, HEIGHT, COLS, ROWS, CELL_WIDTH, CELL_HEIGHT, FPS,
    SOURCE_HEIGHT, LEFT, TOP, SCALE, X, Y, CHAR,
    choose_glyphs, make_atlas, mask_from_shapes, smoothstep, to_grid, composite_cells,
)
from sleigh import draw_sleigh

DURATION = 24
AXIS = (LEFT + 601 * SCALE) / CELL_WIDTH - .5
TURN_START, TURN_END = 15.15, 22.45
SLEIGH_START, SLEIGH_END = 7.0, 21.65
RNG = np.random.default_rng(1527)


def clamp(value, lower=0, upper=1):
    return np.clip(value, lower, upper)


def coord(x, y):
    return ((LEFT + x * SCALE) / CELL_WIDTH - .5,
            (TOP + y * SCALE) / CELL_HEIGHT - .5)


def grid_mask(mask):
    return to_grid(Image.fromarray(np.round(255 * clamp(mask)).astype(np.uint8))).astype(np.float32)/255


def grid_layer(rgb, mask, gamma=.78):
    opacity = grid_mask(mask)
    prem = to_grid(Image.fromarray(np.round(rgb * mask[..., None]).astype(np.uint8)))
    scaled = clamp(prem / np.maximum(opacity[..., None], .06) / 255)
    color = 255*scaled**gamma + (1-scaled)*(7 + 8*np.max(scaled, axis=2, keepdims=True))
    return color.astype(np.float32), opacity


def interpolate_removed(color, opacity, removal, silhouette):
    clean = color.copy()
    for y in range(ROWS):
        available = np.flatnonzero((silhouette[y] > .42) & (opacity[y] > .26) & (removal[y] <= .32))
        x = np.flatnonzero(removal[y] > .13)
        if len(available) == 0 or len(x) == 0:
            continue
        for channel in range(3):
            sampled = np.interp(x, available, color[y, available, channel])
            blend = smoothstep((removal[y, x]-.13)/.56)
            clean[y, x, channel] += (sampled-clean[y, x, channel]) * blend
    return clean


@dataclass
class Sticker:
    color: np.ndarray
    alpha: np.ndarray
    glyph: np.ndarray
    x: float
    y: float
    starts: float
    rear: bool = False


def sprite_sticker(rgb, alpha, x, y, starts, rear=False):
    return Sticker(rgb, alpha, choose_glyphs(rgb, 996), x, y, starts, rear)


def slice_sticker(rgb, alpha, x, y, starts, rear=False):
    rows, cols = np.nonzero(alpha > .10)
    if not len(cols):
        return None
    x0, x1, y0, y1 = cols.min(), cols.max()+1, rows.min(), rows.max()+1
    crop = np.s_[y0:y1, x0:x1]
    return sprite_sticker(rgb[crop], alpha[crop], x, y, starts, rear)


def bauble(color, diameter, x, y, time, rear=False):
    w, h = math.ceil(diameter/CELL_WIDTH) + 2, math.ceil(diameter/CELL_HEIGHT) + 2
    iy, ix = np.indices((h, w), dtype=np.float32)
    xx = (ix - (w-1)*.5)*CELL_WIDTH/(diameter*.5)
    yy = (iy - (h-1)*.5)*CELL_HEIGHT/(diameter*.5)
    rad = np.sqrt(xx*xx + yy*yy)
    shine = .51 + .42*clamp(1-rad) + .29*clamp(-.6*xx - .55*yy)
    specular = np.exp(-((xx+.34)**2+(yy+.37)**2)*14)*.85
    rgb = np.asarray(color)[None, None, :] * shine[...,None] + specular[...,None]*110
    opacity = smoothstep((1.16-rad)/.31)
    rgb[0, w//2] = (241, 216, 123)
    opacity[0, w//2] = .67
    return sprite_sticker(clamp(rgb, 0, 255), opacity, x, y, time, rear)


class Tree:
    def __init__(self, source_path):
        source = Image.open(source_path).convert('RGB').crop((0, 0, 1200, SOURCE_HEIGHT))
        rgb = np.asarray(source, dtype=np.float32)
        r, g, b = rgb.transpose(2, 0, 1)
        ref_y = np.arange(SOURCE_HEIGHT, dtype=np.float32)[:, None]
        field_g = np.interp(ref_y, [0, 500, 900, 1250, 1550, 1850], [74, 79, 85, 104, 135, 165])
        field_b = np.interp(ref_y, [0, 750, 1200, 1600, 1950], [241, 246, 249, 251, 246])
        field_delta = np.maximum.reduce([r*.8, np.abs(g-field_g)*1.24, np.abs(b-field_b)*1.3])
        distinct = smoothstep((field_delta - 21) / 27)
        contrast = np.maximum(smoothstep((r-106)/48), smoothstep((g-field_g-65)/64))
        surface = np.asarray(mask_from_shapes(source.size, [CANOPY, TRUNK],
                                              [([(606, 286), (605, 337)], 20)]))/255
        canopy = surface * np.where(b > 208, np.maximum(distinct, np.where(r > 35, .60, 0)), 1)
        ring_candidates = np.asarray(mask_from_shapes(source.size, lines=[
            (ORBIT_TOP, 45), (ORBIT_LOW, 59),
        ]))/255
        removal = grid_mask(ring_candidates * contrast)
        self.front_rgb, self.front_alpha = grid_layer(rgb, canopy)
        front_extent = grid_mask(surface)
        self.floor_rgb, self.floor_alpha = grid_layer(
            rgb, np.asarray(mask_from_shapes(source.size, lines=[(GROUND_STREAK, 69)]))/255
            * distinct * np.maximum(smoothstep((r-59)/115), .34*smoothstep((field_g-g-14)/72)),
        )
        self.floor_glyph = choose_glyphs(self.floor_rgb, 655, tree=True)
        self.gems = []
        for i, (cx, cy, rx, ry) in enumerate(GEMS):
            bounds = max(0, cx-rx-4), cy-ry-4, min(1200, cx+rx+5), cy+ry+5
            x0, y0, x1, y1 = bounds
            diamond_mask = Image.new('L', (x1-x0, y1-y0))
            painter = ImageDraw.Draw(diamond_mask)
            plume = [(0, -1), (.72, -.44), (1, .21), (.58, .63),
                     (0, 1), (-.64, .62), (-1, .20), (-.60, -.42)]
            painter.polygon([(cx-x0+dx*rx, cy-y0+dy*ry) for dx,dy in plume], fill=255)
            inspection = np.s_[y0:y1, x0:x1]
            raw = np.zeros((SOURCE_HEIGHT, 1200), dtype=np.float32)
            raw[inspection] = np.asarray(diamond_mask)/255 * np.maximum(
                distinct[inspection], contrast[inspection],
            )
            color, alpha = grid_layer(rgb, raw, .73)
            removal = np.maximum(removal, alpha*.95)
            x, y = coord(cx, cy)
            start = 9.15 + i*.192 + (i%3)*.095
            sticker = slice_sticker(color, alpha, x, y, start)
            if sticker is None:
                continue
            self.gems.append(sticker)
            if i%2 == 0:
                tint = sticker.color[..., [2, 0, 1]]*.26 + sticker.color*.74
                self.gems.append(sprite_sticker(tint*.93, sticker.alpha, x + math.sin(i)*7, y+.9,
                                                start, rear=True))
        baubles = [(449,790,34,(255,63,147)), (640,903,42,(45,231,247)),
                   (542,1130,43,(243,167,49)), (864,1170,32,(246,81,177)),
                   (321,1450,38,(63,231,210)), (905,1529,45,(253,117,77)),
                   (590,634,32,(255,107,118)), (500,1575,37,(118,161,255))]
        for i, (x, y, size, color) in enumerate(baubles):
            a, b = coord(x, y)
            self.gems.append(bauble(color, size, a, b, 9.8+i*.432))
            self.gems.append(bauble(color[::-1], size - 2, 2*AXIS-a+.9, b-1.3, 9.8+i*.432, rear=True))
        raw_star = np.asarray(mask_from_shapes(source.size, [STAR_OUTLINE]))/255
        star_color, star_mask = grid_layer(rgb, raw_star*np.maximum(distinct, contrast), .76)
        self.star = slice_sticker(star_color, star_mask, *coord(606, 232), 13.65)
        self.front_rgb = interpolate_removed(self.front_rgb, self.front_alpha, removal, front_extent)
        self.front_alpha = np.maximum(self.front_alpha, front_extent*clamp(removal*1.28)*.93)
        self.front_glyph = choose_glyphs(self.front_rgb, 158, tree=True)

        self.middle = np.full(ROWS, AXIS, dtype=np.float32)
        self.half = np.ones(ROWS, dtype=np.float32)
        for row in range(ROWS):
            xs = np.flatnonzero(front_extent[row] > .40)
            if len(xs):
                self.middle[row], self.half[row] = (xs[-1]+xs[0])*.5, (xs[-1]-xs[0])*.5+.51
        self.vary = np.sin(Y*.143+1.2) * np.minimum(self.half[:, None]*.077, 4.4)
        self.ratio = (.82 + .065*np.sin(Y*.17))[:, :1]
        self.center_z = self.vary[:, :1]
        self.left_start = self.middle[:, None] - AXIS
        self.half_col = self.half[:, None]
        self.ring_sections = [
            (AXIS+10.0, 101, 57.5, 5.15, -.9, 5.77, 1.47, 2.3),
            (AXIS-.5, 140.5, 80, 7.1, 4.6, 7.13, 1.82, .33),
        ]
        self.ring_theta = np.linspace(0, math.tau, 650, endpoint=False, dtype=np.float32)

    def surface_at(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        xpivot = AXIS + self.left_start*c + self.center_z*s
        zpivot = self.center_z*c - self.left_start*s
        apparent = np.sqrt(c*c + self.ratio**2*s*s)
        view_x = (X - xpivot) / np.maximum(self.half_col*apparent, .3)
        shift = np.arctan2(self.ratio*s, c)
        theta = np.arcsin(clamp(view_x, -1, 1)) - shift
        theta_cos = np.cos(theta)
        front_z = zpivot + self.half_col*(self.ratio*theta_cos*c - np.sin(theta)*s)
        if abs(s) < 1e-5 and c > 0:
            return self.front_rgb, self.front_alpha, self.front_glyph, front_z

        backside = smoothstep((-theta_cos-.02)/.76)
        texture_x = clamp(np.sin(theta) + backside*(.23*np.sin(Y*.095) + .13*np.sin(Y*.32)), -1, 1)
        sample_x = clamp(self.middle[:, None] + texture_x*self.half_col, 0, COLS-1.001)
        x0 = sample_x.astype(np.int32)
        y0 = np.arange(ROWS)[:, None]
        part = sample_x - x0
        alpha0, alpha1 = self.front_alpha[y0, x0], self.front_alpha[y0, x0+1]
        within = clamp((1-np.abs(view_x))*self.half_col*apparent+.49)
        opacity = within * (alpha0*(1-part) + alpha1*part)
        rgb = self.front_rgb[y0, x0] * (1-part[...,None]) + self.front_rgb[y0,x0+1]*part[...,None]
        rgb = rgb * (1-backside[...,None]*.19) + rgb[..., [2, 0, 1]]*(backside[...,None]*.21)
        longitudinal = np.cos(theta+.48)*c
        light = (.84 + .16*np.sqrt(clamp(1-view_x**2)) + .055*longitudinal)
        rgb = rgb*(1 + (light[...,None]-1)*clamp(abs(s)*2.1+(1-c)*.5))
        glyphs = self.front_glyph[y0, x0 + (part > .5)]
        return rgb, opacity, glyphs, front_z

    def draw_ring(self, section, t, angle, canopy, depth, color, glyph, strength, calm=0.0):
        cx, cy, radius, dip, tilt, start, build, lead = section
        progress = clamp((t - start) / build)
        if progress <= 0:
            return
        theta = self.ring_theta + lead
        phi = theta + angle
        sx = cx + radius*np.cos(phi)
        stable_tilt = (1-calm)*np.cos(theta) + calm*.47*np.cos(phi)
        sy = cy + dip*np.sin(phi) + tilt*stable_tilt
        rz = radius*.81*np.sin(phi) + 4.5
        order = self.ring_theta/math.tau
        tail = .60 + .40*np.cos(theta*2.9+.4) ** 2
        switched = smoothstep((progress-order+.006)/.045)
        pulse = np.exp(-((order-progress+.025)/.052)**2)*(progress < .996)
        running = .5 + .5*np.sin(theta*2.0 - 3*t)
        opacity = switched * (.74 + .17*tail + .09*running) + pulse*.40
        cyan_to_pink = .5 + .5*np.sin(theta*2 + .42*t)
        cyan = np.array([54, 223, 255])
        pink = np.array([255, 39, 162])
        spectrum = cyan + (pink-cyan)*cyan_to_pink[:, None]
        white = pulse*1.38 + .19*running**8 + .46*(.5+.5*np.cos(theta*4-.4))**5
        spectrum = spectrum*(1-clamp(white[:,None])) + [251, 251, 255]*clamp(white[:,None])
        energy = np.zeros((ROWS, COLS), dtype=np.float32)
        tint = np.zeros((ROWS, COLS, 3), dtype=np.float32)
        xi, yi = np.floor(sx).astype(int), np.floor(sy).astype(int)
        for dx, dy in ((0,0), (1,0), (0,1), (1,1)):
            h, k = clamp(xi+dx, 0, COLS-1), clamp(yi+dy, 0, ROWS-1)
            exposed = smoothstep((rz-depth[k,h]+2.2)/4.4)
            visible = np.where(canopy[k,h] > .39, exposed, 1)
            val = clamp(1-np.abs(sx-h)) * clamp(1-np.abs(sy-k)*.83) * opacity * visible
            np.add.at(energy, (k,h), val)
            np.add.at(tint, (k,h), spectrum*val[:,None])
        valid = energy > .08
        color[valid] = tint[valid]/energy[valid,None]
        value = np.max(color[valid], axis=1)
        white_head = (np.min(color[valid], axis=1) >= 223) & (progress < .997)
        running_pos = .5+.5*np.sin(X[valid]*.23 + Y[valid]*.34 - t*4.7)
        ring_chars = np.where(energy[valid] >= .65, CHAR['='], CHAR['-'])
        ring_chars = np.where((running_pos>.79) & (value>183) & (energy[valid]>.51), CHAR['*'], ring_chars)
        glyph[valid] = np.where(white_head, CHAR['#'], ring_chars)
        strength[valid] = clamp(energy[valid]*.80, .14, 1)

    def project_gem(self, gem, angle, depth, alpha, calm=0.0):
        j = int(clamp(round(gem.y), 0, ROWS-1))
        dx = gem.x - AXIS
        local_x = gem.x - self.middle[j]
        radius = max(self.half[j], 12)
        shell = radius*(.82 + .064*math.sin(j*.17))
        # The reference has pendants hanging well below the edge of the lowest branches.
        limit = int(clamp(j-7, 0, ROWS-1))
        if j > 164 and abs(local_x) > radius*.85:
            radius = max(self.half[limit], abs(local_x)*1.06)
            shell = radius*.78
        forward = shell*math.sqrt(max(.025, 1-(local_x/max(radius,1))**2))
        dz = (forward+5) * (-1 if gem.rear else 1) + self.center_z[j, 0]
        c, s = math.cos(angle), math.sin(angle)
        x = AXIS + dx*c + dz*s
        delta = dz*c - dx*s - dz
        y = gem.y + delta*(.023-.010*calm)
        row = int(clamp(round(y), 0, ROWS-1))
        col = int(clamp(round(x), 0, COLS-1))
        z = dz*c - dx*s
        depth_gap = z - depth[row, col]
        covered = smoothstep((depth_gap + 2.6 + 3.6*calm)/(4.0 + 4.2*calm))
        occlusion = smoothstep((alpha[row, col] - .24)/.24)
        old_visibility = 1 if alpha[row, col] < .3 else covered
        visibility = old_visibility*(1-calm) + (1-occlusion*(1-covered))*calm
        if not gem.rear:
            visibility = max(visibility, smoothstep((c-.89)/.11))
        else:
            visibility *= smoothstep((1-c-.055)/.25)
            if c < 0:
                visibility = max(visibility, smoothstep((-c-.82)/.18))
        return x, y, visibility


def backdrop():
    y, x = np.indices((HEIGHT, WIDTH), dtype=np.float32)
    xc = (x-WIDTH*.5)/(WIDTH*.5)
    yc = y/HEIGHT
    aperture = np.exp(-2.4*xc**2)
    sky = aperture*np.exp(-((yc-.53)/.43)**2)
    ground = np.exp(-((yc-.905)/.075)**2)*aperture
    air = np.exp(-((xc-.42)/.68)**2 - ((yc-.115)/.13)**2)
    cloud = np.sin(x*.006+y*.011)*np.sin(x*.009-y*.016)
    return np.stack([2 + 3*sky + 6*ground + 2*air + .65*cloud,
                     5 + 14*sky + 20*ground + 5*air + 1.2*cloud,
                     17 + 48*sky + 58*ground + 15*air + 1.9*cloud], axis=-1).astype(np.uint16)


class Renderer:
    red_nose = False
    sleigh_start, sleigh_end = SLEIGH_START, SLEIGH_END
    sleigh_width = 852
    sleigh_ease = .045
    sleigh_light = 1.0

    def __init__(self, source):
        self.tree = Tree(source)
        self.atlas = make_atlas().astype(np.uint16)
        self.backdrop = backdrop()
        self.halo_mix = (.20 + .095 * np.sin(X*.23+Y*.16)**2).astype(np.float32)
        self.growth_noise = RNG.uniform(-.010, .010, X.shape)
        self.floor_noise = RNG.random(X.shape)
        self.snow = self.make_snow()
        self.gifts = self.make_gifts()

    def make_snow(self):
        count = 458
        fg = np.arange(count) > 373
        x, y = RNG.uniform(0, COLS, count), RNG.uniform(0, ROWS, count)
        phase, drift = RNG.uniform(0, math.tau, count), RNG.uniform(.3, 3.8, count)
        speed = RNG.uniform(1.5, 7.1, count) + fg*RNG.uniform(2, 4.7, count)
        flicker = RNG.uniform(.7, 2.3, count)
        alpha = RNG.uniform(.24, .55, count) + .26*fg
        snow_color = np.tile([141, 197, 249], (count, 1))
        snow_color[fg] = (209, 237, 255)
        chars = RNG.choice([CHAR['.'], CHAR[':'], CHAR['+'], CHAR['*']], count, p=[.32,.30,.21,.17])
        chars[fg] = RNG.choice([CHAR['+'], CHAR['*'], CHAR['x']], np.sum(fg), p=[.37,.55,.08])
        return x, y, phase, drift, speed, flicker, alpha, snow_color, chars, fg

    def make_gifts(self):
        starts = [12.56, 12.98, 13.43, 13.88, 14.28]
        result = []
        for (sprite, x, bottom), start in zip(draw_ground_gifts(), starts):
            w, h = math.ceil(sprite.width/CELL_WIDTH), math.ceil(sprite.height/CELL_HEIGHT)
            rgba = np.asarray(sprite.resize((w, h), Image.Resampling.BOX), dtype=np.float32)
            color = clamp((rgba[:,:,:3]/255)**.76*260, 0, 255)
            result.append(sprite_sticker(color, (rgba[:,:,3]/255)**.72, x/CELL_WIDTH+w*.5,
                                         bottom/CELL_HEIGHT-h*.5, start))
        return result

    def draw_snow(self, color, glyph, strength, t, front):
        x, y, phase, drift, speed, flicker, alpha, snow_color, chars, big = self.snow
        sx = np.round((x + np.sin(phase+t*.69)*drift - t*speed*.16) % COLS).astype(int) % COLS
        sy = np.round((y + t*speed) % ROWS).astype(int) % ROWS
        wanted = big if front else ~big
        opacity = alpha * (.71+.29*np.sin(t*flicker+phase))
        if front:
            arms = wanted & (opacity > .68) & ((np.arange(len(big)) % 3) == 0)
            for dx, mark in ((-1,'.'), (1,'.')):
                ix = (sx[arms]+dx) % COLS
                color[sy[arms], ix] = snow_color[arms]
                glyph[sy[arms], ix] = CHAR[mark]
                strength[sy[arms], ix] = opacity[arms]*.35
        color[sy[wanted], sx[wanted]] = snow_color[wanted]
        glyph[sy[wanted], sx[wanted]] = chars[wanted]
        strength[sy[wanted], sx[wanted]] = opacity[wanted]

    def draw_floor(self, color, glyph, strength, t):
        f = clamp((Y-174)/19)
        noise = self.floor_noise
        radius = np.exp(-((X-90)/(47+f*73))**2)
        valid = (noise < (.13+.12*f)*radius) & (Y >= 175)
        band = np.exp(-((Y-179)/4.0)**2)*np.exp(-((X-90)/51)**2)
        floor_color = np.stack([24+85*band, 72+31*band, 151+58*band], axis=-1)
        color[valid] = floor_color[valid]
        glyph[valid] = np.where(noise[valid]<.045, CHAR['='], CHAR['-'])
        strength[valid] = (.29+.12*np.sin(X*.077-Y*.32+t*.88)+.21*band)[valid]
        composite_cells(color, glyph, strength, self.tree.floor_rgb, self.tree.floor_glyph,
                        self.tree.floor_alpha*.67*smoothstep(t/.84))

    def stamp_sleigh(self, color, glyph, strength, t):
        if not self.sleigh_start <= t <= self.sleigh_end:
            return
        sprite = draw_sleigh(t, red_nose=self.red_nose)
        target_width = self.sleigh_width
        target_height = round(sprite.height*target_width/sprite.width)
        sprite = sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
        p = (t-self.sleigh_start)/(self.sleigh_end-self.sleigh_start)
        travel = p + self.sleigh_ease*math.sin(math.tau*p)
        cx = round(-target_width+(WIDTH+target_width)*travel)
        cy = round(184 - 78*math.sin(math.pi*p) + 3.6*math.sin(t*5.0))
        sky = Image.new('RGBA', (WIDTH, 440))
        sky.paste(sprite, (cx, cy))
        rgba = np.asarray(sky.resize((COLS, 44), Image.Resampling.BOX), dtype=np.float32)
        opacity = (rgba[...,3]/255)**.70
        rgb = clamp(((rgba[...,:3]/255)**.72*265 + [9, 5, 9])*self.sleigh_light, 0, 255)
        composite_cells(color[:44], glyph[:44], strength[:44], rgb, choose_glyphs(rgb, 684), opacity)
        relative = np.arange(35, dtype=np.float32)
        tx = np.round((cx+19-relative*8.0)/CELL_WIDTH).astype(int)
        ty = np.round((cy+target_height*.72+np.sin(relative*.38-t*3.5)*10+relative*.35)/CELL_HEIGHT).astype(int)
        visible = (tx >= 0) & (tx < COLS) & (ty >= 0) & (ty < 42)
        tx, ty = tx[visible], ty[visible]
        rd = relative[visible]
        color[ty, tx] = np.where((rd%3==0)[:,None], [255,146,208], [127,224,255])
        glyph[ty, tx] = np.where(rd%3==0, CHAR['+'], CHAR['.'])
        strength[ty, tx] = (.28+.29*np.sin(rd*1.85+t*7)**2)*np.exp(-rd/23)

    def angle_at(self, t):
        return math.tau*smoothstep((t-TURN_START)/(TURN_END-TURN_START))

    def draw_canopy(self, t, angle, color, glyph, strength):
        tree_color, tree_alpha, tree_glyph, depth = self.tree.surface_at(angle)
        grow = clamp((t-.75)/4.97)
        growth_tip = 165 - 117*(.19*smoothstep(grow)+.81*grow)
        edge = Y - growth_tip + 22*self.growth_noise + 1.25*np.sin(X*.22+Y*.18+t*.6)
        branch_distance = np.abs(X-self.tree.middle[:,None])/self.tree.half_col
        spreading = smoothstep((edge+3.1)/15) * 1.22
        leaves = smoothstep((edge+2.0)/7.0) * smoothstep((spreading-branch_distance+.10)/.29)
        stalk_tip = 184 - 30*smoothstep((t+.08)/1.12)
        trunk = smoothstep((Y-stalk_tip+2.0)/5.4)
        reveal = np.where(Y>=165, trunk, leaves)
        if t >= 5.95:
            reveal = np.ones_like(Y)
        # A quick silver leading edge makes new foliage visibly grow from the last row.
        trace = np.exp(-(edge/2.2)**2) * (.43 + .25*np.sin(X*.6+Y*.4)**2) * (t < 5.75) * (t>.65)
        lit = .94 + .055*np.sin(X*.129-Y*.155-2.6*t)
        tree_rgb = tree_color*lit[...,None]+trace[...,None]*[16,53,68]
        effective_alpha = tree_alpha**.83*reveal
        composite_cells(color, glyph, strength, tree_rgb, tree_glyph, effective_alpha*.93)
        return effective_alpha, depth

    def gem_reveal(self, p, strength):
        return strength, 0.0

    def calm_at(self, t):
        return 0.0

    def draw_garland(self, t, angle, opacity, depth, color, glyph, strength, calm):
        for ring in self.tree.ring_sections:
            self.tree.draw_ring(ring, t, angle, opacity, depth, color, glyph, strength, calm)

    def draw_ornaments(self, t, angle, effective_alpha, depth, color, glyph, strength, calm):
        if t <= 9.14:
            return
        for item in self.tree.gems:
            p = smoothstep((t-item.starts)/.58)
            if p <= 0:
                continue
            x, y, facing = self.tree.project_gem(item, angle, depth, effective_alpha, calm)
            shine = .88 + .09*calm + (.13-.08*calm)*math.sin(t*2.2+item.x*.43) + .43*math.sin(p*math.pi)
            how_bright, white = self.gem_reveal(p, shine)
            stamp(item, x, y, p*facing, how_bright, color, glyph, strength, white=white)

    def assemble_cells(self, t, use_sleigh=True):
        color = np.zeros((ROWS, COLS, 3), dtype=np.float32)
        glyph = np.zeros((ROWS, COLS), dtype=np.uint8)
        strength = np.zeros((ROWS, COLS), dtype=np.float32)
        self.draw_floor(color, glyph, strength, t)
        self.draw_snow(color, glyph, strength, t, front=False)
        angle = self.angle_at(t)
        calm = self.calm_at(t)
        effective_alpha, depth = self.draw_canopy(t, angle, color, glyph, strength)

        self.draw_garland(t, angle, effective_alpha, depth, color, glyph, strength, calm)
        self.draw_ornaments(t, angle, effective_alpha, depth, color, glyph, strength, calm)
        if t >= self.tree.star.starts:
            item = self.tree.star
            p = smoothstep((t-item.starts)/.63)
            star_width = max(.18+.60*calm, abs(math.cos(angle)))
            shine = 1.09 + .16*math.sin(t*2.6) + math.sin(p*math.pi)*.61
            how_bright, white = self.gem_reveal(p, shine)
            stamp(item, item.x, item.y, p, how_bright, color, glyph, strength, width=star_width, white=white)
            crown_x, crown_y = round(item.x), round(item.y)
            blink = .76+.23*math.sin((t-13.55)*3.8)
            if blink>.74:
                color[crown_y,crown_x] = (249,247,255)
                glyph[crown_y,crown_x] = CHAR['*']
                strength[crown_y,crown_x] = p*blink
        for item in self.gifts:
            p = smoothstep((t-item.starts)/.71)
            y = item.y + .8*math.sin(p*math.pi)*math.cos(p*math.pi)
            how_bright, white = self.gem_reveal(p, 1.05+.35*math.sin(math.pi*p))
            stamp(item, item.x, y, p, how_bright, color, glyph, strength, white=white)
        if use_sleigh:
            self.stamp_sleigh(color, glyph, strength, t)
        self.draw_snow(color, glyph, strength, t, front=True)
        return color, glyph, strength

    def assemble(self, t, use_sleigh=True):
        color, glyph, strength = self.assemble_cells(t, use_sleigh)
        lit = np.clip(color, 0, 255).astype(np.uint16)
        weights = self.atlas[glyph]*(strength*249).astype(np.uint16)[...,None,None] >> 8
        energy = strength*clamp((np.max(color, axis=2)-71)/184)
        fill = (energy*self.halo_mix*255).astype(np.uint16)
        weights = np.minimum(weights+fill[...,None,None], 255)
        pixels = (weights[...,None]*lit[:,:,None,None,:] >> 8)
        pixels = pixels.transpose(0,2,1,3,4).reshape(HEIGHT, WIDTH, 3)
        halo = np.clip(color*energy[...,None]*.245, 0, 255).astype(np.uint8)
        bloom = Image.fromarray(halo).resize((COLS//2, ROWS//2), Image.Resampling.BOX)
        bloom = bloom.filter(ImageFilter.GaussianBlur(1.7)).resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
        return np.minimum(self.backdrop + np.asarray(bloom) + pixels, 255).astype(np.uint8)


def stamp(item, x, y, opacity, shine, color, glyph, strength, width=1, white=0):
    if opacity < .044:
        return
    h, w = item.alpha.shape
    if width < .985:
        idx = np.rint(np.linspace(0, w-1, max(1, round(w*width)))).astype(int)
        if len(idx) == 1:
            idx[0] = w//2
        rgb, alpha, chars = item.color[:,idx], item.alpha[:,idx], item.glyph[:,idx]
        w = alpha.shape[1]
    else:
        rgb, alpha, chars = item.color, item.alpha, item.glyph
    col, row = round(x-(w-1)*.5), round(y-(h-1)*.5)
    a, b, c, d = max(0,col), max(0,row), min(COLS,col+w), min(ROWS,row+h)
    if a >= c or b >= d:
        return
    src = np.s_[b-row:d-row, a-col:c-col]
    dst = np.s_[b:d, a:c]
    lit = rgb[src]*shine
    if white > .01:
        lit = lit*(1-white) + np.array([251, 251, 255], dtype=np.float32)*white
        chars = np.where((white > .50) & (alpha > .42), CHAR['#'], chars)
    composite_cells(color[dst], glyph[dst], strength[dst], lit, chars[src], alpha[src]*opacity)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', required=True)
    parser.add_argument('--snapshot', type=float)
    parser.add_argument('--review', action='store_true')
    parser.add_argument('--no-sleigh', action='store_true')
    args = parser.parse_args()
    renderer = Renderer(args.source)
    if args.snapshot is not None:
        Image.fromarray(renderer.assemble(args.snapshot, not args.no_sleigh)).save(args.output)
        return
    if args.review:
        stages = [1.18, 3.15, 5.55, 8.0, 11.7, 14.85, 17.48, 18.8, 20.3, 22.6]
        grid = Image.new('RGB', (1080, 768))
        for i,t in enumerate(stages):
            im = Image.fromarray(renderer.assemble(t, not args.no_sleigh))
            grid.paste(im.resize((216,384), Image.Resampling.LANCZOS), ((i%5)*216,(i//5)*384))
        grid.save(args.output)
        return
    command = [
        'ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),'-i','-','-an',
        '-c:v','libx264','-pix_fmt','yuv420p','-preset','fast','-crf','16',
        '-movflags','+faststart',args.output,
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        assert encoder.stdin is not None
        for i in range(FPS*DURATION):
            encoder.stdin.write(renderer.assemble(i/FPS, not args.no_sleigh).tobytes())
            if i%(FPS*3)==0:
                print(f'{i//FPS:02}/{DURATION}s', flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise SystemExit('FFmpeg did not finish the video.')


if __name__ == '__main__':
    main()
