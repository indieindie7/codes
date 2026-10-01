"""Read and write ActorX .psk (skinned mesh) and .psa (animation) files.

Both formats are a flat list of chunks: a 32-byte header (20-byte id, type flags,
record size, record count) followed by count * size bytes of records. Only the chunks
this tool changes are decoded; everything else is carried through byte for byte.
"""
import struct

BONE_PSK = struct.Struct("<64sIii" + "f" * 11)   # name, flags, children, parent, quat xyzw, pos xyz, length, size xyz
BONE_PSA = BONE_PSK                              # FNamedBoneBinary is the same record in both files
ANIMINFO = struct.Struct("<64s64siiiifffiii")     # name, group, bones, root include, compression, key quota, key reduction, track time, rate, start bone, first frame, frames
KEY = struct.Struct("<ffffffff")                  # pos xyz, quat xyzw, time


class Chunks:
    def __init__(self, path):
        self.path = path
        data = open(path, "rb").read()
        self.items = []                          # [id, type, size, count, bytes]
        o = 0
        while o + 32 <= len(data):
            cid = data[o:o + 20].split(b"\0")[0].decode("latin-1")
            typ, size, count = struct.unpack("<iii", data[o + 20:o + 32])
            o += 32
            self.items.append([cid, typ, size, count, data[o:o + size * count]])
            o += size * count

    def get(self, cid):
        for it in self.items:
            if it[0] == cid:
                return it
        raise KeyError(cid)

    def records(self, cid):
        _, _, size, count, raw = self.get(cid)
        return [raw[i * size:(i + 1) * size] for i in range(count)]

    def set_records(self, cid, recs):
        it = self.get(cid)
        it[3] = len(recs)
        it[4] = b"".join(recs)

    def save(self, path):
        with open(path, "wb") as f:
            for cid, typ, size, count, raw in self.items:
                f.write(cid.encode("latin-1").ljust(20, b"\0"))
                f.write(struct.pack("<iii", typ, size, count))
                f.write(raw)


def name_of(raw64):
    return raw64.split(b"\0")[0].decode("latin-1")


class Bone:
    def __init__(self, rec):
        v = BONE_PSK.unpack(rec)
        self.name = name_of(v[0])
        self.flags, self.children, self.parent = v[1], v[2], v[3]
        self.quat = list(v[4:8])
        self.pos = list(v[8:11])
        self.length = v[11]
        self.size = list(v[12:15])

    def pack(self):
        return BONE_PSK.pack(self.name.encode("latin-1").ljust(64, b"\0"), self.flags, self.children,
                             self.parent, *self.quat, *self.pos, self.length, *self.size)


class Mesh:
    """A .psk: points, bones and materials are editable; the rest is kept as is."""
    def __init__(self, path):
        self.c = Chunks(path)
        self.points = [list(struct.unpack("<fff", r)) for r in self.c.records("PNTS0000")]
        self.bones = [Bone(r) for r in self.c.records("REFSKELT")]
        self.materials = [name_of(r[:64]) for r in self.c.records("MATT0000")]
        self._mat_tail = [r[64:] for r in self.c.records("MATT0000")]

    def bounds(self):
        xs, ys, zs = zip(*self.points)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def scale(self, s):
        for p in self.points:
            p[0] *= s; p[1] *= s; p[2] *= s
        for b in self.bones:
            b.pos = [v * s for v in b.pos]
            b.length *= s
            b.size = [v * s for v in b.size]

    def add_bone(self, name, parent, pos, quat=(0.0, 0.0, 0.0, 1.0)):
        b = Bone(self.bones[parent].pack())
        b.name, b.parent, b.children = name, parent, 0
        b.pos, b.quat = list(pos), list(quat)
        self.bones[parent].children += 1
        self.bones.append(b)
        return len(self.bones) - 1

    def save(self, path):
        self.c.set_records("PNTS0000", [struct.pack("<fff", *p) for p in self.points])
        self.c.set_records("REFSKELT", [b.pack() for b in self.bones])
        self.c.set_records("MATT0000", [n.encode("latin-1").ljust(64, b"\0") + t
                                        for n, t in zip(self.materials, self._mat_tail)])
        self.c.save(path)


class Anims:
    """A .psa: bone names, sequences and keys (positions scaled with the mesh)."""
    def __init__(self, path):
        self.c = Chunks(path)
        self.bones = [Bone(r) for r in self.c.records("BONENAMES")]
        self.seqs = [ANIMINFO.unpack(r) for r in self.c.records("ANIMINFO")]
        self.keys = [list(KEY.unpack(r)) for r in self.c.records("ANIMKEYS")]

    def names(self):
        return [name_of(s[0]) for s in self.seqs]

    def scale(self, s):
        for b in self.bones:
            b.pos = [v * s for v in b.pos]
        for k in self.keys:
            k[0] *= s; k[1] *= s; k[2] *= s

    def save(self, path):
        self.c.set_records("BONENAMES", [b.pack() for b in self.bones])
        self.c.set_records("ANIMKEYS", [KEY.pack(*k) for k in self.keys])
        self.c.save(path)
