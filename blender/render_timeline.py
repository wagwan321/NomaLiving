"""Render the walk-through at the moments listed in blender/timeline.json.

The timeline adds in-between frames (e.g. 150.5) where the camera moves fast, so every
rendered step is a similar, small change. Motion blur is kept light so frames stay crisp
when scrubbed by scrolling.

Run headless, once per scene:
  blender -b blender/noma_entrance.blend     --python blender/render_timeline.py -- blender/render_v2_night
  blender -b blender/noma_entrance_day.blend --python blender/render_timeline.py -- blender/render_v2_day
Already-rendered frames are skipped, so an interrupted run can simply be started again.
"""
import json
import os
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1]
here = os.path.dirname(bpy.data.filepath)
times = json.load(open(os.path.join(here, "timeline.json")))["times"]
os.makedirs(out, exist_ok=True)

sc = bpy.context.scene
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.12
sc.eevee.taa_render_samples = 32
sc.render.image_settings.file_format = "PNG"

for i, t in enumerate(times):
    path = os.path.join(out, f"f_{i:04d}.png")
    if os.path.exists(path) and os.path.getsize(path) > 100_000:
        continue
    frame = int(t)
    sc.frame_set(frame, subframe=t - frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[timeline] {i + 1}/{len(times)} t={t}", flush=True)
