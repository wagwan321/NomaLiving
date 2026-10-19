"""Measure on-screen motion of the camera move, in pixels, every quarter frame.

Projects points (corners and centres of every visible mesh) through the camera at time t and
t + 0.25 and records the median distance travelled by points visible in both, at 1920 px wide.
Writes blender/motion.json: {"t": [...], "px": [...]}.

    blender -b blender/noma_entrance.blend --python blender/measure_motion.py
"""
import json
import os
import statistics

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sc = bpy.context.scene
cam = sc.camera
W, H = 1920, 1080
dg = bpy.context.evaluated_depsgraph_get()

pts = []
for ob in sc.objects:
    if ob.type not in {"MESH", "CURVE", "FONT"} or ob.hide_render:
        continue
    corners = [Vector(c) for c in ob.bound_box]
    centre = sum(corners, Vector()) / 8
    pts.append((ob, [centre] + corners))


def project(t):
    f = int(t)
    sc.frame_set(f, subframe=t - f)
    out = {}
    for ob, local in pts:
        mw = ob.matrix_world
        for k, p in enumerate(local):
            v = world_to_camera_view(sc, cam, mw @ p)
            if v.z > 0.05 and -0.1 <= v.x <= 1.1 and -0.1 <= v.y <= 1.1:
                out[(ob.name, k)] = (v.x * W, v.y * H)
    return out


ts, px = [], []
t = 1.0
prev = project(t)
while t < 290:
    nt = round(t + 0.25, 4)
    cur = project(nt)
    common = prev.keys() & cur.keys()
    d = [((cur[k][0] - prev[k][0]) ** 2 + (cur[k][1] - prev[k][1]) ** 2) ** 0.5 for k in common]
    ts.append(t)
    px.append(round(statistics.median(d) * 4, 2) if d else 0.0)   # per whole frame
    prev, t = cur, nt

here = os.path.dirname(bpy.data.filepath)
json.dump({"t": ts, "px": px}, open(os.path.join(here, "motion.json"), "w"))
print("MOTION done", len(ts), "max px/frame", max(px))
