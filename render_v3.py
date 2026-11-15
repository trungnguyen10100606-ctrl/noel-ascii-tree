"""A rotating scene projected onto a fixed, high-contrast ASCII character grid."""
from __future__ import annotations

import argparse
import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from point_canopy import PointCanopy
from render import ATLAS_CHARS, DEFAULT_SOURCE, ffmpeg_exe, CHAR, COLS, FONT, FPS, HEIGHT, ROWS, WIDTH, X, Y, composite_cells
from render_v2 import DURATION, Renderer, clamp, smoothstep

FRAME_TIMES = [1.4, 2.8, 4.15, 5.85, 6.7, 8.35, 11.4, 14.7, 18.9, 23.75]


def ascii_atlas(pitch_x, pitch_y, font_size, baseline):
    font = ImageFont.truetype(FONT, font_size)
    stack = []
    for char in ATLAS_CHARS:
        tile = Image.new('L', (pitch_x, pitch_y))
        ImageDraw.Draw(tile).text((0, baseline), char, font=font, anchor='ls', fill=255)
        stack.append(np.array(tile, dtype=np.uint16))
    return np.stack(stack)


class ProjectedRenderer(Renderer):
    pitch_x, pitch_y, font_size, baseline = 10, 16, 16, 12
    canopy_begins, canopy_rise = 1.04, 4.42
    trunk_begins, trunk_rise = .30, .72

    def __init__(self, source):
        super().__init__(source)
        self.tree.front_rgb = self.color_canopy(self.tree.front_rgb)
        self.cloud = PointCanopy(self.tree)
        self.screen_font = ascii_atlas(self.pitch_x, self.pitch_y, self.font_size, self.baseline)
        self.backdrop = (self.backdrop*.79).astype(np.uint16)
        grid_cols, grid_rows = WIDTH//self.pitch_x, HEIGHT//self.pitch_y
        tx = (np.arange(grid_cols, dtype=np.float32)+.5)*COLS/grid_cols-.5
        ty = (np.arange(grid_rows, dtype=np.float32)+.5)*ROWS/grid_rows-.5
        bx, by = np.floor(tx).astype(int), np.floor(ty).astype(int)
        fx, fy = tx-bx, ty-by
        self.lookup_x = np.stack(np.broadcast_arrays(bx[None,:], (bx+1)[None,:], bx[None,:], (bx+1)[None,:]))
        self.lookup_y = np.stack(np.broadcast_arrays(by[:,None], by[:,None], (by+1)[:,None], (by+1)[:,None]))
        self.mix = np.stack([(1-fy[:,None])*(1-fx[None,:]),
                             (1-fy[:,None])*fx[None,:],
                             fy[:,None]*(1-fx[None,:]),
                             fy[:,None]*fx[None,:]]).astype(np.float32)
        # The lower neon ring writes on first. A white head leads each sweep.
        upper, lower = self.tree.ring_sections
        self.tree.ring_sections = [
            (*lower[:5], 5.81, 1.52, lower[-1]),
            (*upper[:5], 7.21, 1.71, upper[-1]),
        ]

    def color_canopy(self, color):
        return color

    def angle_at(self, t):
        additional_turn = .57 * math.tau * smoothstep((t-14.8)/8.5)
        return math.radians(17.76)*(t-14.8) + additional_turn

    def gem_reveal(self, p, strength):
        return strength, float(smoothstep(p/.21) * (1-smoothstep((p-.27)/.47)))

    def draw_canopy(self, t, angle, color, glyph, strength):
        rgb, alpha, chars, depth = self.cloud.sample(t, angle, self.calm_at(t))
        c, s = math.cos(angle), math.sin(angle)
        center = self.tree.left_start*c + self.tree.center_z*s
        x_delta = X - (self.tree.middle[:,None] - self.tree.left_start + center)
        dist = np.abs(x_delta)/np.maximum(self.tree.half_col, 1.0)
        branch_pause = .31*clamp(dist)**1.45 + self.growth_noise*5
        branch_pause += .105*np.sin(X*.103 + Y*.271) + .062*np.sin(X*.32 - Y*.165)
        canopy_start = self.canopy_begins + clamp((165-Y)/112.0)*self.canopy_rise + branch_pause
        trunk_start = self.trunk_begins + clamp((183-Y)/19)*self.trunk_rise + self.growth_noise*3.1
        age = t - np.where(Y >= 166, trunk_start, canopy_start)
        return self.paint_foliage(rgb, alpha, chars, depth, age, color, glyph, strength)

    def paint_foliage(self, rgb, alpha, chars, depth, age, color, glyph, strength):
        grown = smoothstep((age+.033)/.145)
        fresh = smoothstep(age/.077) * (1-smoothstep((age-.12)/.27))
        fresh *= clamp(alpha*1.50)
        bright_rgb = rgb * (1-fresh[...,None]) + fresh[...,None]*[244, 252, 255]
        sprout = (fresh > .38) & (alpha > .28)
        ink = np.where(sprout, CHAR['#'], chars)
        opacity = alpha*grown
        visible = np.minimum(opacity*(.99+.15*fresh), 1)
        composite_cells(color, glyph, strength, bright_rgb, ink, visible)
        return opacity, depth

    def read_cells(self, color, glyph, strength, calm=0.0):
        choices = color[self.lookup_y, self.lookup_x]
        weight = strength[self.lookup_y, self.lookup_x]
        ink_strength = np.max(choices, axis=-1)/255
        rank = (self.mix*.74+.26)*weight**1.14*(.21+ink_strength)
        winner = np.argmax(rank, axis=0)[None]
        selected_strength = np.take_along_axis(weight, winner, axis=0)[0]
        selected_color = np.take_along_axis(choices, winner[...,None], axis=0)[0]
        selected_char = np.take_along_axis(glyph[self.lookup_y, self.lookup_x], winner, axis=0)[0]
        local_mix = (self.mix*weight)[...,None]
        mean = np.sum(choices*local_mix, axis=0)/np.maximum(np.sum(local_mix, axis=0), .05)
        average_strength = np.sum(weight*self.mix, axis=0)
        coverage = clamp((.83-.17*calm)*selected_strength + (.17+.17*calm)*average_strength)
        mix = .12+.24*calm
        return selected_color*(1-mix)+mean*mix, selected_char, coverage

    def assemble(self, t, use_sleigh=True):
        color, glyph, strength = self.read_cells(*self.assemble_cells(t, use_sleigh), calm=self.calm_at(t))
        rgb = np.clip(color*1.12, 0, 255).astype(np.uint16)
        masks = self.screen_font[glyph]
        opacity = (strength*255).astype(np.uint16)[...,None,None]
        energy = strength*clamp((np.max(color, axis=2)-105)/150)
        solid = (energy*9).astype(np.uint16)[...,None,None]
        mask = np.minimum((masks*opacity >> 8)+solid, 255)
        pixels = mask[...,None]*rgb[:,:,None,None,:] >> 8
        pixels = pixels.transpose(0,2,1,3,4).reshape(HEIGHT, WIDTH, 3)
        glow = np.clip(color*energy[...,None]*.19, 0, 255).astype(np.uint8)
        bloom = Image.fromarray(glow).filter(ImageFilter.GaussianBlur(1.2))
        bloom = bloom.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
        return np.minimum(self.backdrop + np.asarray(bloom) + pixels, 255).astype(np.uint8)


def main(renderer_type=ProjectedRenderer, review_times=FRAME_TIMES, crf='16', duration=DURATION):
    cli = argparse.ArgumentParser()
    cli.add_argument('source', nargs='?', default=DEFAULT_SOURCE)
    cli.add_argument('--output', default='noel-ascii.mp4')
    cli.add_argument('--snapshot', type=float)
    cli.add_argument('--review', action='store_true')
    cli.add_argument('--duration', type=float, default=duration)
    args = cli.parse_args()
    renderer = renderer_type(args.source)
    if args.snapshot is not None:
        Image.fromarray(renderer.assemble(args.snapshot)).save(args.output)
        return
    if args.review:
        grid = Image.new('RGB', (1080, 768))
        for i, t in enumerate(review_times):
            im = Image.fromarray(renderer.assemble(t))
            grid.paste(im.resize((216,384), Image.Resampling.LANCZOS), ((i%5)*216,(i//5)*384))
        grid.save(args.output)
        return
    encoder_args = [
        ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),'-i','-','-an',
        '-c:v','libx264','-pix_fmt','yuv420p','-preset','fast','-crf',crf,
        '-movflags','+faststart',args.output,
    ]
    with subprocess.Popen(encoder_args, stdin=subprocess.PIPE) as encoder:
        assert encoder.stdin is not None
        for index in range(round(FPS*args.duration)):
            encoder.stdin.write(renderer.assemble(index/FPS).tobytes())
            if index%(FPS*3)==0:
                print(f'{index//FPS:02}/{args.duration:g}s', flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise SystemExit('FFmpeg did not finish the video.')


if __name__ == '__main__':
    main()
