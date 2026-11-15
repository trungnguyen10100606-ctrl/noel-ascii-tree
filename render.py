from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1080, 1920
CELL_WIDTH, CELL_HEIGHT = 6, 10
COLS, ROWS = WIDTH // CELL_WIDTH, HEIGHT // CELL_HEIGHT
FPS, DURATION = 30, 12
SCALE, LEFT, TOP = 0.798, 61, 305
SOURCE_HEIGHT = 2000
from pathlib import Path as _Path
ASSETS = _Path(__file__).resolve().parent / 'assets'
FONT = str(ASSETS / 'DejaVuSansMono.ttf')
FONT_BOLD = str(ASSETS / 'DejaVuSansMono-Bold.ttf')
DEFAULT_SOURCE = str(ASSETS / 'tree-source.png')


def ffmpeg_exe():
    """Bundled ffmpeg from imageio-ffmpeg when available, else the system one."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'
ATLAS_CHARS = ' .:`-~+*ox/\\=<>0123456789ABCFHKLMNTVX[]%#@^&W'
CHAR = {character: i for i, character in enumerate(ATLAS_CHARS)}
Y, X = np.indices((ROWS, COLS), dtype=np.float32)
RNG = np.random.default_rng(214)

STAR_OUTLINE = [
    (601, 143), (613, 146), (627, 197), (632, 210), (702, 210),
    (701, 229), (650, 257), (669, 319), (654, 324), (607, 289),
    (584, 301), (546, 322), (537, 314), (554, 258), (512, 226),
    (512, 210), (575, 212), (589, 186),
]
CANOPY = [
    (587, 328), (636, 329), (636, 365), (661, 364), (663, 399),
    (637, 398), (638, 418), (673, 418), (673, 443), (685, 443),
    (689, 473), (720, 480), (721, 521), (734, 522), (732, 542),
    (758, 550), (776, 577), (795, 610), (801, 669), (774, 674),
    (776, 712), (801, 748), (830, 750), (859, 794), (886, 820),
    (888, 847), (919, 845), (922, 883), (892, 898), (891, 926),
    (865, 936), (884, 976), (906, 981), (927, 1004), (932, 1065),
    (955, 1099), (982, 1100), (998, 1145), (1018, 1152), (1020, 1202),
    (1045, 1203), (1056, 1241), (1057, 1284), (1028, 1303),
    (1001, 1301), (1003, 1344), (1036, 1346), (1035, 1380),
    (1021, 1401), (1041, 1425), (1076, 1434), (1079, 1477),
    (1098, 1486), (1112, 1507), (1142, 1513), (1144, 1535),
    (1165, 1538), (1163, 1558), (1196, 1570), (1196, 1657),
    (1129, 1658), (1127, 1680), (1011, 1684), (976, 1691),
    (884, 1687), (842, 1701), (732, 1685), (674, 1696), (557, 1687),
    (507, 1697), (408, 1689), (337, 1690), (307, 1681), (219, 1683),
    (202, 1694), (132, 1694), (110, 1674), (73, 1676), (72, 1655),
    (60, 1656), (61, 1642), (33, 1641), (33, 1624), (14, 1625),
    (14, 1578), (35, 1567), (37, 1542), (68, 1540), (77, 1500),
    (93, 1486), (91, 1470), (131, 1464), (133, 1445), (161, 1436),
    (162, 1408), (194, 1403), (199, 1364), (215, 1359), (208, 1329),
    (233, 1317), (228, 1299), (203, 1305), (176, 1294), (155, 1275),
    (159, 1216), (178, 1210), (187, 1194), (235, 1194), (241, 1168),
    (269, 1163), (269, 1145), (288, 1138), (296, 1104), (325, 1084),
    (327, 1057), (350, 1049), (364, 1022), (396, 997), (398, 970),
    (415, 956), (401, 932), (362, 920), (350, 905), (350, 867),
    (369, 859), (371, 836), (395, 825), (399, 804), (417, 786),
    (423, 762), (440, 750), (445, 723), (426, 716), (441, 688),
    (446, 674), (459, 663), (461, 638), (480, 624), (485, 605),
    (471, 587), (480, 550), (504, 540), (524, 523), (539, 516),
    (538, 471), (549, 451), (554, 415), (570, 401), (565, 363),
    (582, 352),
]
TRUNK = [
    (508, 1570), (687, 1590), (696, 1851), (739, 1855), (739, 1874),
    (790, 1877), (792, 1907), (394, 1915), (390, 1878), (429, 1874),
    (437, 1856), (507, 1854),
]
GEMS = [
    (543, 468, 35, 54), (438, 617, 24, 45), (409, 710, 19, 39),
    (734, 668, 46, 70), (839, 769, 24, 44), (360, 952, 48, 70),
    (251, 1109, 33, 52), (923, 1023, 24, 39), (985, 1135, 25, 43),
    (803, 1280, 58, 83), (285, 1337, 49, 86), (119, 1475, 24, 39),
    (374, 1429, 29, 37), (732, 1534, 55, 81), (1133, 1426, 32, 57),
    (1083, 1481, 20, 37), (252, 1725, 47, 66), (418, 1728, 24, 27),
    (839, 1722, 30, 36), (1055, 1720, 30, 43),
]
ORBIT_TOP = [
    (169, 940), (249, 932), (255, 889), (295, 856), (351, 829),
    (453, 807), (588, 792), (719, 795), (826, 787), (1002, 822),
    (1093, 851), (1134, 891), (1119, 925), (1050, 955),
    (930, 987), (855, 997),
]
ORBIT_LOW = [
    (0, 1283), (85, 1241), (165, 1237), (189, 1276), (95, 1311),
    (37, 1320), (72, 1344), (218, 1368), (395, 1391), (558, 1401),
    (727, 1404), (873, 1422), (1020, 1435), (1113, 1452),
    (1199, 1470), (1199, 1518), (1112, 1550),
]
GROUND_STREAK = [
    (25, 1905), (161, 1896), (312, 1891), (500, 1916), (706, 1920),
    (854, 1911), (999, 1923), (1099, 1954), (1186, 1955),
]


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def make_atlas():
    font = ImageFont.truetype(FONT, 10)
    bank = []
    for character in ATLAS_CHARS:
        sample = Image.new('L', (CELL_WIDTH, CELL_HEIGHT))
        painter = ImageDraw.Draw(sample)
        painter.text((0, 8), character, font=font, anchor='ls', fill=255)
        bank.append(np.array(sample))
    return np.stack(bank)


def mask_from_shapes(size, polygons=(), lines=()):
    mask = Image.new('L', size)
    painter = ImageDraw.Draw(mask)
    for points in polygons:
        painter.polygon(points, fill=255)
    for points, width in lines:
        painter.line(points, fill=255, width=width, joint='curve')
    return mask


def to_grid(image, resample=Image.Resampling.BOX):
    image = image.resize(
        (round(1200 * SCALE), round(SOURCE_HEIGHT * SCALE)), Image.Resampling.BICUBIC,
    )
    canvas = Image.new(image.mode, (WIDTH, HEIGHT))
    canvas.paste(image, (LEFT, TOP))
    return np.asarray(canvas.resize((COLS, ROWS), resample))


def choose_glyphs(colors, seed, tree=False):
    rng = np.random.default_rng(seed)
    brightness = np.max(colors, axis=-1)
    density = np.clip(brightness.astype('float32') / 255, 0, 1)
    ramp = np.array([CHAR[c] for c in '.:-+*ox=0X%#@'])
    dist = density * (5.4 if tree else 8.1) + rng.uniform(0, 3.2, brightness.shape)
    result = ramp[np.clip(dist.astype(int), 0, len(ramp) - 1)]
    if tree:
        code = np.array([CHAR[c] for c in '0123456789ABCFHKLMNTVX[]'])
        code_idx = rng.integers(0, len(code), brightness.shape)
        result = np.where(rng.random(brightness.shape) > 0.48, code[code_idx], result)
        result = np.where(brightness < 53, ramp[1], result)
        horizontal = np.ceil(Y + np.sin(X * .06) * 2) % 11
        result = np.where((horizontal == 0) & (rng.random(brightness.shape) < 0.70),
                          CHAR['-'], result)
    return result.astype(np.uint8)


def tree_from_ref(path):
    source = Image.open(path).convert('RGB').crop((0, 0, 1200, SOURCE_HEIGHT))
    coords = source.size
    tree_mask = mask_from_shapes(coords, [CANOPY, TRUNK], [([(606, 286), (605, 337)], 22)])
    star_mask = mask_from_shapes(coords, [STAR_OUTLINE])
    gem_polygons = [
        [(cx, cy-ry), (cx+round(rx*.72), cy-round(ry*.44)), (cx+rx, cy+round(ry*.21)),
         (cx+round(rx*.58), cy+round(ry*.63)), (cx, cy+ry),
         (cx-round(rx*.64), cy+round(ry*.62)), (cx-rx, cy+round(ry*.20)),
         (cx-round(rx*.60), cy-round(ry*.42))]
        for cx, cy, rx, ry in GEMS
    ]
    gem_mask = mask_from_shapes(coords, gem_polygons)
    orbit_mask = mask_from_shapes(coords, lines=[(ORBIT_TOP, 52), (ORBIT_LOW, 64)])
    floor_mask = mask_from_shapes(coords, lines=[(GROUND_STREAK, 71)])

    rgb = np.asarray(source).astype(np.float32)
    r, g, b = rgb.transpose(2, 0, 1)
    ref_y = np.arange(SOURCE_HEIGHT, dtype=np.float32)[:, None]
    # The reference's blue field gets lighter towards the floor.
    field_g = np.interp(ref_y, [0, 500, 900, 1250, 1550, 1850], [74, 79, 85, 104, 135, 165])
    field_b = np.interp(ref_y, [0, 750, 1200, 1600, 1950], [241, 246, 249, 251, 246])
    field_delta = np.maximum.reduce([r*.8, np.abs(g-field_g)*1.24, np.abs(b-field_b)*1.3])
    distinct = smoothstep((field_delta - 21) / 27)
    highlight = np.maximum(smoothstep((r - 106) / 48), smoothstep((g - field_g - 65) / 64))
    star, gems = np.asarray(star_mask)/255, np.asarray(gem_mask)/255
    canopy = np.asarray(tree_mask)/255
    canopy = canopy * np.where(b > 208, np.maximum(distinct, np.where(r > 35, .60, 0)), 1)
    ornaments = np.maximum(star, gems) * np.maximum(distinct, highlight)
    orbit = np.asarray(orbit_mask)/255 * highlight
    floor = np.asarray(floor_mask)/255 * distinct * np.maximum(
        smoothstep((r - 59)/115),
        .49*smoothstep((field_g - g - 14)/72),
    )
    mask = np.maximum.reduce([canopy, ornaments, orbit, floor * .68])
    coverage = to_grid(Image.fromarray(np.round(255*mask).astype(np.uint8))).astype(np.float32)/255
    safe_cov = np.maximum(coverage[..., None], .09)
    rgb = np.clip(to_grid(Image.fromarray(np.round(rgb * mask[..., None]).astype(np.uint8))) / safe_cov, 0, 255)
    src_cells = rgb / 255
    colors = (255 * np.power(src_cells, .78)).clip(0, 255)
    brightness = np.max(src_cells, axis=2)
    colors += (1 - src_cells) * (8 + 9 * brightness[..., None])
    colors = colors.clip(0, 255)
    glyphs = choose_glyphs(colors, 158, tree=True)
    effects = [to_grid(Image.fromarray(np.round(255*m).astype(np.uint8))).astype(np.float32)/255
               for m in (star*highlight, gems*highlight, orbit)]
    return colors, coverage, glyphs, *effects


def build_background(tree):
    y, x = np.indices((HEIGHT, WIDTH), dtype=np.float32)
    xc = (x - WIDTH * .5) / (WIDTH * .5)
    yc = y / HEIGHT
    aperture = np.exp(-2.4 * xc**2)
    sky_glow = aperture * np.exp(-((yc - .53) / .43)**2)
    ground = np.exp(-((yc - .905) / .075)**2) * aperture
    air = np.exp(-((xc - .42) / 0.65)**2 - ((yc - .14) / .11)**2)
    faint_cloud = np.sin(x*.006 + y*.011) * np.sin(x*.009 - y*.016)
    scan = np.where((y.astype(np.int16) % CELL_HEIGHT) == 0, -.85, .1)
    back = np.stack([
        2 + 3*sky_glow + 6*ground + 2*air + .65*faint_cloud + scan,
        5 + 14*sky_glow + 20*ground + 5*air + 1.2*faint_cloud + scan,
        17 + 48*sky_glow + 58*ground + 15*air + 1.9*faint_cloud + scan,
    ], axis=2)
    canvas = Image.fromarray(back.clip(0, 255).astype(np.uint8))
    light = np.clip(np.max(tree[0], axis=2) / 255, 0, 1)
    color = tree[0] * (tree[1] * light**2 * .31)[..., None]
    color[:int((TOP+130*SCALE)/CELL_HEIGHT), :, :] = 0
    halo = Image.fromarray(color.astype(np.uint8)).resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
    halo = halo.filter(ImageFilter.GaussianBlur(26))
    return np.asarray(canvas), np.asarray(halo)


def draw_floor(color, glyph, strength, t):
    ahead = (Y - 174) / 19
    noise = floor_noise
    floor_fit = np.exp(-((X-90) / (46+np.maximum(ahead, 0)*77))**2)
    cells = (noise < (.10 + .15*np.maximum(ahead, 0)) * floor_fit) & (Y >= 173)
    shimmer = .77 + .23*np.sin(X*.08 - Y*.3 + t*.85)
    band = np.exp(-((Y - 178) / 3.9)**2) * np.exp(-((X - 90) / 49)**2)
    floor_color = np.stack([27+100*band, 75+28*band, 152+60*band], -1)
    color[cells] = floor_color[cells]
    glyph[cells] = np.where(noise[cells] < .05, CHAR['='], CHAR['-'])
    strength[cells] = (.38*shimmer+.21*band)[cells]


def draw_snow(color, glyph, strength, t):
    x = np.floor((snow_x + np.sin(snow_phase+t*.55)*snow_drift - t*snow_speed*.17) % COLS).astype(int)
    y = np.floor((snow_y + t*snow_speed) % ROWS).astype(int)
    wink = .68 + .32*np.sin(t*snow_wink+snow_phase)
    color[y, x] = snow_colors
    glyph[y, x] = snow_chars
    strength[y, x] = snow_strength * wink


def composite_cells(color, glyph, strength, over_color, over_glyph, over_strength):
    valid = over_strength > .115
    color[valid] = over_color[valid]
    glyph[valid] = over_glyph[valid]
    strength[valid] = over_strength[valid]


def stamp_sleigh(color, glyph, strength, t):
    if not 2.55 <= t <= 9.45:
        return
    from sleigh import draw_sleigh

    sprite = draw_sleigh(t)
    # Fill the empty sky while keeping the wagon, its load and both deer readable.
    target_width = 840
    target_height = round(sprite.height * target_width / sprite.width)
    sprite = sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
    p = (t - 2.55) / 6.9
    travel = p + .082*np.sin(2*np.pi*p)
    x = round(-target_width + (WIDTH + target_width) * travel)
    y = round(203 - 80*np.sin(np.pi*p) + 5*np.sin(5.5*t))
    sky = Image.new('RGBA', (WIDTH, 440))
    sky.paste(sprite, (x, y))
    sky_grid = sky.resize((COLS, 440 // CELL_HEIGHT), Image.Resampling.BOX)
    data = np.asarray(sky_grid)
    opacity = np.power(data[..., 3] / 255, .70)
    rgb = data[..., :3].astype(np.float32)
    rgb = np.clip(np.power(rgb/255, .72)*265 + [9, 5, 9], 0, 255)
    code = choose_glyphs(rgb, 684)
    composite_cells(color[:44], glyph[:44], strength[:44], rgb, code, opacity)

    # Loose glowing flakes slip away behind the runner as it crosses the sky.
    relative = np.arange(34, dtype=np.float32)
    trail_x = np.round((x+19 - relative*8.8) / CELL_WIDTH).astype(int)
    trail_y = np.round((y+target_height*.71 + np.sin(relative*.44-t*5.1)*11
                         + relative*.43) / CELL_HEIGHT).astype(int)
    visible = (trail_x >= 0) & (trail_x < COLS) & (trail_y >= 0) & (trail_y < 42)
    tx, ty = trail_x[visible], trail_y[visible]
    color[ty, tx] = np.where((relative[visible]%3 == 0)[:, None], [255, 146, 208], [127, 224, 255])
    glyph[ty, tx] = np.where(relative[visible]%3 == 0, CHAR['+'], CHAR['.'])
    strength[ty, tx] = (.28+.29*np.sin(relative[visible]*1.85+t*9)**2) * np.exp(-relative[visible]/25)


def twinkle_glints(color, glyph, strength, t, reveal):
    for i, (source_x, source_y, phase) in enumerate(glint_points):
        x = round((LEFT+source_x*SCALE)/CELL_WIDTH)
        y = round((TOP+source_y*SCALE)/CELL_HEIGHT)
        if reveal[y, x] < .65:
            continue
        twinkle = max(0.0, np.sin(t*(1.7 + .10*i) + phase))**10
        if i == 0:
            twinkle = max(twinkle, math.exp(-((t-9.0)/.43)**2) * .9)
        if twinkle < .14:
            continue
        color[y, x] = (220, 250, 255) if i%2 == 0 else (255, 219, 244)
        glyph[y, x] = CHAR['*']
        strength[y, x] = .84 + twinkle*.16
        if twinkle > .45:
            color[y, x-1:x+2:2] = (129, 239, 255)
            glyph[y, x-1:x+2:2] = CHAR['-']
            strength[y, x-1:x+2:2] = np.maximum(strength[y, x-1:x+2:2], twinkle*.46)
            color[y-1:y+2:2, x] = (230, 185, 255)
            glyph[y-1:y+2:2, x] = CHAR[':']
            strength[y-1:y+2:2, x] = np.maximum(strength[y-1:y+2:2, x], twinkle*.56)


def prepare():
    global floor_noise, snow_x, snow_y, snow_phase, snow_drift, snow_speed, snow_wink
    global snow_strength, snow_colors, snow_chars, glint_points
    floor_noise = RNG.random((ROWS, COLS))
    n = 480
    snow_x, snow_y = RNG.uniform(0, COLS, n), RNG.uniform(0, ROWS, n)
    snow_phase, snow_drift = RNG.uniform(0, math.tau, n), RNG.uniform(.3, 4, n)
    snow_speed, snow_wink = RNG.uniform(1.4, 8.6, n), RNG.uniform(.6, 1.8, n)
    snow_strength = RNG.uniform(.22, .64, n)
    bright = RNG.random(n) < .08
    snow_strength[bright] += .16
    snow_colors = np.repeat([[117, 178, 248]], n, axis=0)
    snow_colors[bright] = (162, 226, 255)
    snow_chars = RNG.choice([CHAR['.'], CHAR['`'], CHAR[':'], CHAR['+']], n, p=[.51, .24, .19, .06])
    glint_points = [(606, 228, .7), (727, 657, 1.1), (798, 1275, 2.1),
                    (352, 940, 5.0), (731, 1530, .8), (274, 1334, 3.2),
                    (555, 458, 4.5), (840, 770, 6.0), (1129, 1430, .4)]


def render_frame(t, tree, background, atlas, use_sleigh):
    base, coverage, tree_glyphs, star, gems, orbit = tree
    color = np.zeros((ROWS, COLS, 3), dtype=np.float32)
    glyph = np.zeros((ROWS, COLS), dtype=np.uint8)
    strength = np.zeros((ROWS, COLS), dtype=np.float32)
    draw_floor(color, glyph, strength, t)
    draw_snow(color, glyph, strength, t)

    vertical = 1 - (Y - 43) / 138
    advance = -.055 + 1.162 * smoothstep(t / 2.72)
    edge = advance - vertical - .009*np.sin(X*.27 + Y*.36)
    reveal = smoothstep((edge + .034) / .079)
    trace = np.exp(-((edge - .022)/.018)**2) * (t < 3)
    pulse = .5 + .5*np.sin(X*.14 - Y*.20 - 3.6*t)
    orbit_pulse = .5 + .5*np.sin(np.arctan2((Y-111)/26, (X-89)/62)*3.4 - t*3.6)
    star_pulse = .61+.27*np.sin(t*3.14)+.30*math.exp(-((t-9)/.46)**2)
    illumination = .91 + .09*pulse + orbit*(.14+.19*orbit_pulse**5) + star*star_pulse*.30 + gems*.15*pulse
    rgb = base * illumination[..., None] * 1.045
    rgb += trace[..., None]*coverage[..., None]*np.array([22, 74, 97])
    rgb += (orbit * orbit_pulse**6)[..., None]*[.5, 9, 24]
    tree_strength = np.power(coverage, .83) * reveal * (.88+.12*pulse)
    composite_cells(color, glyph, strength, rgb, tree_glyphs, tree_strength)
    twinkle_glints(color, glyph, strength, t, reveal)
    if use_sleigh:
        stamp_sleigh(color, glyph, strength, t)

    weights = atlas[glyph].astype(np.uint16)
    # Solid pixels below the characters preserve the stepped shapes and bright facets.
    highlights = strength * np.clip(np.max(color, axis=-1) - 70, 0, 185) / 185
    bold_pixels = (.20 + .10 * np.sin(X*.23+Y*.16)**2 + .09*orbit)
    fill = np.clip(highlights * bold_pixels * 255, 0, 255).astype(np.uint16)
    weight = (weights * (strength * 248).astype(np.uint16)[..., None, None] >> 8)
    weight = np.minimum(weight+fill[..., None, None], 255)
    cell_rgb = np.clip(color, 0, 255).astype(np.uint16)
    lit = (weight[..., None] * cell_rgb[:, :, None, None, :]) >> 8
    lit = lit.transpose(0, 2, 1, 3, 4).reshape(HEIGHT, WIDTH, 3)
    backdrop, halo = background
    halo_opacity = np.repeat(reveal[:, COLS//2], CELL_HEIGHT)
    visible_halo = (halo * halo_opacity[:, None, None]).astype(np.uint8)
    return np.minimum(backdrop + visible_halo + lit, 255).astype(np.uint8)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('source')
    cli.add_argument('--snapshot', type=float)
    cli.add_argument('--output', required=True)
    cli.add_argument('--no-sleigh', action='store_true')
    cli.add_argument('--quick', action='store_true')
    args = cli.parse_args()
    prepare()
    tree = tree_from_ref(args.source)
    background = build_background(tree)
    atlas = make_atlas()
    if args.snapshot is not None:
        frame = render_frame(args.snapshot, tree, background, atlas, not args.no_sleigh)
        Image.fromarray(frame).save(args.output)
        return

    ffmpeg = [
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', f'{WIDTH}x{HEIGHT}', '-framerate', str(FPS), '-i', '-',
        '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-preset', 'ultrafast' if args.quick else 'fast', '-crf', '27' if args.quick else '16',
        str(Path(args.output)),
    ]
    with subprocess.Popen(ffmpeg, stdin=subprocess.PIPE) as encoder:
        for frame_index in range(FPS*DURATION):
            t = frame_index/FPS
            frame = render_frame(t, tree, background, atlas, not args.no_sleigh)
            encoder.stdin.write(frame.tobytes())
            if frame_index % FPS == 0:
                print(f'{t:02.0f}/{DURATION}s', flush=True)
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError('FFmpeg failed to encode the video.')


if __name__ == '__main__':
    main()
