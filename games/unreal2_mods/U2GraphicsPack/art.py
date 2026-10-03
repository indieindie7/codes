# U2GraphicsPack Nexus thumbnail + screenshots from pilot shotp frames
from PIL import Image, ImageDraw, ImageFont
import os
R = r"C:\Users\john\Documents\github\codes\tools\python\U2Pilot\runs"
D = os.path.join(os.path.expanduser("~"), "Downloads")
def fr(run, n): return Image.open(os.path.join(R, run, "frames", "f%05d.bmp" % n)).convert("RGB")
p1, p3, p2 = "20261003-091705_pack_shots", "20261003-134143_pack_shots3", "20261003-091806_pack_shots2"
fp = "20261003-134250_shadow_fp"   # first person: a marine casting two soft shadows

def font(size, name="Bold Condensed"):
    f = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", size)
    try: f.set_variation_by_name(name)
    except Exception: pass
    return f

def band(img, y0, y1, a=150):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([0, y0, img.width, y1], fill=(0, 0, 0, a))
    return Image.alpha_composite(img.convert("RGBA"), ov)

def centred(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((1280 - w) / 2 + 2, y + 2), text, font=f, fill=(0, 0, 0))
    d.text(((1280 - w) / 2, y), text, font=f, fill=fill)

# thumbnail
t = fr(fp, 0).resize((1280, 720), Image.LANCZOS)
t = band(t, 30, 180); t = band(t, 640, 720, 170)
d = ImageDraw.Draw(t)
centred(d, 40, "UNREAL II GRAPHICS PACK", font(86), (255, 255, 255))
centred(d, 132, "soft shadows, post-processing, SMAA - no dgVoodoo needed", font(34, "SemiBold Condensed"), (215, 215, 215))
centred(d, 652, "SOFT SHADOWS  \u2022  BLOOM & COLOUR GRADE  \u2022  SMAA  \u2022  BORDERLESS", font(44), (255, 200, 60))
t.convert("RGB").save(os.path.join(D, "U2GraphicsPack-thumbnail.png"))

# screenshots (960x540 like the earlier pages)
fr(fp, 0).save(os.path.join(D, "U2GraphicsPack-screenshot1.png"))
a, b = fr(p1, 4), fr(p1, 5)
s = a.copy(); s.paste(b.crop((480, 0, 960, 540)), (480, 0))
s = band(s, 0, 44, 140); d = ImageDraw.Draw(s)
d.line([(480, 0), (480, 540)], fill=(255, 255, 255), width=2)
f = font(30)
d.text((20, 6), "POST-PROCESSING OFF", font=f, fill=(255, 255, 255))
d.text((960 - 20 - d.textlength("POST-PROCESSING ON", font=f), 6), "POST-PROCESSING ON", font=f, fill=(255, 200, 60))
s.convert("RGB").save(os.path.join(D, "U2GraphicsPack-screenshot2.png"))
fr(p2, 3).save(os.path.join(D, "U2GraphicsPack-screenshot3.png"))
fr(p1, 1).save(os.path.join(D, "U2GraphicsPack-screenshot4.png"))
fr(p3, 3).save(os.path.join(D, "U2GraphicsPack-screenshot5.png"))
print("ok")
