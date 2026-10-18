"""Turn rendered PNG frames into the web image sequence used by the scroll intro.

Usage (from the project root):
    python blender/frames.py night blender/render      # every 2nd frame of a full render
    python blender/frames.py day   blender/render_day  # a render already made with step 2

Writes assets/cine/<mode>/lg/000.webp … (1600 px) and sm/000.webp … (960 px).
"""
import os
import sys

from PIL import Image

mode, src = sys.argv[1], sys.argv[2]
files = sorted(f for f in os.listdir(src) if f.endswith(".png"))
nums = sorted(int(f[2:6]) for f in files)
# keep odd frames (1, 3, 5 … 289) so both modes line up frame for frame
picked = [n for n in nums if n % 2 == 1]

sizes = {"lg": (1600, 900, 74), "sm": (960, 540, 70)}
for key, (w, h, q) in sizes.items():
    out = os.path.join("assets", "cine", mode, key)
    os.makedirs(out, exist_ok=True)
    for i, n in enumerate(picked):
        im = Image.open(os.path.join(src, f"f_{n:04d}.png")).convert("RGB").resize((w, h), Image.LANCZOS)
        im.save(os.path.join(out, f"{i:03d}.webp"), "WEBP", quality=q, method=5)
    total = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print(f"{mode}/{key}: {len(picked)} frames, {total / 1e6:.1f} MB")
