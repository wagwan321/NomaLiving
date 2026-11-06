"""While the glass door swings open, the AI shows a faint ghost of an invented interior through the
glass. Give the swinging glass a soft, bright, realistic sheen instead (frames, handle and its
NOMA lettering stay untouched).

Per frame the leaf's glass is found between the dark vertical bars inside the door opening.

    python -E higgsfield/door_sheen.py <in.mp4> <out.mp4> --box x0,y0,x1,y1 --from S --to S
"""
import argparse
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 24


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--box", required=True, help="door opening x0,y0,x1,y1 (glass rows)")
    ap.add_argument("--from", dest="t0", type=float, required=True)
    ap.add_argument("--to", dest="t1", type=float, required=True)
    ap.add_argument("--ramp", type=int, default=3)
    a = ap.parse_args()
    x0, y0, x1, y1 = map(int, a.box.split(","))
    info = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    W, H = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
                            "-pix_fmt", "yuv420p", a.dst], stdin=subprocess.PIPE)
    i0, i1 = round(a.t0 * FPS), round(a.t1 * FPS)
    frames = [np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3).copy() for i in range(n)]

    def glass_run(reg):
        v = cv2.cvtColor(reg, cv2.COLOR_BGR2HSV)[..., 2]
        bars = (v < 70).mean(0) > 0.55
        xs = np.nonzero(~bars)[0]
        if not len(xs):
            return None
        gl = gr = xs[0]
        while gr + 1 < len(bars) and not bars[gr + 1]:
            gr += 1
        return (gl, gr) if gr - gl > 12 else None

    ref_reg = frames[max(0, i0 - 2)][y0:y1, x0:x1]
    run = glass_run(ref_reg)
    ref = ref_reg[:, run[0]:run[1] + 1].copy()          # clean corridor view through the closed door
    for i in range(n):
        f = frames[i]
        if i0 <= i <= i1:
            k = min(1.0, (i - i0 + 1) / a.ramp, (i1 - i + 1) / a.ramp)
            reg = f[y0:y1, x0:x1]
            r = glass_run(reg)
            if r:
                gl, gr = r
                g = reg[:, gl:gr + 1].astype(np.float32)
                hh, ww = g.shape[:2]
                view = cv2.resize(ref, (ww, hh), interpolation=cv2.INTER_AREA).astype(np.float32)
                grad = np.linspace(1.0, 0.2, ww)[None, :, None]
                view = view * 0.9 + np.float32([245, 246, 248]) * 0.1 * grad      # faint reflection
                hsv = cv2.cvtColor(reg[:, gl:gr + 1], cv2.COLOR_BGR2HSV)
                dark = (hsv[..., 2] < 80).astype(np.uint8)
                handle = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((120, 1), np.uint8))   # long vertical bar only
                handle = cv2.dilate(handle, np.ones((3, 7), np.uint8)) > 0
                m = (~handle).astype(np.float32)
                m[:, :3] *= np.linspace(0, 1, 3)[None, :]; m[:, -3:] *= np.linspace(1, 0, 3)[None, :]
                m = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None] * k
                reg[:, gl:gr + 1] = np.clip(view * m + g * (1 - m), 0, 255).astype(np.uint8)
                f[y0:y1, x0:x1] = reg
        enc.stdin.write(f.tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, n, "frames")


if __name__ == "__main__":
    main()
