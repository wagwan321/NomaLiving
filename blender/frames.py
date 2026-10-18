"""Turn rendered PNG frames into the web image sequence used by the scroll walk-through.

Usage (from the project root):
    python blender/frames.py night blender/render
    python blender/frames.py day   blender/render_day

Every rendered frame is kept, in order: assets/cine/<mode>/000.webp … at the full
render size (1920×1080). Phones load every second one; the page blends between them.
"""
import os
import shutil
import sys

from PIL import Image

mode, src = sys.argv[1], sys.argv[2]
nums = sorted(int(f[2:6]) for f in os.listdir(src) if f.startswith("f_") and f.endswith(".png"))
picked = nums

out = os.path.join("assets", "cine", mode)
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)
for n in picked:
    # file name = render frame - 1, so a partial render (e.g. odd frames only) lands in place
    im = Image.open(os.path.join(src, f"f_{n:04d}.png")).convert("RGB")
    im.save(os.path.join(out, f"{n - 1:03d}.webp"), "WEBP", quality=86, method=6)
total = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
print(f"{mode}: {len(picked)} frames at {im.size[0]}x{im.size[1]}, {total / 1e6:.1f} MB")
