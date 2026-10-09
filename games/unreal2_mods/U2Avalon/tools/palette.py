"""The Liandri palette: 8 colours measured from the Hunyuan paint models (tools/hunyuan_palette.py, 2026-10-06) +
the 4 the artist asked for in the redesign (artist.md s. 2.2, plan.md D5, approved 2026-10-09): bodies in
near-black charcoal and dark steel (~55 % of every texture), mid greys for trim and platforms (~25 %), a deep
rust-red for accent panels (~10 %), a dusty brown for dirt bands, light grey only on the cooling towers' shells.
Orange is the company's SIGNAL colour (doors, door frames, the road dash, pad markings; < 3 %), glow the company's
warm light (< 2 %). The four new ones: slate = the Authority's body/trim, cyan = cold light (screens, the Authority's
one lit strip; emissive), hazard = yellow for edges, hooks, nosings and moving machines (the gameplay channel: orange
is no longer the hazard colour), soot = stains only, darker than the lifted charcoal (never a body colour).

Values are LINEAR rgb (Blender's Principled base colour; the sRGB they came from is in the comment) and Pal.tga
stores them linear too: UE2's overbright sun washes sRGB-encoded textures to cream. The darks were lifted once
(charcoal, steel, rustred, brown) because UE2 vertex lighting turned the measured values black; soot is deliberately
below that floor because it is only ever a stain on something lit.

THE TEXTURE (Pal.tga, 64 x 64, written by write_tga()): the first 8 colours are the 8-px column stripes they always
were, but only in the middle rows (16..47); the 4 new colours are 16-px columns in a 16-row cap band that is written
IDENTICALLY at the top and the bottom. Every existing ASE samples U = (i + 0.5) / 8 at V = 0.5, so it still hits
its old column; the new stripes are sampled at V = 1/8 (or 7/8: the two bands are the same, so the TGA's row order
cannot matter, the lesson that made the stripes columns in the first place). U is normalised, so 12 full-height
columns would have moved every old mesh onto the wrong colour; this layout is a superset of the old texture.
Import with MIPS=0 as before (no mip averaging across the bands).
"""
import struct

COLOURS = {
    # the measured 8 (stripes 0-7: full-width column stripes, as before)
    "charcoal": (0.085, 0.078, 0.076),   # #4f4b4a  the bodies (lifted from the measured #3a3636: UE2 vertex light has no cavity, it went black)
    "steel":    (0.190, 0.180, 0.172),   # #777370 (lifted)  secondary walls, legs, machinery
    "grey":     (0.270, 0.260, 0.252),   # #8f8c89  trim, roof slabs, platforms, concrete
    "pale":     (0.540, 0.540, 0.520),   # #c2c2be  cooling-tower shells, the office
    "rustred":  (0.170, 0.030, 0.012),   # #702a18 (lifted)  accent panels, silos, the dead rig
    "brown":    (0.135, 0.090, 0.074),   # #665449 (lifted)  dirt bands, weathered panels
    "orange":   (0.480, 0.095, 0.015),   # #b85a22  the company's signal: doors, door frames, the road dash, pad marks
    "glow":     (1.000, 0.450, 0.100),   # lit strips and lamps (emissive): the company's warm sodium light
    # the redesign's 4 (stripes 8-11: the cap band)
    "slate":    (0.105, 0.135, 0.165),   # #5b6670  the Authority / TCA body and trim: tower, checkpoint, pad markings
    "cyan":     (0.250, 0.850, 1.000),   # #8cefff  cold light (emissive): screens, consoles, the Authority's one lit strip
    "hazard":   (0.550, 0.380, 0.030),   # #c4a530  hazard yellow: edges, hooks, stair nosings, grate rims, moving machines
    "soot":     (0.030, 0.027, 0.026),   # #302e2d  stains only: stack tops, under vents, burnt-out shacks, dark holes
}
NAMES = list(COLOURS)
N = len(NAMES)                         # 12 stripes
BASE = 8                               # the old full-column stripes
SIZE = 64                              # the texture's width and height
BAND = 16                              # the cap band's height (rows 0..15 and 48..63)
EMISSIVE = {"glow", "cyan"}

# the artist's value roles (artist.md s. 2.1): body 55 % / trim 25 % / accent 10 % / signal < 3 % / light < 2 %
ROLES = {
    "body":   ["charcoal", "steel", "slate"],
    "trim":   ["grey", "pale"],
    "accent": ["rustred", "brown"],
    "signal": ["orange", "hazard"],
    "light":  ["glow", "cyan"],
    "stain":  ["soot"],
}

# the old names the first builders used -> the measured palette
ALIASES = {"concrete": "steel", "dark": "charcoal", "rust": "brown"}


def colour(name):
    return COLOURS[ALIASES.get(name, name)]


def index(name):
    return NAMES.index(ALIASES.get(name, name))


def role_of(name):
    name = ALIASES.get(name, name)
    return next(r for r, ns in ROLES.items() if name in ns)


def rect(i):
    """stripe i's pixel rectangle (x0, y0, x1, y1), rows top-down; the cap-band stripes return the TOP copy
    (the bottom copy is the same rectangle mirrored: y -> SIZE - y)"""
    if i < BASE:
        w = SIZE // BASE
        return (i * w, BAND, (i + 1) * w, SIZE - BAND)
    w = SIZE // (N - BASE)
    j = i - BASE
    return (j * w, 0, (j + 1) * w, BAND)


def urange(name_or_index):
    """(u0, u1, v0, v1) of a stripe: the texture-space box whose middle uv() samples"""
    i = name_or_index if isinstance(name_or_index, int) else index(name_or_index)
    x0, y0, x1, y1 = rect(i)
    return (x0 / SIZE, x1 / SIZE, y0 / SIZE, y1 / SIZE)


def role_uranges(role):
    """the role's stripes as [(name, (u0, u1, v0, v1)), ...]"""
    return [(n, urange(n)) for n in ROLES[role]]


def uv(name_or_index):
    """the UV every triangle of that colour uses: the stripe's middle"""
    u0, u1, v0, v1 = urange(name_or_index)
    return ((u0 + u1) / 2, (v0 + v1) / 2)


def stripe_at(u, v):
    """the stripe index a (u, v) samples, or None if it falls outside every stripe (row-order agnostic)"""
    x, y = int(u * SIZE) % SIZE, int(v * SIZE) % SIZE
    if y >= SIZE - BAND:
        y = SIZE - 1 - y
    for i in range(N):
        x0, y0, x1, y1 = rect(i)
        if x0 <= x < x1 and y0 <= y < y1:
            return i
    return None


def image(colours=None):
    """the texture as rows (top-down) of (r, g, b, a) bytes, linear values; colours = the stripe list (default COLOURS)"""
    cols = list(COLOURS.values()) if colours is None else colours
    px = [[(0, 0, 0, 255)] * SIZE for _ in range(SIZE)]
    for i, c in enumerate(cols):
        b = tuple(max(0, min(255, int(round(v * 255)))) for v in c[:3]) + (255,)
        x0, y0, x1, y1 = rect(i)
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[y][x] = b
                if i >= BASE:
                    px[SIZE - 1 - y][x] = b          # the mirrored cap band
    return px


def write_tga(path, colours=None):
    """an uncompressed 32-bit TGA, bottom-up rows (descriptor 0x08: the header UnrealEd accepted for the old Pal.tga;
    RLE is rejected with 'Bad image format'). The layout is row-symmetric, so the origin flag cannot matter."""
    px = image(colours)
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, SIZE, SIZE, 32, 0x08)
    body = bytearray()
    for row in reversed(px):
        for r, g, b, a in row:
            body += bytes((b, g, r, a))
    with open(path, "wb") as f:
        f.write(hdr + bytes(body) + b"\0" * 8 + b"TRUEVISION-XFILE.\0")
    return path
