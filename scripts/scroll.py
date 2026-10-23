"""Build a long horizontal painted scroll (or any panorama) from one base image by outpainting panel by panel.

Panels are 2400x1350; neighbours overlap by 600 px (a quarter), so every new panel is painted from a canvas whose
edge strip is copied from its neighbour, and the stitch is exact.

    python3 scroll.py widen  base.jpg canvas_C.png            # base centred on a 16:9 silk canvas -> outpaint sides
    python3 scroll.py canvas panel.png right canvas_B.png      # new panel continues to the RIGHT of panel.png
    python3 scroll.py canvas panel.png left  canvas_D.png      # new panel continues to the LEFT
    python3 scroll.py stitch scroll.png --base 2 E.png D.png C.png B.png A.png   # left->right; --base = original
    python3 scroll.py crops  scroll.png frames/ 7200 6600 5200 4000 3000 1500 0  # 16:9 crops -> 1920x1080 jpgs

Fill each canvas with keyframe.py --painting ("OUTPAINT: the LEFT quarter is an existing strip ... keep it unchanged").
"""
import os, sys
import numpy as np
from PIL import Image

PW, PH, OV = 2400, 1350, 600


def silk_colour(a):
    """Median colour of the flattest 5% of 40x40 blocks: the plain ground of the painting."""
    h, w = a.shape[:2]; blocks = []
    for y in range(0, h - 40, 40):
        for x in range(0, w - 40, 40):
            b = a[y:y + 40, x:x + 40].reshape(-1, 3); blocks.append((b.std(), np.median(b, 0)))
    blocks.sort(key=lambda t: t[0])
    return tuple(int(v) for v in np.median([b for _, b in blocks[:max(1, len(blocks) // 20)]], 0))


def widen(src, out):
    p = Image.open(src).convert('RGB'); p = p.resize((int(p.width * PH / p.height), PH), Image.LANCZOS)
    c = Image.new('RGB', (PW, PH), silk_colour(np.asarray(p).astype(float)))
    c.paste(p, ((PW - p.width) // 2, 0)); c.save(out); print('canvas', out, 'base width', p.width)


def canvas(src, side, out):
    a = Image.open(src).convert('RGB').resize((PW, PH))
    c = Image.new('RGB', (PW, PH), silk_colour(np.asarray(a).astype(float)))
    if side == 'right': c.paste(a.crop((PW - OV, 0, PW, PH)), (0, 0))
    else: c.paste(a.crop((0, 0, OV, PH)), (PW - OV, 0))
    c.save(out); print('canvas', out)


def stitch(out, panels, base):
    from scipy.ndimage import gaussian_filter, gaussian_filter1d
    P = [np.asarray(Image.open(p).convert('RGB').resize((PW, PH))).astype(np.float32) for p in panels]
    n = len(P); step = PW - OV; total = step * (n - 1) + PW
    pano = np.zeros((PH, total, 3), np.float32); pano[:, :PW] = P[0]
    ramp = np.linspace(0, 1, OV)[None, :, None]
    for i in range(1, n):
        x0 = step * i
        pano[:, x0:x0 + OV] = pano[:, x0:x0 + OV] * (1 - ramp) + P[i][:, :OV] * ramp
        pano[:, x0 + OV:x0 + PW] = P[i][:, OV:]
    # seams sit where newly painted content meets a copied strip: left of base -> new content is on the left
    seams = [(step * i + PW - OV, 'L') for i in range(base)] + [(step * i + OV, 'R') for i in range(base + 1, n)]
    for xb, side in seams:
        old = pano[:, xb:xb + 40] if side == 'L' else pano[:, xb - 40:xb]
        new = pano[:, xb - 40:xb] if side == 'L' else pano[:, xb:xb + 40]
        diff = gaussian_filter1d(old.mean(1) - new.mean(1), 60, axis=0)   # per-row colour offset
        r = np.linspace(1, 0, 500) ** 1.5
        if side == 'L': pano[:, xb - 500:xb] += diff[:, None, :] * r[::-1][None, :, None]
        else: pano[:, xb:xb + 500] += diff[:, None, :] * r[None, :, None]
        band = pano[:, xb - 60:xb + 60]                                   # soften residual texture line
        m = np.exp(-((np.arange(120) - 60) / 18.0) ** 2)[None, :, None]
        pano[:, xb - 60:xb + 60] = band * (1 - m) + gaussian_filter(band, (0, 14, 0)) * m
    im = Image.fromarray(pano.clip(0, 255).astype(np.uint8)); im.save(out)
    im.resize((total // 6, PH // 6)).save(os.path.splitext(out)[0] + '_preview.jpg')
    print('scroll', out, im.size, 'seams', [s for s, _ in seams])


def crops(src, outdir, xs):
    im = Image.open(src).convert('RGB'); os.makedirs(outdir, exist_ok=True)
    for i, x in enumerate(xs):
        im.crop((x, 0, x + PW, PH)).resize((1920, 1080), Image.LANCZOS).save(f'{outdir}/P{i}_{x}.jpg', quality=95)
    print('crops', len(xs), '->', outdir)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'widen': widen(*args)
    elif cmd == 'canvas': canvas(*args)
    elif cmd == 'stitch':
        b = args.index('--base'); base = int(args[b + 1]); rest = args[:b] + args[b + 2:]
        stitch(rest[0], rest[1:], base)
    elif cmd == 'crops': crops(args[0], args[1], [int(x) for x in args[2:]])
