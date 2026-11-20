"""Phone walk-through that opens full screen on the whole NOMA LIVING front.

The laptop video's first frame is not tall enough to fill a phone with the whole sign in view, so the
start of the laptop video was reframed to 9:16 (Higgsfield reframe), which draws the building above and
the pavement below. Only those two strips are taken from it (its first frame), each lined up with the
edge of the video it touches and then carried along with the video's own motion at that edge. Inside the
laptop picture every pixel is the laptop video. The phone view starts wide (whole sign, full screen)
and narrows to the normal portrait crop by frame N; from there on it is exactly portrait_crop.py output.

    py -3.10 -E higgsfield/portrait_reframe.py <master dir NNN.webp> <crop dir f_NNNN.png> <reframe.mp4> <out dir> [--sheet x.jpg]
"""
import argparse, os, shutil, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portrait_crop import path  # noqa: E402

N = 60                 # frames over which the wide view becomes the normal crop (2.5 s at 24 fps)
START_W = 1400         # landscape pixels across the phone at the start: the whole sign plus a margin
START_CX = 1018        # centre of the sign
SEAM = 90              # rows (landscape pixels) over which the original fades into the fill
STRIPS = {"top": (0, 200), "bottom": (760, 1080)}   # rows of the video each fill is lined up with

sift = cv2.SIFT_create(20000)


def feats(img, rows=None, scale=1.0):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = None
    if rows:
        mask = np.zeros(g.shape, np.uint8); mask[rows[0]:rows[1]] = 255
    if scale != 1.0:
        g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if mask is not None: mask = cv2.resize(mask, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST)
    k, d = sift.detectAndCompute(g, mask)
    return np.float32([p.pt for p in k]) / scale, d


def similarity(f1, f2, ratio=.75, thr=3.0):
    """3x3 similarity taking points of f1 onto f2."""
    (p1, d1), (p2, d2) = f1, f2
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    g = [a for a, b in m if a.distance < ratio * b.distance]
    A, inl = cv2.estimateAffinePartial2D(p1[[a.queryIdx for a in g]], p2[[a.trainIdx for a in g]],
                                         ransacReprojThreshold=thr, maxIters=5000)
    return np.vstack([A, [0, 0, 1]]), int(inl.sum())


def smooth(Ms, k=3):
    P = np.array([M[:2].ravel() for M in Ms])
    ker = np.exp(-0.5 * (np.arange(-2 * k, 2 * k + 1) / k) ** 2); ker /= ker.sum()
    P = np.stack([np.convolve(np.pad(P[:, j], 2 * k, mode="edge"), ker, "valid") for j in range(6)], 1)
    return [np.vstack([p.reshape(2, 3), [0, 0, 1]]) for p in P]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("crop"); ap.add_argument("reframe"); ap.add_argument("out")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(a.src) if f.endswith(".webp"))
    cx = path(len(names))
    ok, R = cv2.VideoCapture(a.reframe).read()
    assert ok
    frames = [cv2.imread(os.path.join(a.src, names[i])) for i in range(N)]
    H, W = frames[0].shape[:2]
    fR = feats(R)

    # 1) where the reframe sits relative to video frame 0 overall (SIFT), then refined for each strip
    #    separately on the pixels themselves (ECC), since the reframe re-draws the front slightly differently
    G, n = similarity(feats(frames[0], None, .5), fR)
    print("overall fit on", n, "points, scale %.3f" % G[0, 0])
    gR = cv2.GaussianBlur(cv2.cvtColor(R, cv2.COLOR_BGR2GRAY), (0, 0), 1).astype(np.float32)
    g0 = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    align = {}
    for key, (r0, r1) in STRIPS.items():
        T = np.array([[2, 0, 0], [0, 2, r0], [0, 0, 1]], float)       # half-size strip -> video coords
        tmpl = cv2.resize(g0, (W // 2, H // 2), interpolation=cv2.INTER_AREA)[r0 // 2:r1 // 2]
        tmpl = cv2.GaussianBlur(tmpl, (0, 0), 1).astype(np.float32)
        # straight lines stay straight: only one uniform scale and a shift (no slant, no rotation). The
        # scale is searched, the shift is solved on the pixels (ECC) for each scale; best match wins.
        best = (-1, None)
        for sc in np.linspace(G[0, 0] * .85, G[0, 0] * 1.15, 61):
            Wm = np.array([[1, 0, 0], [0, 1, 0]], np.float32)
            ctr = np.array([W / 2, (r0 + r1) / 2, 1])
            pt = G @ ctr                                             # keep the overall fit's centre as the start
            Ws = np.array([[sc * 2, 0, pt[0] - sc * W / 2], [0, sc * 2, pt[1] - sc * (r1 - r0) / 2]], np.float32)
            sm = cv2.resize(gR, None, fx=1, fy=1)
            warped = cv2.warpAffine(sm, Ws, (tmpl.shape[1], tmpl.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            try:
                cc, Wt = cv2.findTransformECC(tmpl, warped, Wm, cv2.MOTION_TRANSLATION,
                                              (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
            except cv2.error:
                continue
            if cc > best[0]:
                full = np.vstack([Ws, [0, 0, 1]]) @ np.vstack([Wt, [0, 0, 1]])
                best = (cc, full)
        cc, Wm = best
        align[key] = Wm @ np.linalg.inv(T)                             # video frame 0 -> reframe
        print(key, "edge match %.3f" % cc, np.round(align[key][:2].ravel(), 3))

    # 2) the video's own motion near each edge, frame to frame (upper half / lower half of the picture)
    motion = {k: [np.eye(3)] for k in STRIPS}
    prev = feats(frames[0], None, .5)
    for i in range(1, N):
        cur = feats(frames[i], None, .5)
        m = cv2.BFMatcher().knnMatch(prev[1], cur[1], k=2)
        g = [x for x, y in m if x.distance < .75 * y.distance]
        p1 = prev[0][[x.queryIdx for x in g]]; p2 = cur[0][[x.trainIdx for x in g]]
        for key, sel in (("top", p1[:, 1] < H * .45), ("bottom", p1[:, 1] > H * .55)):
            A, inl = cv2.estimateAffinePartial2D(p1[sel], p2[sel], ransacReprojThreshold=1.5, maxIters=5000)
            motion[key].append(np.vstack([A, [0, 0, 1]]) @ motion[key][-1])
        prev = cur
    # 3) an extended first frame per edge: video frame 0 itself, with the reframe only beyond its edges.
    #    It is carried along with the video's motion, so anything the camera has moved past is filled
    #    with the video's own earlier pixels (the whole sign is in frame 0) and only what frame 0 never
    #    showed (above the balcony, the street) comes from the reframe.
    PAD = 1500
    Off = np.array([[1, 0, PAD], [0, 1, PAD], [0, 0, 1]], float)       # frame-0 coords -> canvas
    CW, CH = W + 2 * PAD, H + 2 * PAD
    y = np.arange(CH)[:, None] - PAD
    edge = np.clip(np.minimum(y, H - 1 - y) / SEAM, 0, 1)
    m0 = (((y >= 0) & (y <= H - 1)) * edge)[:, :, None].astype(np.float32)
    f0c = cv2.warpAffine(frames[0], Off[:2], (CW, CH))
    ext = {}
    for key in STRIPS:
        rc = cv2.warpAffine(R, (Off @ np.linalg.inv(align[key]))[:2], (CW, CH), flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_REPLICATE)
        ext[key] = np.clip(f0c * m0 + rc * (1 - m0), 0, 255).astype(np.uint8)
    fill = {key: [M @ np.linalg.inv(Off) for M in smooth(motion[key])] for key in STRIPS}  # canvas -> frame i

    # 4) refine every frame right at its join: line the extended frame up with the frame's own edge rows
    #    on the pixels (ECC, perspective, so the floor and facade planes match), then smooth over time
    Sh = np.diag([.5, .5, 1.0])
    JOIN = {"top": (0, 240), "bottom": (840, 1080)}
    for key, (r0, r1) in JOIN.items():
        eg = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(ext[key], (CW // 2, CH // 2), interpolation=cv2.INTER_AREA),
                                           cv2.COLOR_BGR2GRAY), (0, 0), 1).astype(np.float32)
        Tt = np.array([[2, 0, 0], [0, 2, r0], [0, 0, 1]], float)
        out = [fill[key][0]]
        for i in range(1, N):
            g = cv2.resize(cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
            tmpl = cv2.GaussianBlur(g[r0 // 2:r1 // 2], (0, 0), 1).astype(np.float32)
            Wm = Sh @ np.linalg.inv(fill[key][i]) @ Tt
            Wm = (Wm / Wm[2, 2]).astype(np.float32)
            try:
                cc, Wm = cv2.findTransformECC(tmpl, eg, Wm, cv2.MOTION_HOMOGRAPHY,
                                              (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
                F = np.linalg.inv(np.linalg.inv(Sh) @ Wm.astype(float) @ np.linalg.inv(Tt))
            except cv2.error:
                cc, F = -1, fill[key][i]
            out.append(F / F[2, 2])
            if i % 10 == 0: print(key, i, "join match %.3f" % cc)
        P = np.array([F.ravel()[:8] for F in out])
        k = 2
        ker = np.exp(-0.5 * (np.arange(-2 * k, 2 * k + 1) / k) ** 2); ker /= ker.sum()
        P = np.stack([np.convolve(np.pad(P[:, j], 2 * k, mode="edge"), ker, "valid") for j in range(8)], 1)
        fill[key] = [np.append(p, 1).reshape(3, 3) for p in P]

    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(a.out)
    tiles = []
    for i, name in enumerate(names):
        dst = os.path.join(a.out, f"f_{i:04d}.png")
        if i >= N:
            shutil.copyfile(os.path.join(a.crop, f"f_{i:04d}.png"), dst)
            if i < N + 24 and i % 12 == 0: tiles.append(cv2.resize(cv2.imread(dst), (216, 384)))
            continue
        im = frames[i]
        cw = round(H * 9 / 16)
        x_end = int(round(min(max(cx[i] * W - cw / 2, 0), W - cw))) + cw / 2
        t = i / N
        e = 3 * t * t - 2 * t ** 3
        w = np.exp(np.log(START_W) * (1 - e) + np.log(cw) * e)
        h = w * 16 / 9
        c = START_CX * (1 - e) + x_end * e
        x0, y0 = c - w / 2, H - h                # bottom of the screen stays on the video's bottom edge
        s = 1080 / w
        V = np.array([[s, 0, -x0 * s], [0, s, -y0 * s], [0, 0, 1]])   # video coords -> phone frame
        fg = cv2.warpAffine(im, V[:2], (1080, 1920), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        top = cv2.warpPerspective(ext["top"], V @ fill["top"][i], (1080, 1920), flags=cv2.INTER_LANCZOS4,
                             borderMode=cv2.BORDER_REPLICATE)
        bot = cv2.warpPerspective(ext["bottom"], V @ fill["bottom"][i], (1080, 1920), flags=cv2.INTER_LANCZOS4,
                             borderMode=cv2.BORDER_REPLICATE)
        yy = (np.arange(1920) / s + y0)[:, None]                  # video row of each phone row
        inside = (yy >= 0) & (yy <= H - 1)
        my = np.clip(np.minimum(yy, H - 1 - yy) / SEAM, 0, 1)
        # the seam hardens to pure original as the view closes in, so frame N is exactly the normal crop
        m = (inside * (my + (1 - my) * e * e))[:, :, None]
        bg = np.where((yy < H / 2)[:, :, None], top, bot).astype(np.float32)
        img = np.clip(fg * m + bg * (1 - m), 0, 255).astype(np.uint8)
        cv2.imwrite(dst, img)
        if i % 12 == 0: tiles.append(cv2.resize(img, (216, 384)))
    if a.sheet: cv2.imwrite(a.sheet, np.hstack(tiles))
    print("frames", len(names), "reframed start", N)


if __name__ == "__main__":
    main()
