"""The Liandri palette, measured from the Hunyuan paint models (tools/hunyuan_palette.py, 2026-10-06):
bodies in near-black charcoal and dark steel (~55% of every texture), mid greys for trim and platforms
(~25%), a deep rust-red for accent panels (~10%), a dusty brown for dirt bands, light grey only on the
cooling towers' shells. Bright orange stays as the small accent (doors, stripes), glow for lit strips.

Eight colours exactly: glb_to_ase.py's Pal.tga has eight stripes. Values are LINEAR rgb (Blender's
Principled base colour); the sRGB they came from is in the comment.
"""

COLOURS = {
    "charcoal": (0.085, 0.078, 0.076),   # #4f4b4a  the bodies (lifted from the measured #3a3636: UE2 vertex light has no cavity, it went black)
    "steel":    (0.190, 0.180, 0.172),   # #777370 (lifted)  secondary walls, legs, machinery
    "grey":     (0.270, 0.260, 0.252),   # #8f8c89  trim, roof slabs, platforms, concrete
    "pale":     (0.540, 0.540, 0.520),   # #c2c2be  cooling-tower shells, the office
    "rustred":  (0.170, 0.030, 0.012),   # #702a18 (lifted)  accent panels, silos, the dead rig
    "brown":    (0.135, 0.090, 0.074),   # #665449 (lifted)  dirt bands, weathered panels
    "orange":   (0.480, 0.095, 0.015),   # #b85a22  doors, stripes, warning marks
    "glow":     (1.000, 0.450, 0.100),   # lit strips and lamps (emissive)
}

# the old names the first builders used -> the measured palette
ALIASES = {"concrete": "steel", "dark": "charcoal", "rust": "brown"}


def colour(name):
    return COLOURS[ALIASES.get(name, name)]
