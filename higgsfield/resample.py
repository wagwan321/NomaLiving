"""Resample a walk-through video to more pictures (motion-compensated in-betweens), written as the
PNG frames blender/frames.py exports for the website.

    python -E higgsfield/resample.py <in.mp4> <out dir> --total 743 [--step 2]

Writes f_NNNN.png for ids 0, step, 2*step ... < total; id k shows the video at k/(total-1) of its
length. In-betweens come from optical flow in both directions (no ghosting where they agree).
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drone_retime import read   # noqa: E402


def flow(a, b, sc):
    ga = cv2.cvtColor(cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(cv2.resize(b, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    f = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 5, 25, 4, 7, 1.5, 0)
    return (cv2.resize(f, (a.shape[1], a.shape[0])) / sc).astype(np.float32)


def between(a, b, t, fab, fba):
    H, W = a.shape[:2]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    t = np.float32(t)
    wa = cv2.remap(a, gx - t * fab[..., 0], gy - t * fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(b, gx - (1 - t) * fba[..., 0], gy - (1 - t) * fba[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(wa, float(1 - t), wb, float(t), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--total", type=int, required=True)
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args()
    frames, W, H = read(a.src)
    n = len(frames)
    os.makedirs(a.out, exist_ok=True)
    sc = 960 / max(W, H)
    cache = {}
    for k in range(0, a.total, a.step):
        p = k / (a.total - 1) * (n - 1)
        i = min(int(p), n - 2)
        t = p - i
        if t < 0.03:
            img = frames[i]
        elif t > 0.97:
            img = frames[i + 1]
        else:
            if i not in cache:
                cache.clear()
                cache[i] = (flow(frames[i], frames[i + 1], sc), flow(frames[i + 1], frames[i], sc))
            img = between(frames[i], frames[i + 1], t, *cache[i])
        cv2.imwrite(os.path.join(a.out, f"f_{k:04d}.png"), img)
    print(a.out, len(range(0, a.total, a.step)), "frames from", n)


if __name__ == "__main__":
    main()
