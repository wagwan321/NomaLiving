"""Gimbal-smooth a clip: measure the camera's frame-to-frame motion (translation + rotation + zoom),
smooth that path, and move each frame onto the smooth path. A small zoom hides the moving edges.

    python -E higgsfield/stabilize.py <in.mp4> <out.mp4> [--radius 12] [--zoom 1.04]
"""
import argparse
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--radius", type=int, default=12, help="smoothing window, frames each side")
    ap.add_argument("--zoom", type=float, default=1.04)
    ap.add_argument("--fps", type=float, default=24)
    a = ap.parse_args()
    info = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    W, H = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    fr = [np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3) for i in range(n)]
    sc = 640 / W
    g = [cv2.cvtColor(cv2.resize(f, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for f in fr]
    # per-frame motion: dx, dy (full-res pixels), rotation, log zoom
    m = np.zeros((n - 1, 4))
    for i in range(n - 1):
        p = cv2.goodFeaturesToTrack(g[i], 500, 0.01, 8)
        q, st, _ = cv2.calcOpticalFlowPyrLK(g[i], g[i + 1], p, None)
        A, _ = cv2.estimateAffinePartial2D(p[st == 1], q[st == 1], method=cv2.RANSAC, ransacReprojThreshold=2)
        if A is None:
            continue
        m[i] = [A[0, 2] / sc, A[1, 2] / sc, np.arctan2(A[1, 0], A[0, 0]), np.log(np.hypot(A[0, 0], A[1, 0]))]
    path = np.vstack([np.zeros(4), np.cumsum(m, 0)])
    r = a.radius
    pad = np.pad(path, ((r, r), (0, 0)), mode="edge")
    ker = np.exp(-0.5 * (np.arange(-r, r + 1) / (r / 2)) ** 2); ker /= ker.sum()
    smooth = np.array([np.convolve(pad[:, c], ker, "valid") for c in range(4)]).T
    corr = smooth - path                        # move each frame by this to land on the smooth path
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-crf", "10", "-preset", "slow",
                            "-pix_fmt", "yuv420p", a.dst], stdin=subprocess.PIPE)
    cx, cy = W / 2, H / 2
    for i in range(n):
        dx, dy, da, dz = corr[i]
        s = a.zoom * np.exp(dz)
        M = cv2.getRotationMatrix2D((cx, cy), np.degrees(da), s)
        M[:, 2] += [dx * a.zoom, dy * a.zoom]
        enc.stdin.write(cv2.warpAffine(fr[i], M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT).tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, n, "frames; max correction px", np.abs(corr[:, :2]).max(0).round(1))


if __name__ == "__main__":
    main()
