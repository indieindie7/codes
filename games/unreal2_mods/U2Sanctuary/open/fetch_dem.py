r"""Fetch a small window of Copernicus GLO-30 elevation (ESA, free under the Copernicus DEM licence: credit
"Copernicus DEM GLO-30, (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under
COPERNICUS by the European Union and ESA") from the public AWS bucket, reading ONLY the internal 1024x1024 blocks
that cover the window (HTTP range requests into the Cloud Optimised GeoTIFF; no GDAL/rasterio here).

    py fetch_dem.py LAT_N LAT_S LON_W LON_E out.npy        (decimal degrees, south and west negative)

The user OK'd the download on 2026-10-08 (Carajas, Brazil: the Sanctuary Open terrain reference).
"""
import struct, sys, zlib

import numpy as np
import requests

BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"


def tile_name(lat, lon):
    la = "%s%02d_00" % ("S" if lat < 0 else "N", abs(int(np.floor(lat))) if lat < 0 else int(np.floor(lat)))
    lo = "%s%03d_00" % ("W" if lon < 0 else "E", abs(int(np.floor(lon))) if lon < 0 else int(np.floor(lon)))
    n = "Copernicus_DSM_COG_10_%s_%s_DEM" % (la, lo)
    return "%s/%s/%s.tif" % (BUCKET, n, n)


def get(url, a, b):
    r = requests.get(url, headers={"Range": "bytes=%d-%d" % (a, b - 1)}, timeout=60)
    r.raise_for_status()
    return r.content


def ifd(url):
    head = get(url, 0, 65536)
    assert head[:2] == b"II" and struct.unpack_from("<H", head, 2)[0] == 42, "not a little-endian classic TIFF"
    off = struct.unpack_from("<I", head, 4)[0]
    n = struct.unpack_from("<H", head, off)[0]
    tags = {}
    for k in range(n):
        tag, typ, cnt, val = struct.unpack_from("<HHII", head, off + 2 + 12 * k)
        size = {3: 2, 4: 4, 12: 8, 16: 8}.get(typ, 1) * cnt
        fmt = {3: "H", 4: "I", 12: "d", 16: "Q"}.get(typ)
        if size <= 4 and fmt in ("H", "I"):
            v = struct.unpack_from("<%d%s" % (cnt, fmt), head, off + 2 + 12 * k + 8)
        elif fmt:
            raw = head[val:val + size] if val + size <= len(head) else get(url, val, val + size)
            v = struct.unpack_from("<%d%s" % (cnt, fmt), raw, 0)
        else:
            v = (val,)
        tags[tag] = v
    return tags


def unpredict3(raw, tw, th):
    """TIFF floating-point predictor 3: rows are byte-shuffled (MSB plane first) and horizontally differenced"""
    b = np.frombuffer(raw, dtype=np.uint8).reshape(th, 4 * tw).copy()
    b = np.cumsum(b, axis=1, dtype=np.uint8)
    b = b.reshape(th, 4, tw).transpose(0, 2, 1)[:, :, ::-1]      # big-endian planes -> little-endian bytes
    return np.ascontiguousarray(b).view("<f4").reshape(th, tw)


def fetch(lat_n, lat_s, lon_w, lon_e):
    url = tile_name(lat_s + 1e-6, lon_w + 1e-6)
    t = ifd(url)
    W, H = t[256][0], t[257][0]
    tw, th = t[322][0], t[323][0]
    offs, cnts = t[324], t[325]
    pred = t.get(317, (1,))[0]
    lat0, lon0 = np.floor(lat_s + 1e-6) + 1, np.floor(lon_w + 1e-6)          # the tile's north-west corner
    r0, r1 = int((lat0 - lat_n) * H), int(np.ceil((lat0 - lat_s) * H))
    c0, c1 = int((lon_w - lon0) * W), int(np.ceil((lon_e - lon0) * W))
    across = (W + tw - 1) // tw
    out = np.zeros((r1 - r0, c1 - c0), np.float32)
    got = 0
    for tr in range(r0 // th, (r1 - 1) // th + 1):
        for tc in range(c0 // tw, (c1 - 1) // tw + 1):
            k = tr * across + tc
            raw = zlib.decompress(get(url, offs[k], offs[k] + cnts[k]))
            got += cnts[k]
            blk = unpredict3(raw, tw, th) if pred == 3 else np.frombuffer(raw, "<f4").reshape(th, tw)
            ra, rb = max(r0, tr * th), min(r1, (tr + 1) * th)
            ca, cb = max(c0, tc * tw), min(c1, (tc + 1) * tw)
            out[ra - r0:rb - r0, ca - c0:cb - c0] = blk[ra - tr * th:rb - tr * th, ca - tc * tw:cb - tc * tw]
    return out, url, got


if __name__ == "__main__":
    a = [float(v) for v in sys.argv[1:5]]
    Z, url, got = fetch(*a)
    np.save(sys.argv[5], Z)
    print("%s: %dx%d, %.0f..%.0f m, %.1f MB fetched" % (url.rsplit("/", 1)[-1], Z.shape[1], Z.shape[0], Z.min(), Z.max(), got / 1e6))
