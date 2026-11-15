"""Reproject the tree's colored surface samples into an ASCII depth buffer."""
from __future__ import annotations

import math

import numpy as np

from render import CHAR, COLS, ROWS, X, Y
from render_v2 import AXIS


def _ramp(symbols):
    return np.array([CHAR[c] for c in symbols if c in CHAR], dtype=np.uint8)


class PointCanopy:
    """The canopy's stepped profile sweeps out a textured 3D volume."""

    def __init__(self, tree):
        self.tree = tree
        self.ramp = _ramp('.:^+*oVX%&WM#@')
        self.backup_ramp = _ramp(':^+*oVX%&WM#@')
        rng = np.random.default_rng(5243)
        xz, surface, color, texture = [], [], [], []

        for row in np.flatnonzero(np.max(tree.front_alpha, axis=1) > .12):
            radius = float(tree.half[row])
            mid = float(tree.middle[row])
            ratio = float(tree.ratio[row, 0])
            center_depth = float(tree.center_z[row, 0])
            azimuth_count = max(11, round(math.tau * radius * 1.17))
            core_count = max(5, round(math.tau * radius * .39))
            for core, count in ((False, azimuth_count), (True, core_count)):
                theta = (np.arange(count) + rng.uniform(0, 1, count)) * (math.tau / count)
                theta += rng.uniform(0, math.tau)
                sin, cos = np.sin(theta), np.cos(theta)
                ring = rng.uniform(.58, .91, count) if core else rng.uniform(.93, 1.02, count)
                row_offset = rng.uniform(-.57, .57, count)
                behind = np.clip(-cos * 2.15, 0, 1)
                bend = .21 * math.sin(row*.098) + .13 * math.sin(row*.31)
                image_x = mid + radius * (.976*np.clip(sin + behind*bend, -1, 1))
                px = np.clip(image_x, 0, COLS-1.001)
                lo = px.astype(int)
                frac = px - lo
                alpha = (1-frac)*tree.front_alpha[row, lo] + frac*tree.front_alpha[row, lo+1]
                keep = alpha > .085
                if not np.any(keep):
                    continue
                sample = tree.front_rgb[row, lo]*(1-frac[:, None]) + tree.front_rgb[row, lo+1]*frac[:, None]
                sample = sample*(1-.195*behind[:, None]) + sample[:, (2, 0, 1)]*(.205*behind[:, None])
                sample *= (.79 if core else 1)
                px3 = mid-AXIS + radius * sin * ring
                pz3 = center_depth + radius * ratio * cos * ring
                xz.append(np.stack([px3, pz3], axis=1)[keep])
                surface.append(np.stack([row+row_offset, theta, sin, cos], axis=1)[keep])
                color.append(sample[keep])
                texture.append(np.stack([alpha, rng.uniform(-1, 1, count)], axis=1)[keep])

        self.x, self.z = np.concatenate(xz).astype(np.float32).T.copy()
        self.y, self.theta, self.nx, self.nz = np.concatenate(surface).astype(np.float32).T.copy()
        self.rgb = np.concatenate(color).astype(np.float32)
        self.alpha, self.grain = np.concatenate(texture).astype(np.float32).T.copy()
        self.intensity = np.max(self.rgb, axis=1) / 255
        self.point_ids = np.arange(len(self.x), dtype=np.int64) + 1
        self.packing_shift = int(len(self.x)).bit_length()
        self.point_mask = (1 << self.packing_shift) - 1

    def sample(self, t, angle, calm=0.0):
        """Return per-cell RGB, opacity, glyph index and nearest depth."""
        c, s = math.cos(angle), math.sin(angle)
        sx = AXIS + self.x*c + self.z*s
        pz = self.z*c - self.x*s
        sy = self.y + (self.z - pz)*.008
        cols = np.rint(sx).astype(np.int32)
        rows = np.rint(sy).astype(np.int32)
        valid = (cols >= 0) & (cols < COLS) & (rows >= 0) & (rows < ROWS)
        flat = cols[valid] + rows[valid]*COLS

        encoded_depth = np.rint((pz[valid] + 192.0) * 512).astype(np.int64)
        packed = (encoded_depth << self.packing_shift) | self.point_ids[valid]
        winners = np.zeros(COLS * ROWS, dtype=np.int64)
        np.maximum.at(winners, flat, packed)
        occupancy = winners.reshape(ROWS, COLS) > 0
        point = (winners[winners > 0] & self.point_mask) - 1

        # The analytic silhouette supplies a dark interior where no point lands.
        # Both the point surface and this low-energy fill refresh their glyphs each frame.
        backup_rgb, backup_alpha, _, backup_z = self.tree.surface_at(angle)
        hue_wave = .5 + .5*np.sin((X-AXIS)*.122 + Y*.153 - t*4.4)
        back_value = np.max(backup_rgb, axis=2)/255
        fallback_motion = .34 * (1 - calm*.60)
        index = np.minimum(
            len(self.backup_ramp)-1,
            (np.clip(.155+.43*back_value+fallback_motion*hue_wave, 0, 1)*len(self.backup_ramp)).astype(int),
        )
        glyph = self.backup_ramp[index]
        color = (backup_rgb * .65).astype(np.float32)
        opacity = (backup_alpha * .64).astype(np.float32)
        depth = backup_z.astype(np.float32, copy=True)
        if not len(point):
            return color, opacity, glyph, depth

        theta, py = self.theta[point], self.y[point]
        normal = self.nz[point]*c - self.nx[point]*s
        azimuth = theta + py*.106 - t*2.37
        coil = (.5 + .5*np.sin(azimuth*2-.37))**11
        quiet = np.sin(theta*6.83 + py*.321 + t*4.2) * .087
        wave = 1 - calm*.72
        brightness = .77 + .19*normal + (.24*coil + quiet + .059*self.grain[point])*wave
        lit = self.rgb[point] * brightness[:, None]
        lit += (coil*wave)[:, None] * np.array([7, 18, 22], dtype=np.float32)
        density = (.15 + .46*self.intensity[point] + .187*normal
                   + (.215*coil + quiet + self.grain[point]*.075)*wave)
        render_index = np.rint(np.clip(density, 0, 1) * (len(self.ramp)-1)).astype(int)

        color[occupancy] = lit
        glyph[occupancy] = self.ramp[render_index]
        opacity[occupancy] = self.alpha[point]**.57
        depth[occupancy] = pz[point]
        if calm > 0:
            # The interpolated surface anchors large color patches as visible samples change.
            mix = calm*.51*np.clip((backup_alpha-.05)*1.19, 0, 1)
            color = color*(1-mix[...,None]) + backup_rgb*.94*mix[...,None]
            opacity = np.maximum(opacity, backup_alpha*(.64+.23*calm))
        return color, opacity, glyph, depth
