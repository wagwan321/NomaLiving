"""Re-time the joined walk-through so the camera never slows down or stops: one steady, drone-like
glide from the street to the reception, easing in only at the very start and out at the very end.

1. measure how much the picture moves between consecutive frames (optical flow, median magnitude);
2. lay the output frames out at equal amounts of motion (speed clamped to MIN..MAX of the original);
3. build each output frame at its fractional source position with motion-compensated interpolation.

    python -E higgsfield/drone_retime.py <in.mp4> <out.mp4> [--seconds S]
"""
import argparse
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 24
MIN, MAX = 0.55, 3.0      # never slower than 0.55x or faster than 3x the original speed
EASE = 0.6                # seconds of ease-in and ease-out


def read(path):
    info = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    w, h = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)], w, h


def flow(a, b, scale):
    ga = cv2.cvtColor(cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(cv2.resize(b, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 4, 21, 3, 7, 1.5, 0)


def interp(a, b, t, fl):
    """frame at fraction t between a and b, using the a->b flow (computed at reduced scale)"""
    H, W = a.shape[:2]
    F = (cv2.resize(fl, (W, H)) * (W / fl.shape[1])).astype(np.float32)
    t = np.float32(t)
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    wa = cv2.remap(a, gx - t * F[..., 0], gy - t * F[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(b, gx + (1 - t) * F[..., 0], gy + (1 - t) * F[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(wa, 1 - t, wb, t, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--seconds", type=float, default=None, help="output length (default: same as input)")
    a = ap.parse_args()
    frames, W, H = read(a.src)
    n = len(frames)
    sc = 480 / W
    flows = [flow(frames[i], frames[i + 1], sc) for i in range(n - 1)]
    mot = np.array([np.median(np.hypot(f[..., 0], f[..., 1])) for f in flows]) + 1e-3
    k = 7
    mot = np.convolve(np.pad(mot, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    # target: equal motion per output frame, within the speed limits
    n_out = round((a.seconds or n / FPS) * FPS)
    target = mot.sum() / (n_out - 1)
    for _ in range(30):                                   # adjust the target so the clamped speeds fill n_out frames
        speed = np.clip(target / mot, MIN, MAX)           # source frames per output frame
        total = (1 / speed).sum()                         # output frames needed
        target *= total / (n_out - 1)
    speed = np.clip(target / mot, MIN, MAX)
    # output time spent on each source step, then the ease at both ends
    dt = 1 / speed
    cum = np.concatenate([[0], np.cumsum(dt)]); cum /= cum[-1]
    u = np.linspace(0, 1, n_out)
    r = EASE * FPS / n_out
    v = 1 / (1 - r)
    eased = np.where(u < r, v * u * u / (2 * r), np.where(u > 1 - r, 1 - v * (1 - u) ** 2 / (2 * r), v * (u - r / 2)))
    src_pos = np.interp(eased, cum, np.arange(n))
    print(f"{n} source frames -> {n_out} output frames; speed range {speed.min():.2f}x..{speed.max():.2f}x")
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.dst], stdin=subprocess.PIPE)
    for p in src_pos:
        i = min(int(p), n - 2)
        t = p - i
        if t < 0.02:
            img = frames[i]
        elif t > 0.98:
            img = frames[i + 1]
        else:
            img = interp(frames[i], frames[i + 1], t, flows[i])
        enc.stdin.write(img.tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst)


if __name__ == "__main__":
    main()
