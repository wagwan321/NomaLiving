"""Render the portrait (9:16) version of the walk-through for phones and upright tablets.

Same camera path as the landscape version, re-framed for a tall screen: 1080×1920 with a
narrower horizontal view (sensor fitted to the width), so the sign, the door and reception
stay in frame instead of being cropped from a landscape picture. Only every second timeline
frame is rendered (that is all phones load).

    blender -b blender/noma_entrance.blend     --python blender/render_portrait.py -- blender/render_portrait_night
    blender -b blender/noma_entrance_day.blend --python blender/render_portrait.py -- blender/render_portrait_day
    (append "test" after the output folder to render a handful of check frames)
"""
import json
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
test = len(args) > 1 and args[1] == "test"
here = os.path.dirname(bpy.data.filepath)
times = json.load(open(os.path.join(here, "timeline.json")))["times"]
os.makedirs(out, exist_ok=True)

sc = bpy.context.scene
cam = sc.camera.data
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
cam.sensor_fit = "HORIZONTAL"
cam.sensor_width = 36 / 1.45          # ≈ the landscape lens ×1.45 across the width
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.12
sc.eevee.taa_render_samples = 28 if not test else 16
sc.render.image_settings.file_format = "PNG"

indices = range(0, len(times), 2)
if test:
    indices = [0, 120, 220, 330, 420, 528]
for i in indices:
    path = os.path.join(out, f"f_{i:04d}.png")
    if not test and os.path.exists(path) and os.path.getsize(path) > 100_000:
        continue
    t = times[i]
    frame = int(t)
    sc.frame_set(frame, subframe=t - frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[portrait] {i}/{len(times)} t={t}", flush=True)
