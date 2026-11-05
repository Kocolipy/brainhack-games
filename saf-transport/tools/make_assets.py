"""Build low-poly assets for SAF Transport (5-tonner driving demo in SAFTI City).

Run headless:  blender.exe -b --python tools/make_assets.py -- assets
Writes cab.glb (driver's-eye cab interior, steering wheel tagged kind=wheel), soldier.glb (Body + LegL/LegR) and city.glb
(SAFTI City; glTF extras -> three.js userData: kind=bldg|roof|deco|beacon, depot=<name>, roads=<json> on "Roads"),
plus preview_cab.png / preview_city.png / preview_map.png.

Conventions: 1 unit = 1 m, Blender +Y forward/north -> three.js -Z.
Cab origin = driver's eye; the truck is right-hand drive, so the cab extends mostly to the driver's left (-X).
"""
import math
import os
import random
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
random.seed(5)


def mat(name, rgb, emit=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def mesh_obj(name, verts, faces, mats):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def box(name, x0, y0, z0, x1, y1, z1, m):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return mesh_obj(name, v, f, [m])


def cyl(name, r, depth, loc, m, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    return o


def text(name, body, size, loc, m):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi / 2, 0, 0))  # stands up, readable from -Y
    o = bpy.context.object
    o.data.body, o.data.size, o.data.extrude = body, size, 0.02
    o.data.align_x, o.data.align_y = "CENTER", "CENTER"
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.name = name
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def join(name, parts):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name, o.data.name = name, "M_" + name
    return o


def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_extras=True)


# ---------- cab interior (origin = driver's eye) ----------
olive, dark, dash = mat("Olive", (0.2, 0.24, 0.13)), mat("Dark", (0.04, 0.04, 0.035)), mat("Dash", (0.12, 0.12, 0.11))
roof, gauge = mat("Headliner", (0.3, 0.32, 0.24)), mat("Gauge", (0.85, 0.85, 0.75), emit=0.4)
L, R = -1.8, 0.75  # cab inner walls (driver sits near the right wall)
cab = join("Cab", [
    box("Dashboard", L, 0.55, -1.0, R, 1.15, -0.5, dash),
    box("Binnacle", -0.22, 0.62, -0.5, 0.22, 0.85, -0.38, dark),
    cyl("GaugeL", 0.06, 0.02, (-0.1, 0.62, -0.44), gauge, rot=(math.pi / 2, 0, 0)),
    cyl("GaugeR", 0.06, 0.02, (0.1, 0.62, -0.44), gauge, rot=(math.pi / 2, 0, 0)),
    box("ScreenSill", L, 1.1, -0.55, R, 1.22, -0.42, olive),
    box("PillarL", L - 0.05, 1.05, -0.55, L + 0.12, 1.22, 0.6, olive),
    box("PillarR", R - 0.12, 1.05, -0.55, R + 0.05, 1.22, 0.6, olive),
    box("PillarMid", -0.6, 1.12, -0.45, -0.5, 1.2, 0.55, olive),  # split windscreen
    box("Header", L - 0.05, 0.9, 0.42, R + 0.05, 1.22, 0.7, olive),
    box("Roof", L - 0.05, -0.8, 0.6, R + 0.05, 1.22, 0.75, roof),
    box("DoorR", R, -0.6, -1.3, R + 0.08, 1.1, -0.35, olive),
    box("DoorL", L - 0.08, -0.6, -1.3, L, 1.1, -0.35, olive),
    box("BPillarR", R, -0.7, -0.35, R + 0.08, -0.55, 0.6, olive),
    box("BPillarL", L - 0.08, -0.7, -0.35, L, -0.55, 0.6, olive),
    box("MirrorArmR", R + 0.05, 0.95, -0.05, R + 0.35, 1.0, 0.0, dark),
    box("MirrorR", R + 0.3, 0.93, -0.35, R + 0.5, 1.0, 0.1, dark),
    box("MirrorArmL", L - 0.35, 0.95, -0.05, L - 0.05, 1.0, 0.0, dark),
    box("MirrorL", L - 0.5, 0.93, -0.35, L - 0.3, 1.0, 0.1, dark),
])
bpy.ops.mesh.primitive_torus_add(major_radius=0.23, minor_radius=0.028, major_segments=24, minor_segments=8)
rim = bpy.context.object
rim.data.materials.append(dark)
spokes = [box(f"Spoke{i}", -0.015, 0, -0.012, 0.015, 0.21, 0.012, dark) for i in range(3)]
for i, s in enumerate(spokes):  # three spokes, one pointing down (towards the driver's lap)
    s.rotation_euler.z = math.pi + (i - 1) * 2 * math.pi / 3
    bpy.ops.object.select_all(action="DESELECT")
    s.select_set(True)
    bpy.context.view_layer.objects.active = s
    bpy.ops.object.transform_apply(rotation=True)
wheel = join("Wheel", [rim, *spokes, cyl("Hub", 0.06, 0.06, (0, 0, 0), dash)])
wheel.location = (0, 0.5, -0.55)
wheel.rotation_euler.x = math.radians(50)  # bus-style tilt; the game spins it about its local axis (three.js +Y)
wheel["kind"] = "wheel"

# ---------- SAFTI City (Phase 1, Sector 2) ----------
# Layout follows the MINDEF artist's impression (Straits Times graphic, 1 Jul 2019) and Pioneer photos (19 Mar 2025):
#   west  = high-density commercial-residential area: Skopek Hotel tower, town hall, shophouses, shopping centre
#   east  = complex urban centre: Transport Hub (Poyan station + bus interchange + office tower), Tengah Mall,
#           Brani Museum (footbridge from the hub), petrol kiosk, office carpark, high-security compound,
#           condominium with mall, school, HDB, shophouses
# shortcut: positions/sizes are eyeballed from an oblique artist's impression and photos, not surveyed; refine if a plan appears.
import bmesh
import json
from mathutils import Vector

concrete, concrete_lt = mat("Concrete", (0.72, 0.72, 0.7)), mat("ConcreteLight", (0.84, 0.84, 0.82))
louvre, marker, roof_grey = mat("Louvre", (0.05, 0.05, 0.06)), mat("Marker", (0.95, 0.85, 0.1)), mat("RoofGrey", (0.36, 0.38, 0.42))
grass, asphalt, pad_m = mat("Grass", (0.3, 0.42, 0.16)), mat("Asphalt", (0.33, 0.33, 0.33)), mat("DepotPad", (0.75, 0.65, 0.2))
train_m, stripe = mat("TrainBody", (0.8, 0.82, 0.85)), mat("TrainStripe", (0.75, 0.12, 0.12))
leaf, trunk, label_m = mat("Leaf", (0.12, 0.28, 0.1)), mat("Trunk", (0.25, 0.18, 0.1)), mat("Label", (0.08, 0.08, 0.08))
beacon_m = mat("Beacon", (1.0, 0.8, 0.1), emit=3.0)
BOX_F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]


class MB:
    """Accumulates boxes/prisms into one mesh (one object per building keeps object count low)."""
    def __init__(s):
        s.v, s.f, s.m = [], [], []

    def box(s, x0, y0, z0, x1, y1, z1, mi):
        n = len(s.v)
        s.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        s.f += [[n + i for i in f] for f in BOX_F]
        s.m += [mi] * 6

    def poly(s, pts, z, mi):  # flat polygon (road discs etc.)
        n = len(s.v)
        s.v += [(x, y, z) for x, y in pts]
        s.f.append(list(range(n, n + len(pts))))
        s.m.append(mi)

    def prism(s, x0, y0, x1, y1, z0, z1, mi):  # pitched roof, ridge along the long side
        n = len(s.v)
        if x1 - x0 >= y1 - y0:
            ym = (y0 + y1) / 2
            s.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, ym, z1), (x1, ym, z1)]
        else:
            xm = (x0 + x1) / 2
            s.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (xm, y0, z1), (xm, y1, z1)]
        faces = [[0, 3, 2, 1], [0, 1, 5, 4], [2, 3, 4, 5], [1, 2, 5], [3, 0, 4]] if x1 - x0 >= y1 - y0 else \
                [[0, 3, 2, 1], [0, 1, 4], [1, 2, 5, 4], [2, 3, 5], [3, 0, 4, 5]]
        s.f += [[n + i for i in f] for f in faces]
        s.m += [mi] * 5

    def obj(s, name, mats):
        me = bpy.data.meshes.new("M_" + name)
        me.from_pydata(s.v, [], s.f)
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", s.m)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        scene.collection.objects.link(o)
        return o


BMATS = [concrete, louvre, marker, concrete_lt, roof_grey]
city, footprints, used_nums = [], [], set()  # footprints: collider rects for the layout self-checks


def tag(o, kind):
    o["kind"] = kind
    city.append(o)
    return o


def building(x0, y0, x1, y1, floors, fh=3.5, z0=0.0, label=None, num=None, pitched=False, kind="bldg"):
    """SAFTI City style: bare concrete, floor bands, black louvred windows with yellow target markers, roof railing."""
    mb, top = MB(), z0 + floors * fh
    mb.box(x0, y0, z0, x1, y1, top, 0)
    for f in range(1, floors + 1):
        z = z0 + f * fh - 0.3
        mb.box(x0 - 0.12, y0 - 0.12, z, x1 + 0.12, y1 + 0.12, z + 0.3, 3)
    faces = [((x0, y0), (x1, y0), (0, -1)), ((x1, y1), (x0, y1), (0, 1)), ((x0, y1), (x0, y0), (-1, 0)), ((x1, y0), (x1, y1), (1, 0))]
    for f in range(floors):
        zc = z0 + f * fh + 1.6
        for (ax, ay), (bx, by), (nx, ny) in faces:
            L = math.hypot(bx - ax, by - ay)
            n = max(1, int(L / 5))
            for k in range(n):
                t = (k + 0.5) / n
                cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
                hw = 0.9
                wx0, wx1 = (cx - hw, cx + hw) if nx == 0 else sorted((cx, cx + nx * 0.06))
                wy0, wy1 = (cy - hw, cy + hw) if ny == 0 else sorted((cy, cy + ny * 0.06))
                mb.box(wx0, wy0, zc - 0.65, wx1, wy1, zc + 0.65, 1)
                if k % 2 == 0:
                    mx0, mx1 = (cx - 0.18, cx + 0.18) if nx == 0 else sorted((cx, cx + nx * 0.07))
                    my0, my1 = (cy - 0.18, cy + 0.18) if ny == 0 else sorted((cy, cy + ny * 0.07))
                    mb.box(mx0, my0, zc - 1.05, mx1, my1, zc - 0.75, 2)
    if pitched:
        mb.prism(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, top, top + 2.5, 4)
    else:  # roof railing
        for a in ((x0, y0, x1, y0 + 0.15), (x0, y1 - 0.15, x1, y1), (x0, y0, x0 + 0.15, y1), (x1 - 0.15, y0, x1, y1)):
            mb.box(a[0], a[1], top, a[2], a[3], top + 1.0, 3)
    global_num = num or next(n for n in range(201, 400) if n not in used_nums and n not in RESERVED)
    used_nums.add(global_num)
    name = f"S{global_num}" + (f" {label}" if label else "")
    o = mb.obj(name.replace(" ", "_"), BMATS)
    sign = text("Lbl", name, 0.9 if label else 0.7, ((x0 + x1) / 2, y0 - 0.2, z0 + min(fh * floors - 0.8, 4.6)), label_m)
    o = join(name.replace(" ", "_"), [o, sign])
    if kind == "bldg":
        footprints.append((x0, y0, x1, y1, name))
    return tag(o, kind)


RESERVED = {221, 228, 230, 236, 238, 241, 252, 259, 261, 268}  # numbers seen in photos; used for named landmarks

# --- roads: polylines (x, y) with widths; the game draws the same data on the minimap
def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


RX, RY, RC = 190, 175, 30  # perimeter road: rounded rectangle
ring = (arc(RX - RC, -RY + RC, RC, -math.pi / 2, 0, 6) + arc(RX - RC, RY - RC, RC, 0, math.pi / 2, 6)
        + arc(-RX + RC, RY - RC, RC, math.pi / 2, math.pi, 6) + arc(-RX + RC, -RY + RC, RC, math.pi, 1.5 * math.pi, 6))
ring.append(ring[0])
RB = (-55, -10)  # roundabout with grass island, between Tengah Mall / Brani Museum and Skopek Hotel
ROADS = [
    (ring, 10),
    (arc(RB[0], RB[1], 16, 0, 2 * math.pi, 24), 9),
    ([(8, -10), (-39, -10)], 10),                                          # hub -> roundabout (Mall | Museum either side)
    ([(-71, -10), (-130, -20), (-190, -15)], 10),                          # roundabout -> west past Skopek Hotel
    ([(8, -175), (8, -60), (8, 30), (5, 100), (0, 175)], 10),              # north-south past the hub's west face
    ([(8, -60), (70, -62), (130, -60), (190, -50)], 10),                   # south road: bus interchange entrance
    ([(-55, 6), (-60, 60), (-80, 120), (-90, 175)], 9),                    # roundabout -> north
    ([(-55, -26), (-50, -80), (-30, -150), (-25, -175)], 9),               # roundabout -> south
    ([(8, 30), (60, 28), (125, 30), (190, 40)], 10),                       # north of the hub
    ([(-130, -20), (-120, 40), (-115, 100), (-80, 120)], 8),               # west lanes
    ([(-130, -20), (-120, -80), (-90, -150), (-60, -175)], 8),
    ([(130, -60), (120, -100), (100, -175)], 8),                           # to the school
    ([(0, -175), (0, -200)], 10),                                          # spur to the motor pool (outside the city)
]
mb = MB()
for pts, w in ROADS:
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / L * w / 2, (bx - ax) / L * w / 2
        mb.poly([(ax - nx, ay - ny), (bx - nx, by - ny), (bx + nx, by + ny), (ax + nx, ay + ny)], 0.02, 0)
    for x, y in pts:  # round joints
        mb.poly(arc(x, y, w / 2, 0, 2 * math.pi, 12)[:-1], 0.02, 0)
roads = mb.obj("Roads", [asphalt])
roads["roads"] = json.dumps([[[round(x, 1), round(y, 1)] for x, y in pts] + [w] for pts, w in ROADS])
roads["edge"] = 230
city += [box("Ground", -420, -420, -0.1, 420, 420, 0, grass), roads]
tag(cyl("Island", 10.5, 0.3, (RB[0], RB[1], 0.15), grass, verts=24), "deco")


def pad(name, x0, y0, x1, y1):
    p = box("Depot_" + name.replace(" ", "_"), x0, y0, 0.03, x1, y1, 0.06, pad_m)
    p["depot"] = name
    city.append(p)


def bus(x, y):  # parked bus along x
    mb = MB()
    mb.box(x, y, 0.4, x + 12, y + 2.6, 3.4, 0)
    mb.box(x + 0.5, y - 0.05, 1.8, x + 11.5, y + 2.65, 2.9, 1)
    mb.box(x, y - 0.04, 1.0, x + 12, y + 2.64, 1.4, 2)
    footprints.append((x, y, x + 12, y + 2.6, "bus"))
    return tag(mb.obj("Bus", [train_m, louvre, stripe]), "bldg")


def slab(name, x0, y0, x1, y1, z0, z1, kind, m=concrete):
    o = tag(box(name, x0, y0, z0, x1, y1, z1, m), kind)
    if kind == "bldg":
        footprints.append((x0, y0, x1, y1, name))
    return o


# --- Transport Hub (S221): Poyan station hall with a decommissioned train | drive-through bus interchange | office tower
slab("HubFloor", 15, -62, 95, 2, 0, 0.03, "deco", asphalt)
slab("StationRoof", 15, -40, 45, 20, 7, 8.5, "roof")
slab("InterchangeRoof", 45, -40, 95, 20, 7, 8.5, "roof")
for px, py in [(15, -40), (15, -10), (15, 20), (45, -40), (45, -10), (70, -40), (95, -40)]:
    slab("Pillar", px - 0.6, py - 0.6, px + 0.6, py + 0.6, 0, 7, "bldg")
slab("Platform", 22, -36, 29, 10, 0, 1.1, "bldg")
city.append(text("PoyanSign", "POYAN", 1.2, (25.5, -36.3, 4.5), label_m))
for k, y in enumerate((-36, -13)):  # two stationary MRT cars along the platform
    mb = MB()
    mb.box(30, y, 0.4, 33.2, y + 22, 4.0, 0)
    mb.box(29.94, y + 1, 1.9, 33.26, y + 21, 3.0, 1)
    mb.box(29.96, y, 1.2, 33.24, y + 22, 1.6, 2)
    footprints.append((30, y, 33.2, y + 22, "train"))
    tag(mb.obj(f"Train{k}", [train_m, louvre, stripe]), "bldg")
building(45, 2, 95, 20, 2, label="POYAN INTERCHANGE", num=221)  # bus bays building at the back of the interchange
bus(50, -2.8)
bus(68, -2.8)
pad("Poyan Interchange", 50, -36, 90, -10)
building(95, -40, 125, 20, 2, fh=4.25)
building(98, -32, 122, 12, 10, z0=8.5, label="MURAI TOWER", num=238, kind="deco")  # 12-storey office over the podium
mb = MB()  # footbridge from the hub to Brani Museum, over the north-south road
mb.box(-2, 20, 7, 15, 23.5, 7.6, 0)
mb.box(-2, 20, 7.6, 15, 20.2, 8.7, 3)
mb.box(-2, 23.3, 7.6, 15, 23.5, 8.7, 3)
tag(mb.obj("Footbridge", [concrete, concrete_lt]), "deco")

# --- around the hub (complex urban centre)
building(-34, -50, -2, -22, 4, label="TENGAH MALL", num=228)
pad("Tengah Mall", -32, -64, -6, -54)
building(-34, 2, -2, 16, 4, label="BRANI MUSEUM", num=230)
building(-34, 16, -20, 35, 3)
pad("Brani Museum", -18, 19, -4, 34)
building(50, 38, 110, 70, 5, fh=3.0, label="OFFICE CARPARK")
for a in ((125, 45, 178, 45.6), (125, 99.4, 178, 100), (177.4, 45, 178, 100), (125, 45, 125.6, 60), (125, 72, 125.6, 100)):
    slab("CompoundWall", *a, 0, 3.5, "bldg", concrete_lt)  # high-security compound, gate on the west wall
building(145, 60, 170, 90, 2, label="HIGH-SECURITY COMPOUND")
pad("Secure Compound", 129, 52, 141, 92)
building(135, -40, 180, 10, 2, fh=4.5, label="CONDO MALL")
building(148, -30, 172, 0, 10, z0=9, label="CONDOMINIUM", kind="deco")
pad("Condo Mall", 140, -52, 176, -42)
building(115, -160, 165, -145, 3, label="SCHOOL", num=252)
building(145, -145, 165, -100, 3)
pad("School", 117, -140, 140, -106)
building(20, -130, 60, -112, 10, label="HDB")
building(-24, -112, 0, -100, 2, pitched=True, label="SHOPHOUSES")
building(-24, -140, 0, -128, 3, pitched=True)
slab("KioskCanopy", -30, 70, -8, 86, 5.5, 6.3, "roof", concrete_lt)
for px in (-29, -9):
    for py in (71, 85):
        slab("KioskPillar", px - 0.4, py - 0.4, px + 0.4, py + 0.4, 0, 5.5, "bldg")
building(-30, 89, -18, 97, 1, label="PETROL KIOSK")
pad("Petrol Kiosk", -27, 73, -11, 83)

# --- high-density commercial-residential area (west)
building(-115, 0, -78, 36, 2, fh=4.5)
building(-105, 8, -84, 30, 10, z0=9, label="SKOPEK HOTEL", num=236, kind="deco")  # 12-storey tower on a 2-storey podium
pad("Skopek Hotel", -112, -14, -82, -4)
building(-165, 15, -135, 50, 3, label="TOWN HALL", num=241)
building(-154, 28, -146, 36, 5, num=259)  # clock tower
pad("Town Hall", -132, 18, -112, 48)
building(-165, -75, -130, -63, 2, pitched=True, label="SHOPHOUSES")
building(-165, -100, -130, -88, 3, pitched=True)
building(-85, -135, -56, -100, 3, fh=4.5, label="SHOPPING CENTRE", num=261)

# --- motor pool (vehicle staging outside the perimeter road; not part of SAFTI City itself)
building(-25, -225, -5, -210, 1, fh=5, label="MOTOR POOL", num=268)
pad("Motor Pool", -22, -205, 22, -185)

# --- fill the rest with the dense 2-6 storey blocks seen in the photos (seeded, checked against roads/buildings)
pads = [(o.bound_box, o) for o in city if "depot" in o]
pad_rects = [(min(v[0] for v in bb), min(v[1] for v in bb), max(v[0] for v in bb), max(v[1] for v in bb)) for bb, _ in pads]


def road_clear(r, margin):
    for pts, w in ROADS:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay)
            for i in range(int(L) + 1):
                px, py, e = ax + (bx - ax) * i / max(L, 1), ay + (by - ay) * i / max(L, 1), w / 2 + margin
                if r[0] - e < px < r[2] + e and r[1] - e < py < r[3] + e:
                    return False
    return True


def rect_clear(r, rects, gap):
    return all(r[2] + gap <= q[0] or q[2] + gap <= r[0] or r[3] + gap <= q[1] or q[3] + gap <= r[1] for q in rects)


in_city = lambda r: -RX + 8 < r[0] and r[2] < RX - 8 and -RY + 8 < r[1] and r[3] < RY - 8 and not (
    (abs(r[0]) > RX - RC - 5 or abs(r[2]) > RX - RC - 5) and (abs(r[1]) > RY - RC - 5 or abs(r[3]) > RY - RC - 5))
for _ in range(4000):
    if len(footprints) >= 95:  # ~71 buildings plus pillars/walls/train/bus colliders
        break
    w, d = random.uniform(12, 22), random.uniform(12, 20)
    x, y = random.uniform(-RX, RX), random.uniform(-RY, RY)
    r = (x, y, x + w, y + d)
    if in_city(r) and road_clear(r, 4) and rect_clear(r, footprints, 7) and rect_clear(r, pad_rects, 4):
        building(*r, random.choice([2, 3, 3, 4, 4, 5, 6]), pitched=random.random() < 0.15)

# --- secondary jungle around the site (one decorative mesh)
trees = []
while len(trees) < 2 * 260:
    x, y = random.uniform(-400, 400), random.uniform(-400, 400)
    if (abs(x) < RX + 15 and abs(y) < RY + 15) or (-40 < x < 40 and -240 < y < -170):
        continue
    h = random.uniform(8, 16)
    trees.append(cyl("Trunk", 0.5, h * 0.6, (x, y, h * 0.3), trunk, verts=5))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=h * 0.35, location=(x, y, h * 0.75), scale=(1, 1, 0.7))
    bpy.context.object.data.materials.append(leaf)
    trees.append(bpy.context.object)
tag(join("Jungle", trees), "deco")

beacon = cyl("Beacon", 4, 40, (0, 0, 20), beacon_m, verts=16)  # objective marker; the game moves it
tag(beacon, "beacon")

# self-checks: wheel faces the driver; landmarks and fill buildings stay off the roads; depots and count are sane
axis = wheel.matrix_world.to_3x3() @ Vector((0, 0, 1))
assert axis.y < -0.5 and axis.z > 0.5, f"wheel axis should point back/up at the driver: {tuple(axis)}"
blocked = [f[4] for f in footprints if not road_clear(f, 0.5)]
assert not blocked, f"buildings on roads: {blocked}"
n_bldg = len([o for o in city if o.get("kind") in ("bldg", "deco") and o.name.startswith("S2")])
depot_names = [o["depot"] for o in city if "depot" in o]
assert len(depot_names) == len(set(depot_names)) >= 10, depot_names
print("named buildings:", n_bldg, "colliders:", len(footprints), "depots:", depot_names)

# ---------- soldier (origin at feet, faces +Y; legs pivot at the hip so the game can swing them) ----------
camo, camo_dk, skin, boot = mat("Camo", (0.24, 0.3, 0.17)), mat("CamoDark", (0.15, 0.19, 0.11)), mat("Skin", (0.62, 0.45, 0.33)), mat("Boot", (0.04, 0.04, 0.04))
# safe hang: rifle slung across the front on its sling, muzzle down and slightly forward, hands off the trigger
rifle = join("Rifle", [box("Gun", -0.03, -0.04, -0.75, 0.03, 0.04, 0, boot),           # body, butt at the origin
                       box("Mag", -0.025, 0.04, -0.42, 0.025, 0.12, -0.3, boot)])      # magazine on the front face
rifle.location, rifle.rotation_euler = (0.06, 0.2, 1.38), (0.3, 0.25, 0)
sling = box("Sling", -0.02, -0.01, -0.3, 0.02, 0.01, 0.3, camo_dk)  # strap from the left shoulder down to the right hip
sling.location, sling.rotation_euler = (0, 0.15, 1.17), (0, -0.7, 0)
bpy.context.view_layer.update()
rv = [rifle.matrix_world @ v.co for v in rifle.data.vertices]
muzzle = min(rv, key=lambda v: v.z)
assert 0.5 < muzzle.z < 0.75 and muzzle.y > 0.2, f"rifle should hang muzzle-down in front: {tuple(muzzle)}"
torso = join("Body", [
    box("Torso", -0.2, -0.12, 0.9, 0.2, 0.12, 1.45, camo),
    box("Vest", -0.22, -0.14, 1.05, 0.22, 0.14, 1.4, camo_dk),
    box("ArmL", -0.3, -0.06, 0.95, -0.2, 0.08, 1.42, camo),
    box("ArmR", 0.2, -0.06, 0.95, 0.3, 0.08, 1.42, camo),
    box("Head", -0.1, -0.1, 1.47, 0.1, 0.1, 1.67, skin),
    box("Helmet", -0.14, -0.14, 1.6, 0.14, 0.14, 1.76, camo_dk),
    rifle, sling,
])
legs = []
for s, name in ((-1, "LegL"), (1, "LegR")):
    leg = join(name, [box("Leg", -0.08, -0.08, -0.82, 0.08, 0.08, 0, camo), box("Boot", -0.09, -0.09, -0.9, 0.09, 0.14, -0.78, boot)])
    leg.location = (s * 0.1, 0, 0.9)
    legs.append(leg)
assert max(v.co.z for v in torso.data.vertices) < 1.8 and min(v.co.y for v in torso.data.vertices) < -0.1

os.makedirs(out, exist_ok=True)
p = lambda f: os.path.join(out, f)
export(p("cab.glb"), [cab, wheel])
export(p("city.glb"), city)
export(p("soldier.glb"), [torso, *legs])
for o in (torso, *legs):  # keep it out of the city previews (it stands at the origin)
    o.hide_render = True

# ---------- previews (workbench) ----------
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(cam)
cam.data.sensor_fit, cam.data.angle_y, cam.data.clip_start, cam.data.clip_end = "VERTICAL", math.radians(70), 0.05, 2000
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
bpy.ops.wm.save_as_mainfile(filepath=p("saf.blend"))  # render relative to the .blend (Windows Blender + WSL paths)
eye = Vector((-48.5, -60, 2.6))  # driver's view on the road north to the roundabout, Skopek Hotel ahead-left
for o in (cab, wheel):
    o.location += eye
cam.location, cam.rotation_euler = eye, (math.radians(82), 0, 0)
scene.render.filepath = "//preview_cab.png"
bpy.ops.render.render(write_still=True)
cam.location, cam.rotation_euler = (150, -330, 260), (math.radians(50), 0, math.radians(25))
scene.render.filepath = "//preview_city.png"
bpy.ops.render.render(write_still=True)
cam.data.type, cam.data.ortho_scale = "ORTHO", 470
cam.location, cam.rotation_euler = (0, -15, 300), (0, 0, 0)
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.filepath = "//preview_map.png"
bpy.ops.render.render(write_still=True)
cam.data.type = "PERSP"  # soldier close-up, standing in front of Poyan Interchange
for o in (torso, *legs):
    o.hide_render = False
    o.location.x += 70
    o.location.y -= 50
legs[0].rotation_euler.x, legs[1].rotation_euler.x = 0.3, -0.3
cam.location, cam.rotation_euler = (71.6, -47.7, 1.3), (math.radians(90), 0, math.radians(144))
scene.render.resolution_x, scene.render.resolution_y = 800, 600
scene.render.filepath = "//preview_soldier.png"
bpy.ops.render.render(write_still=True)
print("ASSETS OK")
