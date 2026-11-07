"""3DDFA_V2 (BFM 3D face fit) on a manual face box -> dense mesh + 68 landmarks + yaw/pitch/roll.
Usage: py -3.13 ddfa_run.py <img> <out.png> x0,y0,x1,y1   (box = face, brow to chin)"""
import sys, os, numpy as np, cv2, yaml
R = os.path.abspath(os.environ.get('DDFA_DIR', '3ddfa'))  # clone of https://github.com/cleardusk/3DDFA_V2
sys.path.insert(0, R); os.chdir(R)
from TDDFA import TDDFA
from utils.pose import calc_pose
src, out, box = sys.argv[1], sys.argv[2], [float(v) for v in sys.argv[3].split(',')]
img = cv2.imread(src)
UP = max(1, int(round(400 / (box[2] - box[0]))))           # small faces: upscale so the drawing is readable
img = cv2.resize(img, None, fx=UP, fy=UP, interpolation=cv2.INTER_LANCZOS4); box = [v * UP for v in box]
cfg = yaml.safe_load(open('configs/mb1_120x120.yml'))
t = TDDFA(gpu_mode=True, **cfg)
param, roi = t(img, [box + [1.0]])
dense = t.recon_vers(param, roi, dense_flag=True)[0]       # (3, ~38k)
sp = t.recon_vers(param, roi, dense_flag=False)[0]         # (3, 68)
P, pose = calc_pose(param[0])                              # yaw, pitch, roll (deg)
vis = img.copy()
for x, y in dense[:2].T[::6]: cv2.circle(vis, (int(x), int(y)), 1, (255, 200, 60), -1)
for x, y in sp[:2].T: cv2.circle(vis, (int(x), int(y)), 3, (0, 0, 255), -1)
x0, y0, x1, y1 = [int(v) for v in box]
pad = int((x1 - x0) * 0.6); vis = vis[max(0, y0 - pad):y1 + pad // 2, max(0, x0 - pad):x1 + pad]
txt = f'3DDFA_V2 yaw {pose[0]:+.0f} pitch {pose[1]:+.0f} roll {pose[2]:+.0f}'
cv2.putText(vis, txt, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
cv2.imwrite(out, vis); print(txt)
