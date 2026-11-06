"""Build low-poly assets for Artillery Defence.

Run headless:  blender.exe -b --python make_assets.py -- <assets_dir>
Writes player.glb (objects "Hull" + "Turret", with child "Barrel"), enemy_small/medium/large.glb, shell.glb,
explosion.glb (objects "Fireball" + "Smoke"), ships.blend, preview.png, preview_player.png.

Conventions: 1 unit ~ 8 m (lengths exaggerated for readability), origin at waterline centre.
Built bow +Y; the glTF exporter maps Blender +Y -> three.js -Z (up-screen), -Y -> +Z (down-screen).
Player faces +Y; enemies and the shell are turned to face -Y.

References (silhouettes only, no national markings on enemies):
  player  - RSN Formidable-class frigate: stealth hull, 76mm Super Rapid cupola forward, pyramid mast, helideck
  small   - KCR-60M fast missile craft: low slim hull, small gun, missile canisters
  medium  - SIGMA 10514 frigate: stepped superstructure, mast, hangar + helideck
  large   - Gowind-based LCS: tall integrated mast tower, 57mm stealth cupola
"""
import math
import os
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ---------- materials ----------
def mat(name, rgb, emit=0.0, image=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)  # preview (workbench)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)  # exported to glTF
    bsdf.inputs["Roughness"].default_value = 0.8
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    if image:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        m.use_backface_culling = False  # flag readable from both sides (glTF doubleSided)
    return m


def singapore_flag(w=150, h=100):
    """2:3 flag: red over white, white crescent and five stars in the upper hoist."""
    red, white = (0.93, 0.16, 0.22, 1), (1, 1, 1, 1)
    cx, cy = 0.25 * w, 0.25 * h                        # crescent centre (upper hoist quarter)
    ro, ri, off = 0.15 * h, 0.13 * h, 0.055 * h        # outer/inner circle radii, inner offset to fly side
    sx, sy, sr, star_r = cx + 0.1 * h, cy, 0.075 * h, 0.032 * h

    def star(px, py, x0, y0):  # point in 5-point star (10-vertex polygon, tip up), even-odd ray cast
        pts = [(x0 + (star_r if k % 2 == 0 else star_r * 0.4) * math.sin(k * math.pi / 5),
                y0 - (star_r if k % 2 == 0 else star_r * 0.4) * math.cos(k * math.pi / 5)) for k in range(10)]
        inside = False
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            if (ay > py) != (by > py) and px < ax + (py - ay) * (bx - ax) / (by - ay):
                inside = not inside
        return inside

    stars = [(sx + sr * math.sin(k * 2 * math.pi / 5), sy - sr * math.cos(k * 2 * math.pi / 5)) for k in range(5)]
    px = []
    for row in range(h):          # Blender images start at the bottom row
        y = h - 1 - row + 0.5     # y measured from the top
        for col in range(w):
            x = col + 0.5
            c = white
            if y < h / 2:
                c = red
                crescent = math.hypot(x - cx, y - cy) < ro and math.hypot(x - cx - off, y - cy) >= ri
                if crescent or any(star(x, y, a, b) for a, b in stars):
                    c = white
            px.extend(c)
    img = bpy.data.images.new("SingaporeFlag", w, h)
    img.pixels = px
    img.pack()
    return img


# ---------- geometry helpers ----------
def mesh_obj(name, verts, faces, mats, face_mats=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for m in mats:
        mesh.materials.append(m)
    for i, mi in (face_mats or {}).items():
        mesh.polygons[i].material_index = mi
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def loft(name, bottom, z0, top, z1, side, cap=None):
    """Join two counter-clockwise outlines (same point count); cap material goes on the top face."""
    n = len(bottom)
    verts = [(x, y, z0) for x, y in bottom] + [(x, y, z1) for x, y in top]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_obj(name, verts, faces, [side] + ([cap] if cap else []), {1: 1} if cap else None)


def hull(name, L, W, h, side, deck):
    """Warship hull: pointed bow at +Y, flared sides (narrower keel), transom stern."""
    w = W / 2
    deck_line = [(-w * 0.9, -L / 2), (w * 0.9, -L / 2), (w, -L * 0.1), (w * 0.8, L * 0.25),
                 (w * 0.4, L * 0.42), (0, L / 2), (-w * 0.4, L * 0.42), (-w * 0.8, L * 0.25), (-w, -L * 0.1)]
    keel_line = [(x * 0.7, y * 0.96) for x, y in deck_line]
    return loft(name, keel_line, 0, deck_line, h, side, deck)


def block(name, w, d, z0, z1, y, mat_, taper=0.8, x=0):
    """Stealth-style frustum: sloped sides, top shrunk by `taper`."""
    rect = lambda a, b: [(x - a, y - b), (x + a, y - b), (x + a, y + b), (x - a, y + b)]
    return loft(name, rect(w / 2, d / 2), z0, rect(w / 2 * taper, d / 2 * taper), z1, mat_)


def cyl(name, r, depth, loc, mat_, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat_)
    return obj


def cone(name, r, depth, loc, mat_, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=r, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat_)
    return obj


def quad(name, corners, mat_):
    """Flat textured quad; corners are bottom-left, bottom-right, top-right, top-left of the image."""
    obj = mesh_obj(name, corners, [[0, 1, 2, 3]], [mat_])
    uv = obj.data.uv_layers.new()
    for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    return obj


def gun(prefix, y, z, s, body, barrel, x=0):
    """Stealth cupola gun at deck height z, barrel pointing +Y."""
    return [block(prefix + "Cupola", 0.9 * s, 1.1 * s, z, z + 0.5 * s, y, body, taper=0.6, x=x),
            cyl(prefix + "Barrel", 0.07 * s, 1.6 * s, (x, y + 1.1 * s, z + 0.28 * s), barrel, rot=(math.pi / 2, 0, 0), verts=8)]


def join(name, parts):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = obj.data.name = name
    return obj


def face_aft(obj):
    """Turn a +Y-facing object to face -Y (down-screen in the game)."""
    obj.rotation_euler.z = math.pi
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(rotation=True)


def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True)


# ---------- palette ----------
rsn_hull, rsn_deck, rsn_light = mat("RSNHull", (0.42, 0.45, 0.48)), mat("RSNDeck", (0.28, 0.3, 0.32)), mat("RSNLight", (0.62, 0.64, 0.66))
foe_hull, foe_deck, foe_light = mat("FoeHull", (0.2, 0.21, 0.23)), mat("FoeDeck", (0.42, 0.1, 0.08)), mat("FoeLight", (0.32, 0.33, 0.35))
black = mat("Gun", (0.05, 0.05, 0.06))
flag = mat("Flag", (1, 1, 1), image=singapore_flag())

# ---------- player: Formidable-class style frigate, 14 x 2.6 ----------
D = 1.0  # deck height
hull_obj = join("Hull", [
    hull("Hull", 14, 2.6, D, rsn_hull, rsn_deck),
    block("VLS", 1.4, 1.2, D, D + 0.15, 2.4, black, taper=0.95),
    block("Bridge", 2.2, 2.4, D, D + 1.2, 0.9, rsn_light),
    block("Mast", 1.2, 1.2, D + 1.2, D + 3.2, 0.5, rsn_light, taper=0.35),
    block("Radar", 0.6, 0.6, D + 3.2, D + 3.6, 0.5, black, taper=0.9),
    block("Hangar", 2.3, 2.8, D, D + 1.0, -2.2, rsn_light, taper=0.9),
    block("Funnel", 0.9, 0.9, D + 1.0, D + 1.6, -1.6, rsn_hull, taper=0.7),
    cyl("Flagstaff", 0.03, 1.4, (0, -6.2, D + 0.7), black, verts=6),
    # deck flag on the helideck. The game lays the ship sideways (bow to screen-right, starboard
    # toward the camera), so the flag's top edge faces port (-X) and its hoist faces aft (-Y).
    quad("DeckFlag", [(0.6, -5.9, D + 0.01), (0.6, -4.1, D + 0.01), (-0.6, -4.1, D + 0.01), (-0.6, -5.9, D + 0.01)], flag),
    # stern ensign streaming straight aft, broadside to the camera
    quad("Ensign", [(0, -6.2, D + 0.85), (0, -6.95, D + 0.85), (0, -6.95, D + 1.35), (0, -6.2, D + 1.35)], flag),
    # flag painted on the bridge's starboard face (the side the 3D game's camera sees), just proud of the sloped wall:
    # the wall leans in from x = 1.1 at the deck to 0.88 at the roof (Bridge block above)
    quad("BridgeFlag", [(1.074, 0.375, D + 0.25), (1.074, 1.425, D + 0.25), (0.946, 1.425, D + 0.95), (0.946, 0.375, D + 0.95)], flag),
])
cupola, barrel = gun("Turret", 0, 0, 1.3, rsn_light, black)
turret = join("Turret", [cupola])
# barrel hangs off an empty "Barrel" at its breech, so the 3D game can elevate it (rotate Barrel about x)
bpy.ops.object.empty_add(location=(0, 0.39, 0.364))  # breech: barrel centre y 1.43 minus half its 2.08 length
pivot = bpy.context.object
pivot.name = "Barrel"
barrel.parent, barrel.location = pivot, (0, 1.04, 0)  # Python parenting keeps location relative to the parent
pivot.parent = turret
turret.location = (0, 4.2, D)  # pivot on the foredeck; the game rotates this object

# ---------- enemies (bow built +Y, then turned to face -Y) ----------
small = join("EnemySmall", [
    hull("EnemySmall", 5, 1.1, 0.45, foe_hull, foe_deck),
    *gun("S", 1.3, 0.45, 0.6, foe_light, black),
    block("SBridge", 0.9, 1.3, 0.45, 1.0, 0.1, foe_light),
    block("SMast", 0.4, 0.4, 1.0, 1.6, 0.0, foe_light, taper=0.4),
    block("SCanL", 0.25, 1.0, 0.45, 0.7, -1.3, black, taper=1, x=-0.25),
    block("SCanR", 0.25, 1.0, 0.45, 0.7, -1.3, black, taper=1, x=0.25),
])
medium = join("EnemyMedium", [
    hull("EnemyMedium", 8, 1.6, 0.6, foe_hull, foe_deck),
    *gun("M", 2.3, 0.6, 0.85, foe_light, black),
    block("MSuper", 1.4, 2.0, 0.6, 1.5, 0.8, foe_light),
    block("MMast", 0.7, 0.7, 1.5, 2.6, 0.6, foe_light, taper=0.4),
    block("MHangar", 1.4, 1.8, 0.6, 1.3, -1.2, foe_light, taper=0.9),
    block("MFunnel", 0.6, 0.6, 1.3, 1.7, -0.6, foe_hull, taper=0.7),
])
large = join("EnemyLarge", [
    hull("EnemyLarge", 10.5, 2.0, 0.7, foe_hull, foe_deck),
    *gun("L", 3.3, 0.7, 1.0, foe_light, black),
    block("LSuper", 1.8, 3.0, 0.7, 1.8, 0.8, foe_light),
    block("LTower", 1.2, 1.4, 1.8, 3.6, 0.8, foe_light, taper=0.5),  # Gowind-style integrated mast
    block("LHangar", 1.7, 2.4, 0.7, 1.6, -2.0, foe_light, taper=0.9),
    cyl("LGunL", 0.12, 0.3, (-0.75, -0.6, 1.0), black),
    cyl("LGunR", 0.12, 0.3, (0.75, -0.6, 1.0), black),
])
for e in (small, medium, large):
    face_aft(e)

# ---------- boss: original sea kaiju "Leviathan", ~10 wide x 18 long (game rescales it) ----------
# Low-slung armoured swimmer seen from above: wedge head, swept horns, clawed fore-flippers, segmented tail, glowing vents.
armour, plate = mat("KaijuArmour", (0.08, 0.2, 0.17)), mat("KaijuPlate", (0.16, 0.32, 0.26))
glow, horn = mat("KaijuGlow", (1.0, 0.45, 0.08), emit=4.0), mat("KaijuHorn", (0.75, 0.7, 0.6))
Z0 = -0.3  # sits slightly submerged
kaiju_parts = [loft("KHead", [(-1.4, 3.8), (1.4, 3.8), (1.0, 6.0), (0, 6.6), (-1.0, 6.0)], Z0,
                    [(-1.1, 4.0), (1.1, 4.0), (0.7, 5.8), (0, 6.2), (-0.7, 5.8)], 1.6, armour, plate)]
for i, (w, d, top, y) in enumerate([(4.6, 3.0, 2.2, 2.2), (4.2, 3.0, 2.0, -0.8), (3.2, 2.8, 1.6, -3.6),
                                     (2.2, 2.2, 1.1, -6.0), (1.5, 2.2, 0.8, -8.0), (0.9, 2.0, 0.5, -9.8)]):
    kaiju_parts.append(block(f"KSeg{i}", w, d, Z0, top, y, armour, taper=0.75))
    if i < 3:  # armour plate with a pair of glowing vents on the big segments
        kaiju_parts.append(block(f"KPlate{i}", w * 0.5, d * 0.6, top, top + 0.3, y, plate, taper=0.7))
        kaiju_parts += [block(f"KVent{i}{s}", 0.3, 0.9, top + 0.3, top + 0.45, y, glow, taper=1, x=s * 0.45) for s in (-1, 1)]
kaiju_parts.append(block("KTailTip", 0.6, 1.4, Z0, 0.3, -11.5, armour, taper=0.3))
for s in (-1, 1):  # s = side; mirrored outlines are reversed to stay counter-clockwise
    arm = [(s * 2.0, 1.2), (s * 4.6, 1.8), (s * 5.0, 3.0), (s * 2.0, 3.2)]
    arm = arm if s > 0 else arm[::-1]
    kaiju_parts.append(loft(f"KArm{s}", arm, Z0, arm, 0.6, armour, plate))
    kaiju_parts += [cone(f"KClaw{s}{k}", 0.22, 0.9, (s * cx, 3.55, 0.2), horn, rot=(-math.pi / 2, 0, 0))
                    for k, cx in enumerate((3.0, 3.9, 4.7))]
    kaiju_parts.append(block(f"KEye{s}", 0.4, 0.3, 1.55, 1.8, 5.2, glow, taper=1, x=s * 0.5))
    kaiju_parts.append(cone(f"KHorn{s}", 0.25, 1.8, (s * 1.0, 3.7, 1.9), horn, rot=(math.radians(60), 0, -s * 0.3)))
kaiju = join("Kaiju", kaiju_parts)
face_aft(kaiju)

# ---------- shell: 76mm-style round, nose turned to -Y (three.js +Z, so lookAt() aims it) ----------
steel, copper = mat("ShellSteel", (0.35, 0.33, 0.28)), mat("ShellBand", (0.72, 0.4, 0.2))
shell = join("Shell", [
    cyl("Body", 0.13, 0.7, (0, 0, 0), steel, rot=(math.pi / 2, 0, 0), verts=10),
    cone("Nose", 0.13, 0.45, (0, 0.575, 0), steel, rot=(-math.pi / 2, 0, 0)),
    cyl("Band", 0.145, 0.08, (0, -0.25, 0), copper, rot=(math.pi / 2, 0, 0), verts=10),
])
face_aft(shell)

# ---------- explosion: fireball + smoke, unit radius; the game animates scale/opacity ----------
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
fireball = bpy.context.object
fireball.name = "Fireball"
fireball.data.materials.append(mat("Fire", (1.0, 0.45, 0.08), emit=3.0))
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
smoke = bpy.context.object
smoke.name = "Smoke"
smoke.data.materials.append(mat("Smoke", (0.18, 0.17, 0.16)))

# self-checks: sizes match what the game expects, and things face the right way
for obj, (w, l) in [(hull_obj, (2.6, 14)), (small, (1.1, 5)), (medium, (1.6, 8)), (large, (2.0, 10.5))]:
    assert abs(obj.dimensions.x - w) < 0.05 and abs(obj.dimensions.y - l) < 0.05, (obj.name, tuple(obj.dimensions))
for e in (small, medium, large):
    tip = min(e.data.vertices, key=lambda v: v.co.y)
    assert abs(tip.co.x) < 0.01, f"{e.name}: pointed bow should be at -Y"
assert min(v.co.y for v in shell.data.vertices) < -0.75, "shell nose should be at -Y"
tip = min(kaiju.data.vertices, key=lambda v: v.co.y)
assert abs(tip.co.x) < 0.01 and tip.co.y < -6, "kaiju snout should be at -Y"
assert 9.5 < kaiju.dimensions.x < 11, ("kaiju width", tuple(kaiju.dimensions))

os.makedirs(out, exist_ok=True)
p = lambda f: os.path.join(out, f)
export(p("player.glb"), [hull_obj, turret, pivot, barrel])
export(p("enemy_small.glb"), [small])
export(p("enemy_medium.glb"), [medium])
export(p("enemy_large.glb"), [large])
export(p("shell.glb"), [shell])
export(p("explosion.glb"), [fireball, smoke])
export(p("kaiju.glb"), [kaiju])

# ---------- preview renders (workbench) ----------
for obj, x in [(large, -10), (medium, -7), (small, -4.5), (shell, 3.5), (fireball, 6), (smoke, 6)]:
    obj.location.x = x
smoke.location.y, shell.location.z = -2.5, 0.5
kaiju.location.y = 30  # own preview, away from the ships
target = bpy.data.objects.new("Target", None)
scene.collection.objects.link(target)
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(cam)
cam.constraints.new("TRACK_TO").target = target
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.color_type = "TEXTURE"
scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1200, 600
# save first: Blender mangles \\wsl UNC paths in render output, so render relative to the .blend
bpy.ops.wm.save_as_mainfile(filepath=p("ships.blend"))
for name, cam_at, look_at in [("preview", (-2, -20, 16), (-2, 0, 0)), ("preview_player", (3, -12, 7), (0, -3, 1)),
                                ("preview_kaiju", (8, 12, 16), (0, 29, 0))]:
    cam.location, target.location = cam_at, look_at
    scene.render.filepath = "//" + name + ".png"
    bpy.ops.render.render(write_still=True)
print("ASSETS OK")
