"""Wide opening for the portrait walk-through.

The first landscape frame is extended upward with the building (outpainted once), and the phone shot
opens on that wide view of the whole storefront, then glides in to the normal portrait crop of the
first video frame. The glide slows to the video's own starting push speed at the handover, so it reads
as one continuous drone move. Frames are written as f_0000 … f_<N-1>; the video frames follow them.

    py -3.10 -E higgsfield/portrait_open.py <master dir NNN.webp> <outpaint.png> <band_top> <out dir> [--sheet x.jpg]
"""
import argparse, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portrait_crop import path  # noqa: E402

N = 72               # opening frames (3 s at 24 fps)
START_CX = .55       # centre of the wide start: the NOMA LIVING sign
START_H = 1800       # height (landscape pixels) shown at the very start
VIDEO_RATE = .0047   # the video's own push at its start, measured in the portrait crop (log scale per frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("outpaint"); ap.add_argument("band_top", type=int); ap.add_argument("out")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(a.src) if f.endswith(".webp"))
    f0 = cv2.imread(os.path.join(a.src, names[0]))
    H, W = f0.shape[:2]
    op = cv2.imread(a.outpaint)
    sc = W / op.shape[1]
    T = round(a.band_top * sc)
    full = cv2.resize(op, (W, round(op.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
    # the real frame sits under the building; its top rows fade in from the outpaint's own copy of
    # them, so the join is invisible
    F = 60
    ramp = (np.arange(F) / F)[:, None, None]
    canvas = np.vstack([full[:T], f0]).astype(np.float32)
    canvas[T:T + F] = full[T:T + F] * (1 - ramp) + f0[:F] * ramp
    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(os.path.dirname(a.out), "open_canvas.jpg"), canvas)

    cx_end = path(len(names))[0]
    L = np.log(START_H / H)                  # how much zoom the glide covers (log scale)
    m1 = VIDEO_RATE * N / L                  # end slope that matches the video's push
    os.makedirs(a.out, exist_ok=True)
    tiles = []
    for i in range(N):
        t = i / N                            # frame N would be the first video frame (t = 1)
        g = (-2 * t ** 3 + 3 * t ** 2) + (t ** 3 - t ** 2) * m1
        h = H * np.exp(L * (1 - g))
        w = h * 9 / 16
        sx = 3 * t * t - 2 * t ** 3          # sideways move eases in and out
        x0 = min(max(((1 - sx) * START_CX + sx * cx_end) * W - w / 2, 0), W - w)
        y0 = T + H - h
        A = np.array([[1080 / w, 0, -x0 * 1080 / w], [0, 1920 / h, -y0 * 1920 / h]])
        img = cv2.warpAffine(canvas, A, (1080, 1920), flags=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(a.out, f"f_{i:04d}.png"), img)
        if i % 8 == 0: tiles.append(cv2.resize(img, (216, 384)))
    if a.sheet: cv2.imwrite(a.sheet, np.hstack(tiles))
    print("opening frames", N, "building rows", T, "end slope %.2f" % m1)


if __name__ == "__main__":
    main()
