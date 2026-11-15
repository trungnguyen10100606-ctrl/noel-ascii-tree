"""Hand-drawn RGBA gift sprites sized for the video's 6 × 10 ASCII grid."""

from PIL import Image, ImageDraw


def _gift(width, height, colors):
    paper, top, side, edge, ribbon, gleam, ribbon_shadow = colors
    image = Image.new("RGBA", (126, 133))
    draw = ImageDraw.Draw(image)

    # Two faces extend below the lid. The narrow front panel reflects the floor.
    draw.polygon([(8, 52), (77, 60), (77, 128), (8, 115)], fill=paper)
    draw.polygon([(77, 60), (119, 42), (119, 106), (77, 128)], fill=side)
    draw.polygon([(8, 100), (77, 114), (77, 128), (8, 115)], fill=side)
    draw.line([(11, 64), (11, 111), (75, 125)], fill=edge, width=3)
    draw.line([(77, 64), (77, 126), (117, 104)], fill=edge, width=3)

    # Small stepped color facets help the smallest boxes read as solid forms.
    draw.polygon([(15, 70), (29, 72), (29, 80), (24, 80),
                  (24, 89), (15, 87)], fill=top)
    draw.polygon([(59, 93), (68, 95), (68, 110), (51, 106),
                  (51, 101), (59, 102)], fill=edge)

    draw.polygon([(6, 46), (47, 26), (123, 33), (79, 54)], fill=top)
    draw.polygon([(6, 46), (79, 54), (79, 65), (6, 56)], fill=paper)
    draw.polygon([(79, 54), (123, 33), (123, 43), (79, 65)], fill=edge)
    draw.line([(7, 46), (78, 55), (122, 34)], fill=edge, width=3)

    # The ribbon runs over the lid and down both faces in perspective.
    draw.polygon([(30, 48), (49, 50), (91, 30), (70, 28)], fill=ribbon)
    draw.polygon([(30, 48), (49, 50), (49, 122), (30, 118)], fill=ribbon)
    draw.polygon([(22, 38), (34, 32), (109, 40), (98, 46)], fill=ribbon)
    draw.polygon([(98, 46), (109, 40), (109, 113), (98, 118)], fill=ribbon_shadow)
    draw.line([(31, 51), (31, 115)], fill=gleam, width=4)
    draw.line([(99, 49), (99, 114)], fill=ribbon, width=4)
    draw.line([(30, 47), (70, 29)], fill=gleam, width=3)

    # A clear pair of loops with a contrasting knot survives downsampling.
    draw.polygon([(63, 38), (47, 10), (32, 3), (25, 13), (31, 28),
                  (54, 40)], fill=ribbon_shadow)
    draw.polygon([(62, 38), (78, 9), (95, 5), (104, 15), (97, 29),
                  (73, 41)], fill=ribbon)
    draw.polygon([(57, 35), (40, 15), (33, 12), (33, 20), (43, 29)],
                 fill=gleam)
    draw.polygon([(68, 36), (84, 16), (96, 12), (96, 19), (87, 26)],
                 fill=gleam)
    draw.polygon([(63, 36), (51, 46), (41, 47), (46, 52), (61, 50), (68, 41)],
                 fill=ribbon_shadow)
    draw.polygon([(66, 38), (81, 42), (99, 47), (97, 52), (77, 49), (63, 41)],
                 fill=ribbon)
    draw.ellipse((55, 30, 74, 43), fill=gleam)

    image = image.crop(image.getbbox())
    return image.resize((width, height), Image.Resampling.LANCZOS)


def draw_ground_gifts():
    """Return (RGBA image, left edge, bottom edge) in back-to-front order."""
    boxes = [
        (108, 120, 299, 1840,
         ("#b90b62", "#fd62c0", "#71154f", "#f5269c", "#ffd865", "#fff4b1", "#d5694b")),
        (105, 100, 739, 1833,
         ("#2549ca", "#549cff", "#17347e", "#7159ef", "#51f9e7", "#c9fff5", "#1493a9")),
        (72, 73, 232, 1860,
         ("#007ba6", "#39cce9", "#204179", "#08baf1", "#ff7079", "#ffd7bc", "#c14388")),
        (66, 69, 845, 1867,
         ("#8e26aa", "#e06bf8", "#53216d", "#bf40ee", "#63e6ff", "#d6f7ff", "#3979d0")),
        (83, 79, 665, 1874,
         ("#dd5129", "#ff9d59", "#8c3c50", "#fd7654", "#fff068", "#fff8cf", "#ce7843")),
    ]
    return [(_gift(w, h, palette), x, y) for w, h, x, y, palette in boxes]
