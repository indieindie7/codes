"""facecheck: MediaPipe FaceLandmarker (478 3D pts) -> Loomis head construction overlay.
Usage: py -3.13 facecheck.py <img> <out.png> [--box x0,y0,x1,y1] [--rot deg]
Draws: ball, side-plane cut (ear), brow line (equator), center line, nose-base + chin thirds, jaw. Prints yaw/pitch/roll.
Model: face_landmarker.task next to this file (float16, 3.7 MB). Tiny CPU model (allowed: helper-size)."""
import sys, os, numpy as np
from PIL import Image, ImageDraw
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

HERE = os.path.dirname(os.path.abspath(__file__))
def arg(n, d=None): return [float(v) for v in sys.argv[sys.argv.index(n) + 1].split(',')] if n in sys.argv else d
src, out = sys.argv[1], sys.argv[2]
img = Image.open(src).convert('RGB')
rot = arg('--rot')
if rot: img = img.rotate(rot[0], expand=True)
box = arg('--box', [0, 0, img.width, img.height])
crop = img.crop(tuple(int(v) for v in box))
S = 640 / max(crop.size); crop = crop.resize((int(crop.width * S), int(crop.height * S)), Image.LANCZOS)
W, H = crop.size
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(HERE, 'face_landmarker.task')), num_faces=1,
    min_face_detection_confidence=0.2, min_face_presence_confidence=0.2))
res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(np.asarray(crop))))
if not res.face_landmarks:
    print('NO FACE FOUND'); crop.save(out); sys.exit(2)
L = np.array([[p.x * W, p.y * H, p.z * W] for p in res.face_landmarks[0]])
u = lambda v: v / np.linalg.norm(v)
right = u(L[263] - L[33])                       # subject's left eye outer - right eye outer (image left->right if facing us)
up = L[10] - L[152]; up = u(up - right * (up @ right))
fwd = np.cross(right, up)
if fwd[2] > 0: fwd = -fwd                        # mediapipe: smaller z = nearer camera; face points toward -z
R = 0.5 * np.linalg.norm(L[234] - L[454]) * 1.02
brow = L[9]; c = brow - fwd * R * 0.92
im = crop.copy(); d = ImageDraw.Draw(im, 'RGBA')
for p in L: d.point((p[0], p[1]), fill=(255, 255, 255, 90))
def circ3(center, n1, n2, r, col, w=3, k=96):
    t = np.linspace(0, 2 * np.pi, k); pts = [center + n1 * r * np.cos(a) + n2 * r * np.sin(a) for a in t]
    for a, b in zip(pts[:-1], pts[1:]):
        vis = ((a + b) / 2 - c) @ np.array([0, 0, -1.0]) > -R * 0.05
        d.line([(a[0], a[1]), (b[0], b[1])], fill=col if vis else col[:3] + (70,), width=w if vis else 1)
RED, BLU, GRN, YEL, PNK = (255, 50, 50, 230), (60, 190, 255, 230), (80, 255, 120, 230), (255, 220, 0, 240), (255, 120, 200, 220)
d.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], outline=RED, width=3)        # ball silhouette (ortho)
circ3(c, fwd, right, R, GRN)                    # brow line = equator
circ3(c, fwd, up, R, BLU)                       # center line
cut = 0.68; rs = R * np.sqrt(1 - cut ** 2)
for s in (1, -1): circ3(c + right * R * cut * s, fwd, up, rs, YEL)   # side planes (ear sits here)
# thirds: hairline - brow - nose base - chin, measured along the center line
nb, chin = L[2], L[152]
unit3 = np.linalg.norm((nb - brow)[:2])
hair = brow + up * unit3  # Loomis hairline: one third above brow (mesh top lm10 is not the hairline)
for p, lab in [(hair, 'hair'), (brow, 'brow'), (nb, 'nose'), (chin, 'chin')]:
    a, b = p - right * R * 0.55, p + right * R * 0.55
    d.line([(a[0], a[1]), (b[0], b[1])], fill=PNK, width=2); d.text((b[0] + 4, b[1] - 6), lab, fill=PNK)
d.line([(nb[0], nb[1]), (L[0][0], L[0][1]), (chin[0], chin[1])], fill=BLU, width=3)  # center line on to chin
# jaw: side-cut bottom -> jaw corner -> chin
for s, jc in ((1, L[454]), (-1, L[234])):
    e = c + right * R * cut * s - up * rs
    j = L[397] if s > 0 else L[172]
    d.line([(e[0], e[1]), (j[0], j[1]), (chin[0], chin[1])], fill=RED, width=3)
yaw = np.degrees(np.arctan2(fwd[0], -fwd[2])); pitch = np.degrees(np.arcsin(np.clip(-fwd[1], -1, 1)))
roll = np.degrees(np.arctan2(right[1], right[0]))
thirds = [np.linalg.norm((brow - hair)[:2]), unit3, np.linalg.norm((chin - nb)[:2])]
eyes_at = (L[468][1] if len(L) > 468 else (L[33][1] + L[263][1]) / 2)
skull_top = c[1] - R
f_eye = (eyes_at - skull_top) / (chin[1] - skull_top)
txt = f'yaw {yaw:+.0f}  pitch {pitch:+.0f}  roll {roll:+.0f}   brow-nose : nose-chin = 1:{thirds[2]/unit3:.2f}   eyes at {f_eye:.2f} of head'
d.rectangle([0, 0, W, 18], fill=(0, 0, 0, 170)); d.text((4, 3), txt, fill=(255, 255, 255))
im.save(out); print(txt)
