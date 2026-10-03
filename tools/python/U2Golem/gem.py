"""Reader for Unreal II Golem mesh files (.gem, "LGEM" v1) - enough to get a character's
skinned mesh out: bones, points (model-space rest positions + weights), normals, render
vertices, UVs, triangles with material IDs. Layout decoded from PlayerGame.gem (2026-10-03).

File: header (magic, version, file size, ?, then (count, offset) pairs: strings, objects,
?, ?, chunk table, attributes); an object table of 0x40-byte records (name, class, ..., data
size, data offset ...); a string table of NUL-separated names.
"""
import struct


class Gem:
    def __init__(self, path):
        d = self.d = open(path, "rb").read()
        h = struct.unpack_from("<14I", d, 0)
        assert h[0] == 0x4D45474C, "not an LGEM file"
        nstr, ostr = h[4], h[5]
        nobj, oobj = h[6], h[7]
        nattr, oattr = h[12], h[13]
        self.strings = [s.decode("latin1") for s in d[ostr:h[2]].split(b"\0")]
        self.objects = {}
        for i in range(nobj):
            r = struct.unpack_from("<16I", d, oobj + 0x40 * i)
            self.objects[self.strings[r[1]]] = dict(name=self.strings[r[0]], size=r[4], offset=r[5], raw=r)
        self.attrs = []
        for i in range(nattr):
            n, v, t, f = struct.unpack_from("<4I", d, oattr + 16 * i)
            self.attrs.append((self.strings[n], v, t & 0xFFFF))

    def attr(self, name, nth=0):
        hits = [v for n, v, t in self.attrs if n == name]
        return hits[nth]

    def block(self, cls):
        o = self.objects[cls]
        return self.d[o["offset"]:o["offset"] + o["size"]]

    # ---- the skinned mesh --------------------------------------------------------------
    def bone_points(self):
        nb, npt = self.attr("BoneCount", 1), self.attr("PointCount", 1)
        nw = self.attr("WeightCount")
        b = self.block("GemBonePoints")
        names = [self.strings[i] for i in struct.unpack_from("<%dI" % nb, b, 0)]
        o = 4 * nb
        pts, spans = [], []
        for i in range(npt):
            x, y, z, packed = struct.unpack_from("<3fI", b, o + 16 * i)
            pts.append((x, y, z))
            spans.append((packed & 0xFFFF, packed >> 16))      # weight count, first weight
        o += 16 * npt
        weights = [struct.unpack_from("<If", b, o + 8 * i) for i in range(nw)]
        o += 8 * nw
        normals = [struct.unpack_from("<3f", b, o + 16 * i) for i in range(npt)]
        return names, pts, spans, weights, normals

    def bones(self):
        """[(name, parent, local position, local quaternion xyzw)], Golem's own convention"""
        nb = self.attr("BoneCount", 1)
        b = self.block("GemBoneHierarchy")
        out = []
        for i in range(nb):
            n, p = struct.unpack_from("<2i", b, 88 * i)
            f = struct.unpack_from("<7f", b, 88 * i + 8)
            out.append((self.strings[n], p, f[:3], f[3:7]))
        return out

    def vertices(self):
        """render vertices: (point, normal, uv) indices"""
        n = self.attr("VertexCount")
        b = self.block("GemVertices")
        return [struct.unpack_from("<3H", b, 8 * i) for i in range(n)]

    def uvs(self):
        n = self.attr("TexUVCount", 1)
        b = self.block("GemTexUVFrames")
        return [struct.unpack_from("<2f", b, 8 * i) for i in range(n)]

    def triangles(self):
        """[(a, b, c, material)] over render vertices; the list follows an 82-byte header"""
        b = self.block("GemTriangles")
        n = struct.unpack_from("<I", b, 0)[0]
        return [struct.unpack_from("<4H", b, 82 + 8 * i) for i in range(n)]

    def materials(self):
        """material names in slot order (MaterialName attributes point into the string table)"""
        return [self.strings[v] for n, v, t in self.attrs if n == "MaterialName"]
