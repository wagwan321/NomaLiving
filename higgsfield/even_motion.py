"""Even out frame-to-frame stutter while keeping the shot's overall pacing, and output 60 fps.

AI video moves in uneven steps (one frame jumps further than the next). The motion per frame is
measured (optical flow), its curve is smoothed over ~0.5 s, and every 60 fps output frame is built at
the source position where the smoothed motion says it should be (motion-compensated in-betweens).

    python -E higgsfield/even_motion.py <in.mp4> <out.mp4> [--fps-in 24] [--fps-out 60] [--window 13]
"""
import argparse
import os
import re
import subprocess
import sys

import cv2
import imageio_ffmpeg
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resample import between, flow  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--fps-in", type=float, default=24)
    ap.add_argument("--fps-out", type=float, default=60)
    ap.add_argument("--window", type=int, default=13)
    a = ap.parse_args()
    info = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    W, H = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    fr = [np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3) for i in range(n)]
    sc = 480 / W
    g = [cv2.cvtColor(cv2.resize(f, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for f in fr]
    m = np.array([np.median(np.hypot(*cv2.calcOpticalFlowFarneback(g[i], g[i + 1], None, 0.5, 4, 21, 3, 7, 1.5, 0)
                                     .transpose(2, 0, 1))) for i in range(n - 1)]) + 1e-3
    k = a.window // 2
    ker = np.exp(-0.5 * (np.arange(-k, k + 1) / (k / 2)) ** 2); ker /= ker.sum()
    s = np.convolve(np.pad(m, k, mode="edge"), ker, "valid")
    s *= m.sum() / s.sum()                                  # same total motion, so same start and end
    Cm = np.concatenate([[0], np.cumsum(m)])                # motion reached at each source frame
    Cs = np.concatenate([[0], np.cumsum(s)])                # where the smoothed motion says it should be
    n_out = int(round((n - 1) / a.fps_in * a.fps_out)) + 1
    u = np.linspace(0, n - 1, n_out)                        # output frames at even times (source-frame units)
    target = np.interp(u, np.arange(n), Cs)
    src_pos = np.interp(target, Cm, np.arange(n))           # source position that has that much motion
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(a.fps_out), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.dst], stdin=subprocess.PIPE)
    fsc = 960 / max(W, H)
    cache = {}
    for p in src_pos:
        i = min(int(p), n - 2)
        t = p - i
        if t < 0.03:
            img = fr[i]
        elif t > 0.97:
            img = fr[i + 1]
        else:
            if i not in cache:
                cache.clear()
                A, B = np.ascontiguousarray(fr[i]), np.ascontiguousarray(fr[i + 1])
                cache[i] = (A, B, flow(A, B, fsc), flow(B, A, fsc))
            A, B, fab, fba = cache[i]
            img = between(A, B, t, fab, fba)
        enc.stdin.write(img.tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, n_out, "frames; motion wobble before %.0f%%" % (100 * np.std(m - s) / m.mean()))


if __name__ == "__main__":
    main()
