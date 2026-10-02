"""Writes the colour-grading LUTs for the U2Shaders post pass (lut= in U2Shaders.ini):
32 slices of 32x32 side by side (1024x32, 24-bit BMP, row 0 at the top = green 0,
x inside a slice = red, slice = blue).
  lut_neutral.bmp - identity (grading off; for checking the LUT path)
  lut_advent.bmp  - a subtle look: soft S-curve, highlights a touch warm, shadows a touch
                    cool (split toning), saturation slightly up in the mids.
Run: python make_luts.py  (writes next to this script)."""
import os, struct

N = 32

def neutral(r, g, b):
    return r, g, b

def smooth(x):                      # gentle S-curve, keeps 0 and 1
    return x + 0.12 * (x - 0.5) * (1 - abs(2 * x - 1)) * 2 * 0.5

def advent(r, g, b):
    r, g, b = smooth(r), smooth(g), smooth(b)
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    hi = max(0.0, luma - 0.5) * 2    # 0..1 in the highlights
    lo = max(0.0, 0.5 - luma) * 2    # 0..1 in the shadows
    r += 0.025 * hi - 0.010 * lo
    g += 0.008 * hi + 0.000 * lo
    b += -0.020 * hi + 0.020 * lo
    mid = 1 - abs(2 * luma - 1)      # saturation +8 % in the mids
    s = 1 + 0.08 * mid
    r, g, b = luma + (r - luma) * s, luma + (g - luma) * s, luma + (b - luma) * s
    return r, g, b

def write(name, fn):
    w, h = N * N, N
    rows = []
    for y in range(h):              # y = green, row 0 = top
        row = bytearray()
        for x in range(w):
            sl, xr = divmod(x, N)
            r, g, b = fn(xr / (N - 1), y / (N - 1), sl / (N - 1))
            row += bytes((int(round(min(max(c, 0), 1) * 255)) for c in (b, g, r)))
        rows.append(bytes(row))
    pad = (4 - (w * 3) % 4) % 4
    data = b''.join(r + b'\0' * pad for r in rows)          # top-down (negative height)
    hdr = struct.pack('<2sIHHI', b'BM', 54 + len(data), 0, 0, 54)
    info = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    open(path, 'wb').write(hdr + info + data)
    print('wrote', path, w, 'x', h)

write('lut_neutral.bmp', neutral)
write('lut_advent.bmp', advent)
