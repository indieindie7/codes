"""Reading and writing Unreal Engine 2 T3D maps (UnrealEd's text map format), without Blender.

A map is a list of actors. Each actor keeps its original text, so whatever this module does
not understand (triggers, AI, scripted sequences) goes back out unchanged; only the lines it
was told to change are rewritten.

Unreal coordinates are left-handed (X forward, Y right, Z up); Blender's are right-handed.
`to_blender` / `from_blender` mirror Y and scale. Mirroring reverses polygon winding, so
polygons are reversed both ways too (see `Poly`).
"""

import math
import re

# ---- small vector maths (3-tuples, 3x3 row-major lists) ------------------------------------

def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def normalize(a):
    l = length(a)
    return mul(a, 1 / l) if l > 0 else a

def mat_vec(m, v):
    return tuple(m[r][0] * v[0] + m[r][1] * v[1] + m[r][2] * v[2] for r in range(3))

def mat_mul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]

def transpose(m):
    return [[m[c][r] for c in range(3)] for r in range(3)]

def inverse(m):
    c = [[m[(r + 1) % 3][(k + 1) % 3] * m[(r + 2) % 3][(k + 2) % 3] - m[(r + 1) % 3][(k + 2) % 3] * m[(r + 2) % 3][(k + 1) % 3]
          for r in range(3)] for k in range(3)]
    det = sum(m[0][k] * c[k][0] for k in range(3))
    return [[c[r][k] / det for k in range(3)] for r in range(3)]

def diag(x, y, z):
    return [[x, 0, 0], [0, y, 0], [0, 0, z]]

# ---- Unreal rotations (Pitch, Yaw, Roll in 65536ths of a turn) -----------------------------

URU = 65536 / (2 * math.pi)   # Unreal rotation units per radian

def rotator_matrix(pitch, yaw, roll):
    """The 3x3 matrix (columns = the rotated X, Y, Z axes) of an Unreal rotator."""
    p, y, r = pitch / URU, yaw / URU, roll / URU
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    x_axis = (cp * cy, cp * sy, sp)
    y_axis = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    z_axis = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return transpose([list(x_axis), list(y_axis), list(z_axis)])

def matrix_rotator(m):
    """Inverse of rotator_matrix, for a pure rotation (Pitch, Yaw, Roll), rounded to integers."""
    x_axis = (m[0][0], m[1][0], m[2][0])
    y_axis = (m[0][1], m[1][1], m[2][1])
    z_axis = (m[0][2], m[1][2], m[2][2])
    pitch = math.atan2(x_axis[2], math.hypot(x_axis[0], x_axis[1]))
    yaw = math.atan2(x_axis[1], x_axis[0])
    # roll: where the rotated Y axis went, measured in the plane the pitch and yaw leave it in
    base = rotator_matrix(pitch * URU, yaw * URU, 0)
    by = (base[0][1], base[1][1], base[2][1])
    bz = (base[0][2], base[1][2], base[2][2])
    roll = math.atan2(-dot(y_axis, bz), dot(y_axis, by))
    del z_axis
    return tuple(int(round(a * URU)) for a in (pitch, yaw, roll))

# ---- Unreal <-> Blender coordinates --------------------------------------------------------

MIRROR = diag(1, -1, 1)

def to_blender(p, scale):
    return (p[0] * scale, -p[1] * scale, p[2] * scale)

def from_blender(p, scale):
    return (p[0] / scale, -p[1] / scale, p[2] / scale)

def gradient_to_blender(g, scale):
    """A texture axis (texels per unit, a gradient) from Unreal to Blender units."""
    return (g[0] / scale, -g[1] / scale, g[2] / scale)

def gradient_from_blender(g, scale):
    return (g[0] * scale, -g[1] * scale, g[2] * scale)

def rotation_to_blender(m):
    return mat_mul(mat_mul(MIRROR, m), MIRROR)

rotation_from_blender = rotation_to_blender   # mirroring is its own inverse

# ---- parsing values -------------------------------------------------------------------------

_NUM = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'

def parse_struct(text):
    """'(X=1.0,Y=2,Z=-3)' -> {'X': '1.0', ...} (one level; nested structs kept as text)."""
    text = text.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]
    out, depth, key, cur = {}, 0, None, ''
    for ch in text + ',':
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == '=' and depth == 0 and key is None:
            key, cur = cur.strip(), ''
        elif ch == ',' and depth == 0:
            if key is not None:
                out[key] = cur.strip()
            key, cur = None, ''
        else:
            cur += ch
    return out

def parse_vector(text, default=(0.0, 0.0, 0.0)):
    if text is None:
        return default
    s = parse_struct(text)
    return tuple(float(s.get(k, d)) for k, d in zip('XYZ', default))

def parse_rotator(text):
    if text is None:
        return (0, 0, 0)
    s = parse_struct(text)
    return tuple(int(float(s.get(k, 0))) for k in ('Pitch', 'Yaw', 'Roll'))

def parse_scale(text):
    """MainScale/PostScale: (Scale=(X=..),SheerAxis=..,SheerRate=..) -> (scale vector, sheer rate)."""
    if text is None:
        return (1.0, 1.0, 1.0), 0.0
    s = parse_struct(text)
    return parse_vector(s.get('Scale'), (1.0, 1.0, 1.0)), float(s.get('SheerRate', 0) or 0)

def clean(v, places=3):
    """v rounded (coordinates come back from Blender's 32-bit floats as -10240.000153), and
    never -0."""
    v = round(v, places)
    return 0.0 if v == 0 else v

def fmt_float(v):
    return '%+013.6f' % (0.0 if abs(v) < 5e-7 else v)

def fmt_vec_line(v):
    return ','.join(fmt_float(c) for c in v)

def fmt_vector(v):
    """As UnrealEd writes a vector property: six decimals, zero components left out."""
    parts = ['%s=%.6f' % (k, c) for k, c in zip('XYZ', v) if abs(c) >= 5e-7]
    return '(' + ','.join(parts or ['X=0.000000']) + ')'

def tex_coords(poly):
    """Texture coordinates at each vertex: what an alignment means, whatever its origin."""
    return [dot(sub(v, poly.origin), poly.texture_u) + poly.pan[0] for v in poly.verts] + \
           [dot(sub(v, poly.origin), poly.texture_v) + poly.pan[1] for v in poly.verts]

def same_polys(a, b, eps=0.01):
    """Two brushes' polygons (world coordinates) describe the same faces, textures and texture
    alignment, within eps units (texels for the alignment)."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if (x.texture or '') != (y.texture or '') or len(x.verts) != len(y.verts):
            return False
        if any(abs(c - d) > eps for u, v in zip(x.verts, y.verts) for c, d in zip(u, v)):
            return False
        if any(abs(c - d) > eps for c, d in zip(tex_coords(x), tex_coords(y))):
            return False
    return True

def fmt_rotator(r):
    return '(Pitch=%d,Yaw=%d,Roll=%d)' % r

# ---- map structure --------------------------------------------------------------------------

class Poly:
    """One brush polygon, in Unreal coordinates (vertex order as in the file)."""
    def __init__(self):
        self.header = {}          # Begin Polygon attributes: Texture=, Flags=, Item=, Link=
        self.origin = (0.0, 0.0, 0.0)
        self.normal = (0.0, 0.0, 0.0)
        self.texture_u = (0.0, 0.0, 0.0)
        self.texture_v = (0.0, 0.0, 0.0)
        self.pan = (0, 0)
        self.verts = []

    @property
    def texture(self):
        return self.header.get('Texture', '')

    @property
    def flags(self):
        try:
            return int(self.header.get('Flags', 0))
        except ValueError:
            return 0

    def computed_normal(self):
        """Newell's method: same direction as Unreal's (v1 - v0) x (v2 - v0), robust to bad vertices."""
        n = (0.0, 0.0, 0.0)
        for i, a in enumerate(self.verts):
            b = self.verts[(i + 1) % len(self.verts)]
            n = add(n, ((a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])))
        return normalize(n)

    def to_lines(self, indent):
        head = 'Begin Polygon'
        for k in ('Item', 'Texture', 'Flags', 'Link'):
            if k in self.header and self.header[k] != '':
                head += ' %s=%s' % (k, self.header[k])
        out = [indent + head]
        out.append(indent + '   Origin   ' + fmt_vec_line(self.origin))
        out.append(indent + '   Normal   ' + fmt_vec_line(self.normal))
        out.append(indent + '   TextureU ' + fmt_vec_line(self.texture_u))
        out.append(indent + '   TextureV ' + fmt_vec_line(self.texture_v))
        if self.pan != (0, 0):
            out.append(indent + '   Pan      U=%d V=%d' % self.pan)
        for v in self.verts:
            out.append(indent + '   Vertex   ' + fmt_vec_line(v))
        out.append(indent + 'End Polygon')
        return out


class Actor:
    def __init__(self, cls, name, lines):
        self.cls = cls
        self.name = name
        self.lines = lines        # the whole block, Begin Actor ... End Actor
        self.props = {}           # top-level Key=Value lines (first occurrence)
        self.polys = None         # brush polygons (Brush, Volume, ...) or None
        self._parse()

    def _parse(self):
        depth = 0
        poly = None
        for line in self.lines[1:-1]:
            t = line.strip()
            low = t.lower()
            if low.startswith('begin '):
                depth += 1
                if low.startswith('begin polylist'):
                    self.polys = []
                elif low.startswith('begin polygon'):
                    poly = Poly()
                    for k, v in re.findall(r'(\w+)=(\S+)', t[len('begin polygon'):]):
                        poly.header[k] = v
                continue
            if low.startswith('end '):
                depth -= 1
                if low.startswith('end polygon') and poly is not None:
                    self.polys.append(poly)
                    poly = None
                continue
            if poly is not None:
                parts = t.split(None, 1)
                if not parts:
                    continue
                key = parts[0].lower()
                rest = parts[1] if len(parts) > 1 else ''
                if key in ('origin', 'normal', 'textureu', 'texturev', 'vertex'):
                    vec = tuple(float(x) for x in re.findall(_NUM, rest)[:3])
                    if key == 'origin': poly.origin = vec
                    elif key == 'normal': poly.normal = vec
                    elif key == 'textureu': poly.texture_u = vec
                    elif key == 'texturev': poly.texture_v = vec
                    else: poly.verts.append(vec)
                elif key == 'pan':
                    m = dict(re.findall(r'([UV])=(' + _NUM + ')', rest))
                    poly.pan = (int(float(m.get('U', 0))), int(float(m.get('V', 0))))
                continue
            if depth == 0 and '=' in t:
                k, v = t.split('=', 1)
                self.props.setdefault(k.strip(), v.strip())

    # -- what the importer needs --
    @property
    def location(self):
        return parse_vector(self.props.get('Location'))

    @property
    def rotation(self):
        return parse_rotator(self.props.get('Rotation'))

    def brush_matrix(self):
        """Linear part of brush-to-world: PostScale * Rotation * MainScale (sheer ignored)."""
        main, _ = parse_scale(self.props.get('MainScale'))
        post, _ = parse_scale(self.props.get('PostScale'))
        return mat_mul(mat_mul(diag(*post), rotator_matrix(*self.rotation)), diag(*main))

    def sheered(self):
        return any(parse_scale(self.props.get(k))[1] != 0 for k in ('MainScale', 'PostScale'))

    def world_polys(self):
        """The brush's polygons in world (Unreal) coordinates: v -> Location + M (v - PrePivot);
        texture axes and normals as gradients (inverse transpose)."""
        m = self.brush_matrix()
        g = transpose(inverse(m))
        loc = self.location
        pivot = parse_vector(self.props.get('PrePivot'))
        out = []
        for p in self.polys or []:
            q = Poly()
            q.header = dict(p.header)
            q.origin = add(loc, mat_vec(m, sub(p.origin, pivot)))
            q.normal = normalize(mat_vec(g, p.normal))
            q.texture_u = mat_vec(g, p.texture_u)
            q.texture_v = mat_vec(g, p.texture_v)
            q.pan = p.pan
            q.verts = [add(loc, mat_vec(m, sub(v, pivot))) for v in p.verts]
            out.append(q)
        return out

    # -- writing --
    def to_text(self, props=None, polys=None, drop=()):
        """The actor block with `props` lines replaced (or added), `drop` keys removed, and the
        brush's PolyList replaced by `polys` when given."""
        props = dict(props or {})
        done = set()
        out = []
        depth = 0
        skip_polylist = False
        for i, line in enumerate(self.lines):
            t = line.strip()
            low = t.lower()
            indent = line[:len(line) - len(line.lstrip())]
            if i == 0 or i == len(self.lines) - 1:
                if i == len(self.lines) - 1:
                    inner = indent + '    '
                    for k, v in props.items():
                        if k not in done:
                            out.append('%s%s=%s' % (inner, k, v))
                out.append(line)
                continue
            if skip_polylist:
                if low.startswith('end polylist'):
                    skip_polylist = False
                    out.append(line)
                continue
            if low.startswith('begin polylist') and polys is not None:
                out.append(line)
                for p in polys:
                    out.extend(p.to_lines(indent + '   '))
                skip_polylist = True
                continue
            if low.startswith('begin '):
                depth += 1
            elif low.startswith('end '):
                depth -= 1
            elif depth == 0 and '=' in t:
                k = t.split('=', 1)[0].strip()
                if k in drop:
                    continue
                if k in props:
                    if k not in done:
                        out.append('%s%s=%s' % (indent, k, props[k]))
                        done.add(k)
                    continue
            out.append(line)
        return out


class Map:
    def __init__(self):
        self.head = []            # lines before the first actor (Begin Map ...)
        self.actors = []
        self.tail = []            # lines after the last actor (End Map, surfaces ...)

    def to_text(self, blocks):
        lines = list(self.head)
        for b in blocks:
            lines.extend(b)
        lines.extend(self.tail)
        return '\r\n'.join(lines) + '\r\n'


def parse(text):
    m = Map()
    lines = text.splitlines()
    i = 0
    seen_actor = False
    while i < len(lines):
        t = lines[i].strip()
        if t.lower().startswith('begin actor'):
            seen_actor = True
            depth, j = 0, i
            while j < len(lines):
                lt = lines[j].strip().lower()
                if lt.startswith('begin '):
                    depth += 1
                elif lt.startswith('end '):
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = lines[i:j + 1]
            attrs = dict(re.findall(r'(\w+)=(\S+)', t))
            m.actors.append(Actor(attrs.get('Class', ''), attrs.get('Name', ''), block))
            i = j + 1
            continue
        (m.tail if seen_actor else m.head).append(lines[i])
        i += 1
    return m


def read(path):
    with open(path, 'rb') as f:
        data = f.read()
    for enc in ('utf-8-sig', 'utf-16', 'latin-1'):
        try:
            return parse(data.decode(enc))
        except UnicodeDecodeError:
            continue
    raise ValueError('could not decode ' + path)
