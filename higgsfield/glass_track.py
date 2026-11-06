"""Give the shop window and door clear, consistent glass through a whole shot.

A clear-glass plate (plate_full.png + plate_mask.png + panes.json, in the coordinates of one
reference frame) is followed through the shot by the four corners of each glass pane:

1. frame-to-frame homographies of the facade (SIFT + RANSAC, glass excluded) chained from the
   reference frame give every pane's corners in every frame;
2. every ANCHOR frames the corners are measured again by matching that frame directly to the
   reference (via a midway frame when they are far apart), and the chained path is corrected so
   it passes through these direct measurements (no drift far from the reference);
3. the corner paths are smoothed over time, and each pane is mapped corner to corner.

    python -E higgsfield/glass_track.py <in.mp4> <out.mp4> <first|last> <plate dir> [--until S] [--panes door,window]
"""
import argparse
import json
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 24
ANCHOR = 12


def read(path):
    info = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    w, h = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)], w, h


class Tracker:
    def __init__(self, frames, glass_ref):
        self.f, self.glass = frames, cv2.dilate(glass_ref, np.ones((31, 31), np.uint8))
        ring = cv2.dilate(glass_ref, np.ones((181, 181), np.uint8))
        ring[int(glass_ref.nonzero()[0].max()) + 40:] = 0            # nothing below the panes (pavement, planter front)
        self.band = np.where((ring > 0) & (self.glass == 0), 255, 0).astype(np.uint8)
        self.sift, self.bf = cv2.SIFT_create(5000), cv2.BFMatcher()

    def feat(self, i, Hm):
        H, W = self.f[i].shape[:2]
        sc = 0.6
        g = cv2.cvtColor(cv2.resize(self.f[i], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        # only the facade band right around the glass (frames, pillar faces, lettering): one flat plane
        band = cv2.resize(cv2.warpPerspective(self.band, Hm, (W, H)), (g.shape[1], g.shape[0]))
        k, d = self.sift.detectAndCompute(g, np.where(band > 0, 255, 0).astype(np.uint8))
        return (np.float32([p.pt for p in k]) / sc if k else np.zeros((0, 2), np.float32)), d

    def match(self, fa, fb):
        """homography a -> b and its inlier count"""
        (pa, da), (pb, db) = fa, fb
        if da is None or db is None or len(da) < 10 or len(db) < 10:
            return None, 0
        good = [x[0] for x in self.bf.knnMatch(da, db, k=2) if len(x) == 2 and x[0].distance < 0.72 * x[1].distance]
        if len(good) < 15:
            return None, 0
        A = np.float32([pa[g.queryIdx] for g in good]); B = np.float32([pb[g.trainIdx] for g in good])
        Hm, inl = cv2.findHomography(A, B, cv2.RANSAC, 2.5)
        return Hm, int(inl.sum()) if inl is not None else 0


def corners(Hm, quad):
    return cv2.perspectiveTransform(np.float32(quad)[None], Hm)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("ref", choices=["first", "last"]); ap.add_argument("plate")
    ap.add_argument("--until", type=float, default=None)
    ap.add_argument("--fade", type=int, default=6)
    ap.add_argument("--panes", default="door,window")
    ap.add_argument("--upto", type=float, default=None, help="only track/replace up to this time (s)")
    a = ap.parse_args()
    frames, W, H = read(a.src)
    cfg = json.load(open(a.plate + "/panes.json"))
    plate = cv2.imread(cfg.get("_plate", a.plate + "/plate_full.png"))   # may be a wider source picture
    pmask = cv2.imread(a.plate + "/plate_mask.png", cv2.IMREAD_GRAYSCALE)
    panes = {k: v for k, v in cfg.items() if k in a.panes.split(",")}
    total = len(frames)
    n = total if a.upto is None else min(total, int(a.upto * FPS) + 1)
    if a.ref == "last" and n < total:
        raise SystemExit("--upto only works with ref=first")
    seq = list(range(n - 1, -1, -1)) if a.ref == "last" else list(range(n))
    ref = seq[0]
    T = Tracker(frames, pmask)

    # 1. chained homographies
    Hc = {ref: np.eye(3)}
    feats = {}
    for p, i in zip(seq, seq[1:]):
        fp = feats.pop(p, None) or T.feat(p, Hc[p])
        fi = T.feat(i, Hc[p])
        st, _ = T.match(fp, fi)
        Hc[i] = (st if st is not None else np.eye(3)) @ Hc[p]
        feats[i] = fi
    # 2. direct measurements at anchors (two hops through a midway frame when far from the reference)
    fref = T.feat(ref, np.eye(3))
    direct = {ref: np.eye(3)}
    for k in range(ANCHOR, n, ANCHOR):
        i = seq[k]
        fi = T.feat(i, Hc[i])
        Hd, inl = T.match(fref, fi)
        if inl < 60:
            mid = seq[k // 2]
            fm = T.feat(mid, Hc[mid])
            H1, i1 = T.match(fref, fm)
            H2, i2 = T.match(fm, fi)
            Hd, inl = (H2 @ H1, min(i1, i2)) if H1 is not None and H2 is not None else (None, 0)
        if Hd is not None and inl >= 40:
            direct[i] = Hd
        print(f"anchor {i}: {inl} inliers{'' if i in direct else ' (skipped)'}")
    # 3. corner paths: chained, corrected through the direct measurements, smoothed
    out_quads = {}
    for name, pane in panes.items():
        quad = pane["frame"]
        ch = np.array([corners(Hc[i], quad) for i in range(n)])          # n x 4 x 2
        meas = {i: corners(direct[i], quad) for i in direct}
        for fi, q in pane.get("anchors", {}).items():                     # hand-measured corners win
            meas[(n + int(fi)) % n] = np.float32(q)
        idx = sorted(meas)
        off = np.array([meas[i] - ch[i] for i in idx])                    # corrections at anchors
        corr = np.zeros_like(ch)
        for c in range(4):
            for d in range(2):
                corr[:, c, d] = np.interp(np.arange(n), idx, off[:, c, d])
        q = ch + corr
        k = 5
        pad = np.concatenate([np.repeat(q[:1], k, 0), q, np.repeat(q[-1:], k, 0)])
        ker = np.ones(2 * k + 1) / (2 * k + 1)
        sm = np.zeros_like(q)
        for c in range(4):
            for d in range(2):
                sm[:, c, d] = np.convolve(pad[:, c, d], ker, "valid")
        for i in idx:                                                     # keep measured frames exact
            sm[i] = meas[i] if i in pane.get("anchors_idx", []) else sm[i]
        out_quads[name] = sm                                              # n x 4 x 2
    # 4. composite
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
                            "-pix_fmt", "yuv420p", a.dst], stdin=subprocess.PIPE)
    for i in range(n):
        img = frames[i].astype(np.float32)
        for name, pane in panes.items():
            until = pane.get("until", a.until)                # per-pane cut-off (e.g. the door starts to swing)
            k = 1.0 if until is None else float(np.clip((until - i / FPS) * FPS / a.fade, 0, 1))
            if k > 0:
                    srcq = pane.get("src", pane["frame"])           # the pane's corners in the plate picture
                    Hm = cv2.getPerspectiveTransform(np.float32(srcq), np.float32(out_quads[name][i]))
                    wp = cv2.warpPerspective(plate, Hm, (W, H), flags=cv2.INTER_LANCZOS4).astype(np.float32)
                    m = np.zeros(plate.shape[:2], np.uint8)
                    cv2.fillConvexPoly(m, np.int32(np.round(srcq)), 255)
                    wm = cv2.warpPerspective(m, Hm, (W, H)).astype(np.float32) / 255
                    s = np.sqrt(abs(np.linalg.det(Hm[:2, :2])))
                    wm = cv2.GaussianBlur(wm, (0, 0), max(0.7, 1.6 * s))[..., None] * k
                    img = wp * wm + img * (1 - wm)
        enc.stdin.write(img.astype(np.uint8).tobytes())
    for i in range(n, total):                              # untouched rest of the shot
        enc.stdin.write(frames[i].tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, n, "frames")


if __name__ == "__main__":
    main()
