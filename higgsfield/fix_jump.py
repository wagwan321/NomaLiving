"""Remove a sudden forward jump (a hidden cut) from a clip: the frames before the jump are zoomed in
progressively (eased) so that the last one lands exactly on the framing after the jump.

    python -E higgsfield/fix_jump.py <in.mp4> <out.mp4> --at 35
--at is the first frame after the jump.
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
    ap.add_argument("--at", type=int, required=True)
    ap.add_argument("--fps", type=float, default=24)
    a = ap.parse_args()
    info = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    W, H = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    fr = [np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3) for i in range(n)]
    # similarity transform frame[at-1] -> frame[at]
    sift = cv2.SIFT_create(5000)
    ka, da = sift.detectAndCompute(cv2.cvtColor(fr[a.at - 1], cv2.COLOR_BGR2GRAY), None)
    kb, db = sift.detectAndCompute(cv2.cvtColor(fr[a.at], cv2.COLOR_BGR2GRAY), None)
    good = [m[0] for m in cv2.BFMatcher().knnMatch(da, db, k=2) if len(m) == 2 and m[0].distance < 0.7 * m[1].distance]
    A, _ = cv2.estimateAffinePartial2D(np.float32([ka[g.queryIdx].pt for g in good]),
                                       np.float32([kb[g.trainIdx].pt for g in good]))
    s = float(np.hypot(A[0, 0], A[1, 0]))
    # the fixed point of the zoom (the point that does not move), so intermediate frames zoom about it
    cx, cy = np.linalg.solve(np.eye(2) - A[:, :2], A[:, 2])
    print(f"jump: scale {s:.3f} about ({cx:.0f}, {cy:.0f})")
    out = []
    for i in range(a.at):
        k = i / (a.at - 1)
        e = k * k * (3 - 2 * k)                      # eased: starts and ends gently
        z = s ** e                                   # zoom grows geometrically (constant perceived speed)
        M = np.array([[z, 0, cx - z * cx], [0, z, cy - z * cy]], np.float32)
        out.append(cv2.warpAffine(fr[i], M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE))
    out += fr[a.at:]
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
                            "-pix_fmt", "yuv420p", a.dst], stdin=subprocess.PIPE)
    for f in out:
        enc.stdin.write(f.tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, len(out), "frames")


if __name__ == "__main__":
    main()
