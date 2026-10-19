"""Give the exterior the real materials seen in the Booking.com photos, then save the file.

  * walls/pillars/soffit: mineral textured render (sandy grain, flecks, soft mottling, matte,
    slightly rounded corners). Each file keeps its own base colour (night vs day grading).
  * front ledge: pitted travertine with horizontal pores
  * storefront platform: vein-cut travertine slabs
  * pavement: grey interlocking concrete pavers

    blender -b blender/noma_entrance.blend     --python blender/upgrade_materials.py
    blender -b blender/noma_entrance_day.blend --python blender/upgrade_materials.py
"""
import bpy


def rgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*c, 1.0)


def fresh_tree(m):
    """Clear the material's nodes, return (nodes, links, principled, coords)."""
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return nt.nodes, nt.links, p, tc.outputs["Object"]


def noise(nodes, links, vec, scale, detail=4.0, rough=0.6):
    n = nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def ramp(nodes, links, fac, stops):
    r = nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = col if len(col) == 4 else rgb(col)
    links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def mix(nodes, links, a, b, fac, blend="MIX"):
    m = nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    links.new(fac, m.inputs["Factor"]) if not isinstance(fac, float) else None
    if isinstance(fac, float):
        m.inputs["Factor"].default_value = fac
    links.new(a, m.inputs["A"]) if not isinstance(a, tuple) else None
    if isinstance(a, tuple):
        m.inputs["A"].default_value = a
    links.new(b, m.inputs["B"]) if not isinstance(b, tuple) else None
    if isinstance(b, tuple):
        m.inputs["B"].default_value = b
    return m.outputs["Result"]


def bump(nodes, links, p, height, strength, distance=0.004, normal=None):
    b = nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    links.new(height, b.inputs["Height"])
    if normal is not None:
        links.new(normal, b.inputs["Normal"])
    return b.outputs["Normal"]


def lin_to_hex_safe(col):
    return tuple(col[:3])


# ---------------------------------------------------------------- textured render (plaster)
def plaster(m):
    # each file's own plaster colour (night grade vs day grade) is kept on the material,
    # so this script can be re-run safely
    if "noma_base" in m:
        base = tuple(m["noma_base"])
    else:
        old = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        base = tuple(old.inputs["Base Color"].default_value) if old else rgb("#C49A5C")
    if len(base) == 3:
        base = base + (1.0,)
    m["noma_base"] = list(base[:3])
    nodes, links, p, co = fresh_tree(m)
    lighter = tuple(min(1, c * 1.10) for c in base[:3]) + (1,)
    darker = tuple(c * 0.86 for c in base[:3]) + (1,)
    # soft cloudy mottling (hand-applied render)
    mott = noise(nodes, links, co, 1.6, detail=3, rough=0.55)
    col = ramp(nodes, links, mott, [(0.35, darker), (0.65, lighter)])
    col = mix(nodes, links, base, col, 0.45)
    # sandy grain: fine speckle of lighter and darker grains
    grain = noise(nodes, links, co, 180, detail=2, rough=0.55)
    speck = ramp(nodes, links, grain, [(0.38, (0, 0, 0, 1)), (0.5, (0.5, 0.5, 0.5, 1)), (0.62, (1, 1, 1, 1))])
    col = mix(nodes, links, col, speck, 0.26, blend="OVERLAY")
    # occasional dark flecks (aggregate)
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 110
    links.new(co, vor.inputs["Vector"])
    fleck = ramp(nodes, links, vor.outputs["Distance"], [(0.0, (0, 0, 0, 1)), (0.09, (1, 1, 1, 1))])
    col = mix(nodes, links, col, fleck, 0.3, blend="MULTIPLY")
    links.new(col, p.inputs["Base Color"])
    # relief: sand grain + gentle trowel undulation
    fine = noise(nodes, links, co, 260, detail=3, rough=0.7)
    trowel = noise(nodes, links, co, 7, detail=2, rough=0.5)
    n1 = bump(nodes, links, p, trowel, 0.12, distance=0.01)
    n2 = bump(nodes, links, p, fine, 0.6, distance=0.004, normal=n1)
    links.new(n2, p.inputs["Normal"])
    rough = ramp(nodes, links, grain, [(0.3, (0.86, 0.86, 0.86, 1)), (0.7, (0.97, 0.97, 0.97, 1))])
    links.new(rough, p.inputs["Roughness"])
    p.inputs["Specular IOR Level"].default_value = 0.35


# ---------------------------------------------------------------- travertine
def travertine(m, cream, vein, pores=0.0, scale=(1.0, 1.0, 1.0)):
    nodes, links, p, co = fresh_tree(m)
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    mp.inputs["Rotation"].default_value = (0.785, 0, 0)   # veins follow y on the floor and z on the walls
    links.new(co, mp.inputs["Vector"])
    v = mp.outputs["Vector"]
    # long linear veins (vein-cut), distorted
    wave = nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 6.0
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 1.5
    links.new(v, wave.inputs["Vector"])
    col = ramp(nodes, links, wave.outputs["Fac"], [(0.15, vein), (0.45, cream), (0.95, cream)])
    cloud = noise(nodes, links, v, 3.5, detail=4)
    col = mix(nodes, links, col, ramp(nodes, links, cloud, [(0.3, (0.9, 0.9, 0.9, 1)), (0.7, (1, 1, 1, 1))]), 1.0, blend="MULTIPLY")
    height = wave.outputs["Fac"]
    if pores:
        # elongated pores typical of travertine
        pm = nodes.new("ShaderNodeMapping")
        pm.inputs["Scale"].default_value = (1.0, 7.0, 7.0)
        links.new(co, pm.inputs["Vector"])
        vor = nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 34
        links.new(pm.outputs["Vector"], vor.inputs["Vector"])
        hole = ramp(nodes, links, vor.outputs["Distance"], [(0.0, (0, 0, 0, 1)), (pores, (1, 1, 1, 1))])
        col = mix(nodes, links, col, hole, 0.45, blend="MULTIPLY")
        height = vor.outputs["Distance"]
    links.new(col, p.inputs["Base Color"])
    links.new(bump(nodes, links, p, height, 0.25, distance=0.004), p.inputs["Normal"])
    p.inputs["Roughness"].default_value = 0.42


# ---------------------------------------------------------------- interlocking pavers
def pavers(m):
    nodes, links, p, co = fresh_tree(m)
    br = nodes.new("ShaderNodeTexBrick")
    br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 0.22
    br.inputs["Row Height"].default_value = 0.11
    br.inputs["Mortar Size"].default_value = 0.008
    br.inputs["Mortar Smooth"].default_value = 0.4
    br.inputs["Color1"].default_value = rgb("#8d8a86")
    br.inputs["Color2"].default_value = rgb("#7a7672")
    br.inputs["Mortar"].default_value = rgb("#4f4b47")
    links.new(co, br.inputs["Vector"])
    grit = noise(nodes, links, co, 180, detail=3)
    col = mix(nodes, links, br.outputs["Color"], ramp(nodes, links, grit, [(0.35, (0.85, 0.85, 0.85, 1)), (0.65, (1, 1, 1, 1))]), 1.0, blend="MULTIPLY")
    links.new(col, p.inputs["Base Color"])
    n1 = bump(nodes, links, p, br.outputs["Fac"], 0.45, distance=0.01)
    links.new(bump(nodes, links, p, grit, 0.25, distance=0.002, normal=n1), p.inputs["Normal"])
    p.inputs["Roughness"].default_value = 0.82


M = bpy.data.materials
plaster(M["Plaster Ochre"])
travertine(M["Travertine"], rgb("#E6D9C4"), rgb("#CDBB9C"))
if "Concrete" in M:
    travertine(M["Concrete"], rgb("#D2C9B9"), rgb("#BDB29E"), pores=0.07, scale=(1.0, 1.0, 1.0))
pavers(M["Pavers"])

# softly rounded corners on the rendered walls
for name in ("Pillar A", "Pillar B", "Door Header", "Window Header", "Wall C", "Right Block", "Nook Back", "Nook Side", "Soffit", "Ledge"):
    ob = bpy.data.objects.get(name)
    if ob and not ob.modifiers.get("Round"):
        bv = ob.modifiers.new("Round", "BEVEL")
        bv.width = 0.015
        bv.segments = 3
        bv.harden_normals = True
        for poly in ob.data.polygons:
            poly.use_smooth = True

bpy.ops.wm.save_mainfile()
print("MATERIALS upgraded:", bpy.data.filepath)
