"""Phone walk-through with a wide start: the first frames of the laptop video are shown wide enough
for the whole NOMA LIVING front to fit the phone's width (the screen's dark background above and
below, nothing invented), and the view widens to fill the screen as the video plays on. From frame N
on it is exactly the normal portrait crop (portrait_crop.py output).

    py -3.10 -E higgsfield/portrait_wide.py <master dir NNN.webp> <crop dir f_NNNN.png> <out dir> [--sheet x.jpg]
"""
import argparse, os, shutil, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portrait_crop import path  # noqa: E402

N = 60                 # frames over which the wide view becomes the full-screen crop (2.5 s at 24 fps)
START_W = 1400         # landscape pixels across the phone at the start: the whole sign plus a margin
START_CX = 1018        # centre of the sign
BG = (8, 9, 11)        # the walk-through's background (#0B0908, BGR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("crop"); ap.add_argument("out"); ap.add_argument("--sheet")
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(a.src) if f.endswith(".webp"))
    cx = path(len(names))
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(a.out)
    tiles = []
    for i, name in enumerate(names):
        dst = os.path.join(a.out, f"f_{i:04d}.png")
        if i >= N:
            shutil.copyfile(os.path.join(a.crop, f"f_{i:04d}.png"), dst)
            if i % 12 == 0 and i < N + 24: tiles.append(cv2.resize(cv2.imread(dst), (216, 384)))
            continue
        im = cv2.imread(os.path.join(a.src, name))
        H, W = im.shape[:2]
        cw = round(H * 9 / 16)
        x_end = int(round(min(max(cx[i] * W - cw / 2, 0), W - cw))) + cw / 2   # where the normal crop sits
        t = i / N                                   # frame N is the plain crop (t = 1)
        e = 3 * t * t - 2 * t ** 3
        w = np.exp(np.log(START_W) * (1 - e) + np.log(cw) * e)
        h = w * 16 / 9
        c = START_CX * (1 - e) + x_end * e
        x0, y0 = c - w / 2, H / 2 - h / 2
        s = 1080 / w
        A = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]])
        img = cv2.warpAffine(im, A, (1080, 1920), flags=cv2.INTER_LANCZOS4,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=BG)
        cv2.imwrite(dst, img)
        if i % 12 == 0: tiles.append(cv2.resize(img, (216, 384)))
    if a.sheet: cv2.imwrite(a.sheet, np.hstack(tiles))
    print("frames", len(names), "wide start", N)


if __name__ == "__main__":
    main()
