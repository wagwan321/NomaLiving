"""Remove flicker (z-fighting): surfaces that sit exactly on top of each other swap from frame to
frame. Each pair gets a millimetre-scale offset so the surface that should show always wins.

Run once per scene:
    blender -b blender/noma_entrance.blend     --python blender/fix_zfighting.py
    blender -b blender/noma_entrance_day.blend --python blender/fix_zfighting.py
Safe to run again (it only moves faces still at their old position).
"""
import bpy

AX = {"x": 0, "y": 1, "z": 2}


def move_face(name, axis, old, new):
    """Move the vertices of `name` lying on the plane axis == old (world space) to axis == new."""
    ob = bpy.data.objects.get(name)
    if not ob:
        print("ZF missing", name)
        return
    a, mw, inv = AX[axis], ob.matrix_world, ob.matrix_world.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        if abs(w[a] - old) < 1e-4:
            w[a] = new
            v.co = inv @ w
            n += 1
    ob.data.update()
    print(f"ZF {name}: {n} verts {axis} {old} -> {new}")


def nudge(name, axis, d):
    ob = bpy.data.objects.get(name)
    if ob:
        ob.location[AX[axis]] += d
        print(f"ZF {name}: moved {axis} {d:+}")


# lobby side walls vs. the facade walls they meet (right edge flicker during the turn)
move_face("Lobby Wall Avenue", "x", 1.27, 1.268)       # lettering and arc stay in front of it
move_face("Lobby Wall Door Side", "x", -2.87, -2.868)
move_face("Lining Pillar A", "x", -2.87, -2.866)
# indoor pillar vs. outdoor pillar: identical side faces
move_face("Lobby Pillar", "x", -1.69, -1.693)
move_face("Lobby Pillar", "x", -0.91, -0.907)
# window beam vs. header (same underside), entrance platform vs. lobby floor, curb vs. sidewalk
move_face("Window Beam", "z", 2.52, 2.517)
move_face("Platform", "z", 0.0, -0.002)
move_face("Curb", "z", 0.051599, 0.0546)
# key panel glow strip 1 mm off the wall
nudge("Key Halo", "x", -0.003)
# the street seen through the glass at the end: windows and shopfront 1 cm off the facade, 23 m away
shop = bpy.data.objects.get("Opp Shopfront")
if shop and abs(max((shop.matrix_world @ v.co).y for v in shop.data.vertices) + 16.99) < 1e-3:
    for ob in bpy.data.objects:
        if ob.name.startswith("Opp Window") or ob.name == "Opp Shopfront":
            ob.location.y += 0.05
    print("ZF street windows and shopfront moved 5 cm off the facade")

bpy.ops.wm.save_mainfile()
print("ZF saved", bpy.data.filepath)
