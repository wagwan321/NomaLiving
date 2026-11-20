"""Cut a portrait (9:16) version out of the landscape walk-through frames, with a crop window that
slides smoothly to keep the subject in view. Same footage, frame for frame.

    py -3.10 -E higgsfield/portrait_crop.py <src dir of NNN.webp> <out dir> [--sheet out.jpg]
"""
import argparse, os
import numpy as np
from PIL import Image

# (frame, centre of the crop as a fraction of the landscape width)
KEYS = [(0, .40), (40, .40), (80, .42), (114, .45), (133, .43), (152, .45), (171, .50), (190, .55),
        (209, .60), (228, .60), (247, .58), (266, .54), (285, .50), (304, .50), (323, .55), (342, .63), (366, .76),
        (378, .76)]


def path(n):
    f, c = np.array(KEYS, float).T
    x = np.interp(np.arange(n), f, c)
    k = 15                                       # soften the corners so the window glides
    ker = np.exp(-0.5 * (np.arange(-2 * k, 2 * k + 1) / k) ** 2); ker /= ker.sum()
    return np.convolve(np.pad(x, 2 * k, mode="edge"), ker, "valid")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--sheet")
    ap.add_argument("--only-sheet", action="store_true")
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(a.src) if f.endswith(".webp"))
    cx = path(len(names))
    os.makedirs(a.out, exist_ok=True)
    tiles = []
    for i, name in enumerate(names):
        if a.only_sheet and i % 19: continue
        im = Image.open(os.path.join(a.src, name)).convert("RGB")
        W, H = im.size
        cw = round(H * 9 / 16)
        x0 = int(round(min(max(cx[i] * W - cw / 2, 0), W - cw)))
        crop = im.crop((x0, 0, x0 + cw, H))
        if not a.only_sheet:
            crop.resize((1080, 1920), Image.LANCZOS).save(os.path.join(a.out, f"f_{i:04d}.png"))
        if i % 19 == 0: tiles.append(crop.resize((180, 320)))
    if a.sheet:
        cols = 10; rows = -(-len(tiles) // cols)
        sheet = Image.new("RGB", (cols * 180, rows * 320))
        for k, t in enumerate(tiles): sheet.paste(t, ((k % cols) * 180, (k // cols) * 320))
        sheet.save(a.sheet)
