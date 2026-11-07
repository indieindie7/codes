"""drawcheck: compare a drawing with its reference using the Sonar tools (NLF pose + SAM2.1 silhouette + 2D part map).

  ref   <ref_img> <out.npz> [--box x0,y0,x1,y1]          reference: NLF joints, SAM2 mask, part map (+ <out>_ref.png)
  over  <out.npz> <ref_img> <overdrawn_img> <out.png>    user's dark strokes drawn over the reference: align, classify, score
  paper <out.npz> <ref_img> <drawing_img> <out.png> [--box x0,y0,x1,y1]   separate drawing: NLF on it, compare angles/proportions

Units: H = head height ~ 2.5 * |head - neck| (NLF SMPL joints). Strokes: closed loop = part outline, open line = edge or limb axis
(user rule 11-06, Sonar). Run with py -3.13 on a free card (CUDA_VISIBLE_DEVICES=<idx>)."""
import os, sys, numpy as np, cv2, torch, torchvision  # torchvision registers nms for NLF
from PIL import Image, ImageDraw, ImageFont
NLF = os.environ.get('NLF_MODEL', 'models/nlf_l_multi_0.3.2.torchscript')  # https://github.com/isarandi/nlf
SAM = 'facebook/sam2.1-hiera-small'
# SMPL 24: 0 pel 1 hipL 2 hipR 3 sp1 4 kneeL 5 kneeR 6 sp2 7 ankL 8 ankR 9 sp3 10 footL 11 footR 12 neck 13 colL 14 colR 15 head
# 16 shL 17 shR 18 elL 19 elR 20 wrL 21 wrR 22 haL 23 haR   (L/R = the figure's own side)
PARTS = {'head': [(12, 15, 1.0)], 'chest': [(3, 6, 0), (6, 9, 0), (9, 12, 0), (9, 13, 0), (9, 14, 0), (13, 16, 0), (14, 17, 0)],
         'pelvis': [(0, 3, 0), (0, 1, 0), (0, 2, 0)],
         'upperarmL': [(16, 18, 0)], 'forearmL': [(18, 20, 0)], 'handL': [(20, 22, 1.0)],
         'upperarmR': [(17, 19, 0)], 'forearmR': [(19, 21, 0)], 'handR': [(21, 23, 1.0)],
         'thighL': [(1, 4, 0)], 'shinL': [(4, 7, 0)], 'footL': [(7, 10, 1.0)],
         'thighR': [(2, 5, 0)], 'shinR': [(5, 8, 0)], 'footR': [(8, 11, 1.0)]}
PN = list(PARTS)
PAL = np.array([[230, 90, 90], [90, 160, 230], [200, 200, 80], [240, 140, 40], [250, 190, 90], [255, 230, 150], [60, 200, 120], [120, 230, 160],
                [190, 255, 200], [170, 90, 220], [210, 140, 255], [235, 200, 255], [40, 170, 200], [90, 210, 240], [170, 240, 255]], np.uint8)
BONES = [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15), (9, 13), (13, 16), (9, 14), (14, 17), (16, 18), (18, 20), (20, 22), (17, 19), (19, 21), (21, 23),
         (0, 1), (1, 4), (4, 7), (7, 10), (0, 2), (2, 5), (5, 8), (8, 11)]

def arg(name, default=None):
    return [float(v) for v in sys.argv[sys.argv.index(name) + 1].split(',')] if name in sys.argv else default

def nlf(img, box=None, up=3):
    m = torch.jit.load(NLF).cuda().eval()
    if max(img.size) > 1500: up = 1  # 3x of a phone photo breaks NLF's box crop (seen 11-07)
    big = img.resize((img.width * up, img.height * up), Image.LANCZOS)
    x = torch.from_numpy(np.array(big)).permute(2, 0, 1)[None].cuda()
    if box is None: box = [img.width * .02, img.height * .01, img.width * .98, img.height * .99]
    b = torch.tensor([[box[0] * up, box[1] * up, (box[2] - box[0]) * up, (box[3] - box[1]) * up, 1.0]], device='cuda')
    with torch.inference_mode():
        d = m.estimate_smpl_batched(x, [b])
    j = d['joints2d'][0][0].float().cpu().numpy() / up
    del m; torch.cuda.empty_cache(); return j

def sam_mask(img, j, box):
    from transformers import Sam2Model, Sam2Processor
    model = Sam2Model.from_pretrained(SAM).cuda().eval(); proc = Sam2Processor.from_pretrained(SAM)
    pts = [[[[float(p[0]), float(p[1])] for p in j[[0, 3, 6, 9, 12, 15, 4, 5]]]]]
    inp = proc(images=img, input_boxes=[[box]], input_points=pts, input_labels=[[[1] * 8]], return_tensors='pt').to('cuda')
    with torch.inference_mode():
        o = model(**inp, multimask_output=True)
    ms = proc.post_process_masks(o.pred_masks.cpu(), inp['original_sizes'])[0][0]  # (3,H,W)
    k = int(o.iou_scores[0, 0].argmax()); del model; torch.cuda.empty_cache()
    return ms[k].numpy().astype(bool), float(o.iou_scores[0, 0, k])

def segdist(P, a, b, ext=0.0):
    b = b + (b - a) * ext; ab = b - a
    t = np.clip(((P - a) @ ab) / (ab @ ab + 1e-9), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)

def partmap(mask, j):
    ys, xs = np.nonzero(mask); P = np.stack([xs, ys], 1).astype(float)
    D = np.stack([np.min([segdist(P, j[a], j[b], e) for a, b, e in PARTS[n]], 0) for n in PN], 1)
    pm = np.full(mask.shape, -1, np.int16); pm[ys, xs] = D.argmin(1); return pm

def headH(j): return 2.5 * np.linalg.norm(j[15] - j[12])

def tilt(a, b): return float(np.degrees(np.arctan2(a[1] - b[1], a[0] - b[0])))

def metrics(j):
    H = headH(j)  # skull top taken as 0.45H above the head joint
    foot = max(j[10][1], j[11][1], j[7][1], j[8][1])
    L = lambda a, b: np.linalg.norm(j[a] - j[b]) / H
    return {'height_heads': (foot - (j[15][1] - 0.45 * H)) / H,
            'shoulder_tilt_deg': tilt(j[16], j[17]), 'hip_tilt_deg': tilt(j[1], j[2]),
            'plumb_footL_heads': (j[7][0] - j[12][0]) / H, 'plumb_footR_heads': (j[8][0] - j[12][0]) / H,
            'shoulder_width_heads': L(16, 17), 'hip_width_heads': L(1, 2), 'torso_heads': L(12, 0),
            'upperarmL': L(16, 18), 'forearmL': L(18, 20), 'upperarmR': L(17, 19), 'forearmR': L(19, 21),
            'thighL': L(1, 4), 'shinL': L(4, 7), 'thighR': L(2, 5), 'shinR': L(5, 8)}

def font(s):
    try: return ImageFont.truetype('arial.ttf', s)
    except OSError: return ImageFont.load_default()

def skel(d, j, s=1.0, col=(0, 220, 255), w=3):
    for a, b in BONES: d.line([tuple(j[a] * s), tuple(j[b] * s)], fill=col, width=w)
    for p in j: r = 3 * w / 3 + 2; d.ellipse([p[0] * s - r, p[1] * s - r, p[0] * s + r, p[1] * s + r], outline=(255, 230, 0), width=2)

def cmd_ref():
    src, out = sys.argv[2], sys.argv[3]
    img = Image.open(src).convert('RGB'); box = arg('--box', [img.width * .02, img.height * .01, img.width * .98, img.height * .99])
    j = nlf(img, box); mask, sc = sam_mask(img, j, box); pm = partmap(mask, j)
    np.savez(out, joints2d=j, mask=mask, partmap=pm, box=np.array(box))
    a = np.array(img).copy(); sel = pm >= 0; a[sel] = (a[sel] * .45 + PAL[pm[sel]] * .55).astype(np.uint8)
    edge = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; a[edge] = (0, 255, 255)
    S = 3; im = Image.fromarray(a).resize((img.width * S, img.height * S), Image.NEAREST); d = ImageDraw.Draw(im); skel(d, j, S)
    im.save(out.replace('.npz', '_ref.png')); print('sam iou', round(sc, 3), 'mask px', int(mask.sum()))
    for k, v in metrics(j).items(): print(f'{k:22s} {v:7.2f}')

def align(ref, over):
    """affine (scale/rot/shift) mapping over -> ref pixel coords via SIFT + RANSAC"""
    g1, g2 = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY), cv2.cvtColor(over, cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create(4000); k1, d1 = sift.detectAndCompute(g1, None); k2, d2 = sift.detectAndCompute(g2, None)
    mt = [m for m, n in cv2.BFMatcher().knnMatch(d2, d1, k=2) if m.distance < .75 * n.distance]
    A, inl = cv2.estimateAffinePartial2D(np.float32([k2[m.queryIdx].pt for m in mt]), np.float32([k1[m.trainIdx].pt for m in mt]),
                                         method=cv2.RANSAC, ransacReprojThreshold=4)
    return A, int(inl.sum()), len(mt)

def strokes(ref, over, A):
    """near-black, unsaturated pixels of the overdrawn image, warped into ref coords, where the ref itself is not dark"""
    hsv = cv2.cvtColor(over, cv2.COLOR_RGB2HSV); dark = (over.max(2) < 70) & (hsv[..., 1] < 110)
    st = cv2.warpAffine(dark.astype(np.uint8) * 255, A, (ref.shape[1], ref.shape[0]), flags=cv2.INTER_LINEAR) > 100
    st &= ref.max(2) > 90
    return cv2.morphologyEx(st.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

def classify(comp, j, pm, dE, H):
    """one stroke -> (kind, part, err in H): loop = closed outline, edge = near SAM2 silhouette, axis = near NLF bone, interior = landmark"""
    ys, xs = np.nonzero(comp); P = np.stack([xs, ys], 1).astype(float)
    cs, hier = cv2.findContours(comp.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    closed = hier is not None and any(h[3] >= 0 and cv2.contourArea(c) > 6 for c, h in zip(cs, hier[0]))
    e = float(np.median(dE[ys, xs])) / H
    ax = min(float(np.median(segdist(P, j[a], j[b]))) for a, b in BONES) / H
    parts = pm[ys, xs]; inside = parts >= 0; part = PN[np.bincount(parts[inside]).argmax()] if inside.any() else 'outside'
    if closed: return 'loop', part, None, xs, ys
    if e <= ax: return 'edge', part, e, xs, ys
    return ('axis', part, ax, xs, ys) if ax <= .35 else ('interior', part, None, xs, ys)

def errcol(err):
    return (150, 150, 150) if err is None else (40, 220, 60) if err < .08 else (255, 200, 0) if err < .2 else (255, 40, 40)

def cmd_over():
    R = np.load(sys.argv[2]); ref = np.array(Image.open(sys.argv[3]).convert('RGB')); over = np.array(Image.open(sys.argv[4]).convert('RGB'))
    out = sys.argv[5]; j, mask, pm = R['joints2d'], R['mask'], R['partmap']; H = headH(j)
    A, ninl, nm = align(ref, over); print('align inliers', ninl, 'of', nm, 'scale', round(float(np.hypot(A[0, 0], A[1, 0])), 3))
    edge = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    dE = cv2.distanceTransform((1 - edge).astype(np.uint8), cv2.DIST_L2, 5)
    n, lab, stats, cen = cv2.connectedComponentsWithStats(strokes(ref, over, A), 8)
    S = 3; base = ref.copy(); sel = pm >= 0; base[sel] = (base[sel] * .7 + PAL[pm[sel]] * .3).astype(np.uint8); base[edge > 0] = (0, 255, 255)
    im = Image.fromarray(base).resize((ref.shape[1] * S, ref.shape[0] * S), Image.NEAREST); d = ImageDraw.Draw(im, 'RGBA'); f = font(13)
    rows = []
    for i in [i for i in range(1, n) if stats[i, 4] >= max(8, H * .15)]:
        kind, part, err, xs, ys = classify(lab == i, j, pm, dE, H)
        for x, y in zip(xs, ys): d.rectangle([x * S, y * S, x * S + S - 1, y * S + S - 1], fill=errcol(err) + (255,))
        tag = f'{i}:{kind}' + ('' if err is None else f' {err:.2f}H')
        d.text((cen[i][0] * S + 6, cen[i][1] * S - 6), tag, fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
        rows.append((i, kind, part, err, int(stats[i, 4])))
    im.save(out)
    print('id kind     part        err(H)  px   (edge = dist to SAM2 silhouette, axis = dist to NLF bone; H =', round(H, 1), 'px)')
    for r in rows: print(f'{r[0]:2d} {r[1]:8s} {r[2]:11s} {"-" if r[3] is None else f"{r[3]:.2f}":>6s} {r[4]:5d}')

def cmd_paper():
    R = np.load(sys.argv[2]); ref = Image.open(sys.argv[3]).convert('RGB'); drw = Image.open(sys.argv[4]).convert('RGB'); out = sys.argv[5]
    rot = arg('--rot');  # degrees CCW (PIL); -90 = turn a head-left photo upright; --box is in rotated px
    if rot: drw = drw.rotate(rot[0], expand=True)
    box = arg('--box'); jd = nlf(drw, box); jr = R['joints2d']; mr, md = metrics(jr), metrics(jd)
    hgt = 900; sr, sd = hgt / ref.height, hgt / drw.height
    im = Image.new('RGB', (int(ref.width * sr) + int(drw.width * sd) + 380, hgt), (20, 20, 20))
    im.paste(ref.resize((int(ref.width * sr), hgt)), (0, 0)); ox = int(ref.width * sr); im.paste(drw.resize((int(drw.width * sd), hgt)), (ox, 0))
    d = ImageDraw.Draw(im); skel(d, jr, sr); jd2 = jd * sd + np.array([ox, 0]); skel(d, jd2, 1.0, (255, 80, 200))
    for jj, s, x0 in [(jr * sr, 1, 0), (jd2, 1, ox)]:
        d.line([(jj[12][0], jj[12][1]), (jj[12][0], hgt)], fill=(80, 255, 120), width=1)
    f = font(15); y = 10; tx = ox + int(drw.width * sd) + 10
    d.text((tx, y), 'metric            ref   yours  diff', fill=(255, 255, 255), font=f); y += 22
    print('metric                  ref   yours   diff')
    for k in mr:
        diff = md[k] - mr[k]; bad = abs(diff) > (6 if 'deg' in k else .25)
        d.text((tx, y), f'{k[:17]:17s} {mr[k]:5.1f} {md[k]:6.1f} {diff:+5.1f}', fill=(255, 90, 90) if bad else (200, 200, 200), font=f); y += 20
        print(f'{k:22s} {mr[k]:6.2f} {md[k]:6.2f} {diff:+6.2f}' + ('  <-' if bad else ''))
    im.save(out); np.save(out.replace('.png', '_joints.npy'), jd)

if __name__ == '__main__':
    {'ref': cmd_ref, 'over': cmd_over, 'paper': cmd_paper}[sys.argv[1]]()
