"""Region masks in a character skin's UV space, for the destructible armour's exposed flesh
(ModArmor phase 3): every face of the mesh belongs to the plate of its dominant bone (head,
torso, left arm, right arm, left leg, right leg); the faces of a region are rasterised in
UV space into one mask texture per region, white with the region in the alpha (dilated a
little over the seams). ModArmor blends the flesh texture over the skin through the mask
of each broken plate (Combiner, CO_AlphaBlend_With_Mask).

    py tools/make_armor_masks.py <mesh.psk> <set name> [size 512]
    e.g. py tools/make_armor_masks.py %USERPROFILE%\\Documents\\AdventRising_meshes\\seekerinfantry.psk seekerinfantry

Writes AdventMod/Textures/armor_<set>_<region>.tga (bottom-up like all our TGAs) and prints
the #exec lines for ModArmorTextures.uc. Uses GibSplit's psk reader.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "python", "GibSplit"))
import gibsplit  # noqa: E402

REGIONS = ["head", "torso", "l_arm", "r_arm", "l_leg", "r_leg"]
# a bone's region: the first ancestor (itself included) whose lower-cased name starts with one of these
ROOTS = [
    ("head", 0), ("neck", 0), ("jaw", 0),
    ("leftarm", 2), ("leftforearm", 2), ("lefthand", 2), ("leftshoulder", 2),
    ("rightarm", 3), ("rightforearm", 3), ("righthand", 3), ("rightshoulder", 3), ("prop", 3),
    ("leftupleg", 4), ("leftleg", 4), ("leftfoot", 4), ("lefttoes", 4), ("leftfront", 4),
    ("rightupleg", 5), ("rightleg", 5), ("rightfoot", 5), ("righttoes", 5), ("rightfront", 5),
    ("hips", 1), ("spine", 1),
]


def region_of(bones, i):
    while True:
        n = bones[i][0].lower()
        for prefix, r in ROOTS:
            if n.startswith(prefix):
                return r
        p = bones[i][1]
        if p == i or p < 0:
            return 1
        i = p


def write_tga(path, im):
    w, h = im.size
    px = im.load()
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            a = px[x, y]
            body += bytes((a, a, a, a))        # the region in colour AND alpha: the renderer may read either
    with open(path, "wb") as f:
        f.write(hdr + body)


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    psk, setname = sys.argv[1], sys.argv[2]
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    W, H = size, size // 2 if setname.startswith("seeker") else size
    pts, wedges, faces, mats, bones, weights = gibsplit.read_psk(psk)
    # dominant bone per point
    best = {}
    for w, p, b in weights:
        if p not in best or w > best[p][0]:
            best[p] = (w, b)
    preg = {p: region_of(bones, b) for p, (w, b) in best.items()}
    masks = [Image.new("L", (W, H), 0) for _ in REGIONS]
    draws = [ImageDraw.Draw(m) for m in masks]
    counts = [0] * 6
    for w0, w1, w2, m in faces:
        ws = [wedges[w0], wedges[w1], wedges[w2]]
        regs = [preg.get(wd[0], 1) for wd in ws]
        r = max(set(regs), key=regs.count)
        counts[r] += 1
        poly = [(((wd[1] % 1.0) * W), ((wd[2] % 1.0) * H)) for wd in ws]
        draws[r].polygon(poly, fill=255, outline=255)
    out = os.path.join(HERE, "..", "AdventMod", "Textures")
    lines = []
    for r, name in enumerate(REGIONS):
        m = masks[r].filter(ImageFilter.MaxFilter(5))      # 2 px over the seams
        fn = "armor_%s_%s.tga" % (setname, name)
        write_tga(os.path.join(out, fn), m)
        cover = sum(1 for v in m.getdata() if v) / float(W * H)
        print("%-8s %5d faces, %4.1f%% of the sheet -> %s" % (name, counts[r], 100 * cover, fn))
        lines.append("#exec TEXTURE IMPORT NAME=Armor_%s_%s FILE=Textures\\%s GROUP=Armor MIPS=1 ALPHA=1" % (setname, name, fn))
    # the combined masks: one texture per set of broken plates, so the exposure is a single
    # Combiner stage (nested combiners made the Seeker a flat colour in game). Left and right
    # limbs share texels on these meshes, so arms and legs count as one plate each here:
    # bits 1 head, 2 torso, 4 arms, 8 legs -> 15 combinations at half size.
    from PIL import ImageChops
    group = [masks[0], masks[1], ImageChops.lighter(masks[2], masks[3]), ImageChops.lighter(masks[4], masks[5])]
    group = [g.filter(ImageFilter.MaxFilter(5)).resize((W // 2, H // 2), Image.BILINEAR) for g in group]
    combos = []
    for bits in range(1, 16):
        m = Image.new("L", (W // 2, H // 2), 0)
        for k in range(4):
            if bits & (1 << k):
                m = ImageChops.lighter(m, group[k])
        fn = "armor_%s_c%02d.tga" % (setname, bits)
        write_tga(os.path.join(out, fn), m)
        combos.append("#exec TEXTURE IMPORT NAME=Armor_%s_c%02d FILE=Textures\\%s GROUP=Armor MIPS=1 ALPHA=1" % (setname, bits, fn))
    # the same combinations with the flesh baked in: colour = the meat tile where the region
    # is, alpha = the region. One texture serves as Material2 and Mask (fewer stages), should
    # the renderer not take a separate mask.
    meat_path = os.path.join(out, "alien_meat.tga" if setname.startswith("seeker") else "meat.tga")
    meat = Image.open(meat_path).convert("RGB")
    tile = Image.new("RGB", (W // 2, H // 2))
    for y in range(0, H // 2, meat.size[1]):
        for x in range(0, W // 2, meat.size[0]):
            tile.paste(meat, (x, y))
    for bits in range(1, 16):
        m = Image.new("L", (W // 2, H // 2), 0)
        for k in range(4):
            if bits & (1 << k):
                m = ImageChops.lighter(m, group[k])
        rgba = Image.merge("RGBA", (ImageChops.multiply(tile.getchannel("R"), m), ImageChops.multiply(tile.getchannel("G"), m), ImageChops.multiply(tile.getchannel("B"), m), m))
        fn = "armor_%s_m%02d.tga" % (setname, bits)
        write_tga_rgba(os.path.join(out, fn), rgba)
        combos.append("#exec TEXTURE IMPORT NAME=Armor_%s_m%02d FILE=Textures\\%s GROUP=Armor MIPS=1 ALPHA=1" % (setname, bits, fn))
    print("\n".join(lines))
    print("\n".join(combos))


def write_tga_rgba(path, im):
    w, h = im.size
    px = im.load()
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            body += bytes((b, g, r, a))
    with open(path, "wb") as f:
        f.write(hdr + body)


if __name__ == "__main__":
    main()
