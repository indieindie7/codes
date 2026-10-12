# Simpler read of the depth pass (2026-10-11): walls are square to each other, so the two walls' depth slopes
# (per pixel, across x) multiply to 1 after the unknown depth scale k: k^2*gf*gs = 1 -> yaw phi = atan(k*gf).
# True lengths: front = px_f/cos(phi), side = px_s/sin(phi); heights straight from pixels. Units = F storey height.
import cv2, numpy as np, json
d = np.load("depth/depth_rel.npy"); H, W = d.shape
FRONT = [(95, 165), (145, 125), (148, 370), (95, 330)]
SIDE = [(160, 225), (262, 180), (262, 312), (160, 372)]
def slope(poly):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(poly, np.int32)], 1)
    ys, xs = np.nonzero(m); A = np.stack([xs, ys, np.ones_like(xs)], 1)
    return np.linalg.lstsq(A, d[ys, xs], rcond=None)[0][0]      # d change per pixel in x
gf, gs = slope(FRONT), slope(SIDE)
k = 1 / np.sqrt(abs(gf * gs)); phi = np.arctan(k * abs(gf))
P = json.load(open("depth/points.json"))
px = lambda a, b: abs(P[a][0] - P[b][0])
vy = lambda a, b: abs(P[a][1] - P[b][1])
Fh = (vy("midN", "botN") + vy("midL", "botL") + vy("midR", "botR")) / 3
m = {"front_width": px("midL", "midN") / np.cos(phi), "side_length": px("midN", "midR") / np.sin(phi),
     "F_height": Fh, "B_wall_height": (vy("eaveN", "midN") + vy("eaveL", "midL") + vy("eaveR", "midR")) / 3,
     "roof_rise": vy("peak", "eaveL"), "awning_height": vy("awnF_top", "botL") if False else vy("awnS_top", "awn_post"),
     "awning_depth": abs(P["awnS_top"][0] - P["midR"][0]) / np.cos(phi)}
r = {k_: round(float(v) / Fh, 3) for k_, v in m.items()}
r["awning_side_frac"] = 0.85
r["chimney_extra"] = round(1 + vy("peak", "chim") / (m["B_wall_height"] + m["roof_rise"]), 3)
print(f"slopes front {gf:+.4f} side {gs:+.4f} -> gable wall turned {np.degrees(phi):.1f} deg from the picture plane")
print(json.dumps(r))
json.dump({"phi_deg": float(np.degrees(phi)), "ratios_to_F_height": r}, open("depth/measure.json", "w"), indent=1)
