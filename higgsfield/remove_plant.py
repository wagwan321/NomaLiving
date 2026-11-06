"""Remove the invented potted plant from the corridor wall in shot 2 (free, frame by frame).

In every frame between --from and --to, green regions that sit on the plain white wall are the
plant (green areas inside the posters are surrounded by colour, not white, and are kept). The plant
plus its grey pot below it are masked and filled in from the surrounding wall (OpenCV inpainting).

    python -E higgsfield/remove_plant.py <in.mp4> <out.mp4> --from 0.5 --to 2.6 [--keep-right 0.62 --keep-right-until 1.5]
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
    ap.add_argument("--from", dest="t0", type=float, default=0.5)
    ap.add_argument("--to", dest="t1", type=float, default=2.6)
    ap.add_argument("--keep-right", type=float, default=0.62, help="share of the width kept untouched (real cacti)")
    ap.add_argument("--keep-right-until", type=float, default=1.5)
    a = ap.parse_args()
    info = subprocess.run([FF, "-i", a.src], capture_output=True, text=True).stderr
    W, H = map(int, re.search(r", (\d{3,4})x(\d{3,4})", info).groups())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
                            "-pix_fmt", "yuv420p", a.dst], stdin=subprocess.PIPE)
    sc = W / 1920
    for i in range(n):
        f = np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3).copy()
        t = i / FPS
        if a.t0 <= t <= a.t1:
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            green = ((hsv[..., 0] >= 24) & (hsv[..., 0] < 95) & (hsv[..., 1] > 42) & (hsv[..., 2] > 35)).astype(np.uint8)
            if t < a.keep_right_until:
                green[:, int(W * a.keep_right):] = 0
            green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((int(15 * sc) | 1,) * 2, np.uint8))
            white = ((hsv[..., 1] < 80) & (hsv[..., 2] > 115)).astype(np.uint8)   # the plain beige/white wall
            # protect long vertical dark structures (door frame, handle): never paint over them
            dark = (hsv[..., 2] < 70).astype(np.uint8)
            protect = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((int(160 * sc), 1), np.uint8))
            protect = cv2.dilate(protect, np.ones((int(9 * sc) | 1,) * 2, np.uint8))
            num, lab, stats, _ = cv2.connectedComponentsWithStats(green)
            mask = np.zeros((H, W), np.uint8)
            for c in range(1, num):
                x, y, w, h, area = stats[c]
                if area < 150 * sc * sc:
                    continue
                blob = (lab == c).astype(np.uint8)
                ring = cv2.dilate(blob, np.ones((int(41 * sc) | 1,) * 2, np.uint8)) - blob
                if white[ring > 0].mean() < 0.28:              # not on the white wall: part of a poster
                    continue
                mask |= blob
                # the pot and its shadow below the leaves: anything clearly darker than the wall there
                wall_v = np.median(hsv[..., 2][ring > 0])
                y0, y1 = max(0, y + h // 2), min(H, y + h + int(1.1 * h))
                x0, x1 = max(0, x - int(0.15 * w)), min(W, x + w + int(0.15 * w))
                pot = (hsv[y0:y1, x0:x1, 2] < wall_v - 22).astype(np.uint8)
                pot = cv2.morphologyEx(pot, cv2.MORPH_CLOSE, np.ones((int(11 * sc) | 1,) * 2, np.uint8))
                mask[y0:y1, x0:x1] |= pot
            if mask.any():
                mask = cv2.dilate(mask, np.ones((int(17 * sc) | 1,) * 2, np.uint8))
                mask[protect > 0] = 0
                f = cv2.inpaint(f, mask * 255, int(9 * sc) + 1, cv2.INPAINT_TELEA)
            # green fringe left right next to the door frame/handle: turn it the colour of the wall
            hsv2 = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            near = cv2.dilate(protect, np.ones((int(61 * sc) | 1,) * 2, np.uint8)) > 0
            fringe = near & (hsv2[..., 0] >= 24) & (hsv2[..., 0] < 95) & (hsv2[..., 1] > 35) & (hsv2[..., 2] > 60)
            if t < a.keep_right_until:
                fringe[:, int(W * a.keep_right):] = False
            if fringe.any():
                wallpx = hsv2[(hsv2[..., 1] < 60) & (hsv2[..., 2] > 115) & near]
                if len(wallpx):
                    hh, ss = np.median(wallpx[:, 0]), np.median(wallpx[:, 1])
                    soft = cv2.GaussianBlur(fringe.astype(np.float32), (0, 0), 3 * sc)
                    tgt = hsv2.copy(); tgt[..., 0] = hh; tgt[..., 1] = ss
                    rec = cv2.cvtColor(tgt, cv2.COLOR_HSV2BGR).astype(np.float32)
                    f = (rec * soft[..., None] + f * (1 - soft[..., None])).astype(np.uint8)
        enc.stdin.write(f.tobytes())
    enc.stdin.close(); enc.wait()
    print(a.dst, n, "frames")


if __name__ == "__main__":
    main()
