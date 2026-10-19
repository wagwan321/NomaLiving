"""Pace of the autoplay walk-through: how long playback spends on each frame.

Run inside Blender (needs the camera animation):
    blender -b blender/noma_entrance.blend --python blender/autoplay_pace.py
Writes blender/autoplay.json: {"pace": [cumulative 0-1 playback time of each walk-through frame],
"seconds": total}. blender/frames.py puts it into assets/js/cine-timeline.js as NOMA_PACE.

Walking moves at an even on-screen pace (the scroll timeline), but the camera never turns faster
than MAX_TURN degrees a second: a quick turn in the animation gets stretched out. The pace is
smoothed so speeding up and slowing down between walking and turning is gradual.
"""
import json
import math
import os

import bpy
from mathutils import Vector

WALK_SECONDS = 9.0      # the walk-through without any turning limit
MAX_TURN = 38.0         # degrees per second the camera may rotate
SMOOTH = 31             # frames in the smoothing window (~0.5 s)

here = os.path.dirname(os.path.abspath(bpy.data.filepath))
tl = json.load(open(os.path.join(here, "timeline.json")))
times, weights = tl["times"], tl["weights"]
scene, cam = bpy.context.scene, bpy.context.scene.camera


def forward(t):
    scene.frame_set(int(t), subframe=t - int(t))
    return (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()


dirs = [forward(t) for t in times]
total_w = sum(weights)
dt = []
for i in range(len(times) - 1):
    walk = weights[i] / total_w * WALK_SECONDS
    turn = math.degrees(dirs[i].angle(dirs[i + 1], 0.0)) / MAX_TURN
    dt.append(max(walk, turn))

# smooth (moving average, edges held) so speed changes are gradual
half = SMOOTH // 2
sm = []
for i in range(len(dt)):
    a, b = max(0, i - half), min(len(dt), i + half + 1)
    sm.append(sum(dt[a:b]) / (b - a))
# a smoothed step may never be shorter than the turning limit
sm = [max(s, math.degrees(dirs[i].angle(dirs[i + 1], 0.0)) / MAX_TURN) for i, s in enumerate(sm)]

cum = [0.0]
for s in sm:
    cum.append(cum[-1] + s)
seconds = cum[-1]
json.dump({"pace": [round(c / seconds, 5) for c in cum], "seconds": round(seconds, 2)},
          open(os.path.join(here, "autoplay.json"), "w"))
print(f"AUTOPLAY {seconds:.2f} s, {len(cum)} frames")
