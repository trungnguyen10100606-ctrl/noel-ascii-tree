"""Right-facing Santa sprite, built as flat colors for character-grid sampling."""
from math import cos, radians, sin, tau

from PIL import Image, ImageDraw

SIZE = (485, 155)

GOLD = "#ffcf72"
CREAM = "#fff0bc"
ICE = "#bee8ff"
WHITE = "#f9f8ff"
SCARLET = "#ff555c"
PINK = "#ff679f"
CRIMSON = "#cb154c"
WINE = "#620f47"
SHADOW = "#291750"


def _cubic(start, control_a, control_b, end):
    points = []
    for step in range(17):
        t = step / 16
        u = 1 - t
        points.append(tuple(
            u**3 * a + 3 * u**2 * t * b + 3 * u * t**2 * c + t**3 * d
            for a, b, c, d in zip(start, control_a, control_b, end)
        ))
    return points


def _gift(draw, x, y, w, h, paper, shadow, ribbon):
    draw.rectangle((x, y + 7, x + w - 4, y + h), fill=paper)
    draw.polygon(
        [(x + w - 9, y + 6), (x + w, y + 4),
         (x + w, y + h - 4), (x + w - 9, y + h)],
        fill=shadow,
    )
    draw.rectangle((x - 2, y, x + w - 2, y + 9), fill=paper)
    draw.line((x + 1, y, x + w - 5, y), fill=WHITE, width=2)
    draw.rectangle((x + w * .42, y, x + w * .59, y + h), fill=ribbon)
    draw.rectangle((x, y + 13, x + w - 9, y + 17), fill=ribbon)
    mid = x + w * .5
    draw.line([(mid, y + 2), (mid - 10, y - 6), (mid - 4, y - 9),
               (mid, y - 2), (mid + 6, y - 8), (mid + 12, y - 4),
               (mid, y + 2)], fill=ribbon, width=4, joint="curve")


def _sled_and_rider(draw):
    # Curved rails, curved front wall, and backboard frame the rider and cargo.
    rail = _cubic((6, 135), (23, 151), (154, 150), (189, 134))
    rail += _cubic((189, 134), (204, 127), (210, 109), (203, 113))
    draw.line(rail, fill=WINE, width=10, joint="curve")
    draw.line(rail, fill=GOLD, width=5, joint="curve")
    draw.line(rail, fill=CREAM, width=2, joint="curve")
    draw.line([(47, 126), (36, 141)], fill=SCARLET, width=8)
    draw.line([(141, 128), (154, 141)], fill=SCARLET, width=8)

    draw.polygon([(10, 76), (33, 81), (42, 90), (157, 101),
                  (169, 103), (183, 93), (194, 76), (197, 94),
                  (184, 119), (161, 128), (42, 127), (22, 112)], fill=WINE)
    draw.line([(12, 75), (24, 75), (33, 83), (44, 99)], fill=PINK, width=7, joint="curve")

    _gift(draw, 40, 62, 35, 44, "#00deec", "#007bac", CREAM)
    _gift(draw, 68, 69, 42, 37, "#f242b6", "#a0229b", "#73fded")
    _gift(draw, 28, 81, 28, 30, "#8e63fd", "#5137c3", "#ffb4e8")
    _gift(draw, 56, 79, 35, 35, "#ffab32", "#da534a", "#fcfb95")
    _gift(draw, 37, 42, 34, 28, "#32bbeb", "#475aff", "#ffe479")
    _gift(draw, 71, 53, 29, 25, "#ff59a6", "#bd397b", "#ffe271")

    # Knees and boot silhouettes read as a seated pose.
    draw.polygon([(115, 92), (134, 87), (153, 90), (164, 96),
                  (169, 105), (142, 110), (120, 109)], fill=CRIMSON)
    draw.polygon([(153, 92), (166, 94), (167, 100), (180, 99), (183, 106),
                  (151, 110), (147, 103)], fill=SHADOW)
    draw.line([(146, 92), (155, 94), (157, 103)], fill=ICE, width=5, joint="curve")
    draw.polygon([(118, 54), (146, 56), (153, 66), (150, 96),
                  (130, 103), (110, 97), (107, 83), (109, 64)], fill=SCARLET)
    draw.polygon([(113, 66), (118, 72), (118, 91), (145, 91),
                  (146, 100), (121, 103), (110, 97), (106, 79)], fill=CRIMSON)
    draw.line([(109, 87), (128, 92), (151, 91)], fill=SHADOW, width=7, joint="curve")
    draw.rectangle((135, 89, 144, 97), fill=GOLD)
    draw.rectangle((138, 91, 141, 95), fill=WINE)
    draw.line([(108, 98), (125, 103), (145, 101)], fill=WHITE, width=6, joint="curve")

    # Hat brim, profile, and pointed beard create a legible face at small sizes.
    draw.polygon([(114, 36), (116, 26), (127, 20), (140, 22), (150, 36),
                  (147, 42), (124, 43)], fill=SCARLET)
    draw.polygon([(116, 27), (126, 23), (124, 31), (114, 42),
                  (103, 41), (106, 35)], fill=CRIMSON)
    draw.ellipse((97, 34, 113, 48), fill=ICE)
    draw.ellipse((99, 34, 110, 44), fill=WHITE)
    draw.polygon([(125, 40), (146, 39), (150, 44), (150, 48),
                  (156, 51), (156, 55), (145, 57), (126, 54)], fill="#ffb790")
    draw.polygon([(122, 45), (129, 48), (133, 54), (145, 53), (152, 55),
                  (153, 60), (146, 65), (140, 76), (131, 71),
                  (121, 63), (119, 52)], fill=WHITE)
    draw.polygon([(121, 52), (128, 56), (132, 65), (143, 66), (140, 76),
                  (130, 71), (122, 64), (118, 58)], fill=ICE)
    draw.line([(116, 43), (127, 38), (149, 37)], fill=WHITE, width=8, joint="curve")
    draw.rectangle((145, 44, 148, 47), fill=SHADOW)
    draw.line([(137, 69), (151, 76), (172, 69)], fill=CRIMSON, width=16, joint="curve")
    draw.line([(135, 66), (150, 72), (170, 67)], fill=SCARLET, width=10, joint="curve")
    draw.line([(165, 67), (169, 72)], fill=WHITE, width=8)
    draw.ellipse((169, 61, 183, 72), fill=GOLD)

    top = _cubic((11, 83), (34, 108), (91, 108), (135, 107))
    top += _cubic((135, 107), (159, 108), (182, 105), (191, 80))
    bottom = _cubic((191, 80), (207, 97), (185, 132), (156, 133))
    bottom += _cubic((156, 133), (65, 138), (21, 135), (11, 83))
    draw.polygon(top + bottom, fill=CRIMSON)
    shine = _cubic((15, 91), (35, 113), (91, 117), (132, 116))
    shine += _cubic((132, 116), (174, 116), (182, 111), (196, 93))
    draw.polygon(top + list(reversed(shine)), fill=SCARLET)
    draw.line(top, fill=GOLD, width=5, joint="curve")
    draw.line(_cubic((32, 115), (82, 133), (159, 126), (179, 120)),
              fill=PINK, width=4, joint="curve")

    draw.polygon([(88, 116), (94, 120), (88, 126), (82, 121)], fill=CREAM)
    draw.polygon([(101, 117), (105, 120), (101, 123), (97, 120)], fill=PINK)
    draw.polygon([(75, 115), (80, 119), (75, 122), (71, 118)], fill=PINK)


# Segment angles are measured from vertical down. The foreleg bends back
# at the carpus, while the hind leg folds forward beneath the hock.
FORE_STRIDE = [
    (58, 35, 23), (38, 20, 10), (12, 9, 10), (-17, -17, -23),
    (-29, -47, -66), (2, -45, -114), (44, -19, -123), (63, 13, -47),
]
HIND_STRIDE = [
    (55, -11, 28), (38, -22, 13), (17, -21, -8), (-6, -28, -32),
    (-28, -47, -40), (5, -70, 37), (46, -74, 99), (64, -49, 77),
]


def _leg_joints(hip, cycle, poses, lengths):
    position = cycle * len(poses)
    index = int(position // 1)
    u = position - index
    before, first, second, after = (
        poses[j % len(poses)] for j in range(index - 1, index + 3)
    )
    joints = [hip]
    x, y = hip
    for a, b, c, d, length in zip(before, first, second, after, lengths):
        # A cyclic cubic moves the rigid segments through each pose continuously.
        angle = radians(.5 * (2*b + (-a+c)*u + (2*a-5*b+4*c-d)*u*u
                              + (-a+3*b-3*c+d)*u*u*u))
        x += length * sin(angle)
        y += length * cos(angle)
        joints.append((x, y))
    return joints


def _deer(draw, x, y, phase, lead=False, red_nose=False):
    def p(points):
        return [(x + a, y + b) for a, b in points]

    amber = "#ec994f" if lead else "#ffa759"
    top = "#ffd087" if lead else "#ffbe7f"
    flank = "#bb5f55" if lead else "#cd6a59"
    dark = "#743746"
    crest = "#e7a96e"

    # The far pair lands slightly ahead of the near pair in each stride.
    for base_x, base_y, fore, offset, near in (
        (66, 62, True, .17, False), (23, 62, False, .60, False),
        (71, 63, True, 0., True), (25, 64, False, .43, True),
    ):
        poses, lengths = (FORE_STRIDE, (19, 19, 15)) if fore else (HIND_STRIDE, (20, 18, 17))
        hip, upper, lower, hoof = _leg_joints((base_x, base_y), phase + offset, poses, lengths)
        # The light edge retains the two bends when sampled into character cells.
        draw.line(p([hip, upper, lower]), fill=flank if near else "#98524f",
                  width=10 if near else 8, joint="curve")
        draw.line(p([lower, hoof]), fill="#e39460" if near else "#a96158",
                  width=7 if near else 6)
        draw.line(p([hip, upper, lower]), fill=amber if near else "#ce825f",
                  width=5 if near else 3, joint="curve")
        hoof_x, hoof_y = hoof
        draw.line(p([(hoof_x - 2, hoof_y - 1), (hoof_x + 4, hoof_y)]),
                  fill="#ffb87b" if near else "#b6736d", width=6 if near else 5)

    # A compact rising neck and tapered muzzle keep the two deer silhouettes separated.
    draw.polygon(p([(17, 43), (8, 36), (1, 37), (7, 49), (15, 53)]), fill=CREAM)
    draw.polygon(p([(10, 47), (24, 43), (42, 46), (55, 44), (63, 36),
                    (74, 27), (80, 32), (80, 53), (78, 68), (70, 74),
                    (56, 75), (41, 73), (29, 77), (14, 73), (8, 61)]), fill=flank)
    draw.polygon(p([(11, 48), (24, 43), (43, 46), (56, 44), (62, 37),
                    (71, 31), (77, 36), (74, 49), (66, 57), (48, 60),
                    (33, 60), (21, 67), (10, 64)]), fill=amber)
    draw.polygon(p([(14, 47), (25, 43), (37, 46), (52, 47), (44, 52),
                    (24, 52), (15, 57)]), fill=top)
    draw.polygon(p([(65, 54), (69, 40), (74, 29), (85, 33),
                    (82, 52), (78, 65), (71, 70), (62, 68)]), fill=top)
    draw.polygon(p([(72, 37), (70, 27), (65, 23), (64, 17), (76, 22), (79, 31)]), fill=flank)
    draw.line(p([(73, 29), (66, 21)]), fill=top, width=4)

    antler_a = p([(80, 28), (77, 17), (72, 12), (72, 6), (73, 2)])
    antler_b = p([(86, 27), (87, 16), (92, 12), (96, 3)])
    draw.line(antler_a, fill=crest, width=5, joint="curve")
    draw.line(p([(75, 15), (65, 10), (63, 5)]), fill=crest, width=5, joint="curve")
    draw.line(p([(78, 19), (81, 12), (80, 7)]), fill=crest, width=4, joint="curve")
    draw.line(antler_b, fill=CREAM, width=5, joint="curve")
    draw.line(p([(91, 14), (86, 6), (88, 2)]), fill=CREAM, width=4, joint="curve")
    draw.line(p([(94, 10), (102, 8), (104, 4)]), fill=CREAM, width=4, joint="curve")

    draw.polygon(p([(75, 28), (85, 23), (94, 28), (99, 35), (107, 37),
                    (112, 44), (110, 49), (98, 51), (87, 47), (78, 45)]), fill=amber)
    draw.polygon(p([(88, 41), (98, 43), (110, 43), (112, 47), (108, 51),
                    (98, 51), (89, 47)]), fill=CREAM)
    draw.line(p([(88, 34), (93, 34)]), fill=SHADOW, width=5)
    if red_nose:
        draw.ellipse((x + 102, y + 36, x + 115, y + 49), fill="#9b1239")
        draw.ellipse((x + 103, y + 36, x + 114, y + 47), fill="#ff1538")
        draw.ellipse((x + 105, y + 37, x + 110, y + 41), fill="#ff7868")
    else:
        draw.ellipse((*p([(105, 39)])[0], *p([(112, 46)])[0]),
                     fill=PINK if lead else dark)
    draw.line(p([(61, 42), (67, 50), (70, 61)]), fill=CRIMSON, width=7, joint="curve")
    draw.line(p([(61, 43), (67, 50), (70, 60)]), fill=GOLD, width=3, joint="curve")
    draw.ellipse((*p([(66, 56)])[0], *p([(74, 64)])[0]), fill=CREAM)


def draw_sleigh(t, red_nose=False):
    """Return a 485 × 155 RGBA frame with an optional red nose on the lead deer."""
    canvas = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(canvas)
    phase = 1.38 * t
    lead_phase = phase + .24
    rear_y = 17 + round(3 * sin(tau * (phase + .09)))
    front_y = 5 + round(3 * sin(tau * (lead_phase + .09)))

    rope_a = _cubic((177, 67), (205, 82), (222, 79), (285, rear_y + 53))
    rope_b = _cubic((316, rear_y + 42), (336, 55), (361, 63), (434, front_y + 57))
    traces = _cubic((184, 92), (251, 98), (337, 89), (430, front_y + 63))
    draw.line(traces, fill="#b56b7b", width=3, joint="curve")
    draw.line(rope_a, fill=GOLD, width=4, joint="curve")
    draw.line(rope_b, fill=GOLD, width=4, joint="curve")

    _deer(draw, 221, rear_y, phase)
    _deer(draw, 368, front_y, lead_phase, lead=True, red_nose=red_nose)
    _sled_and_rider(draw)
    return canvas
