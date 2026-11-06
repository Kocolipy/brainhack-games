"""Render the TRON-style sprites for Breach Run: black bodies with glowing neon edges.

Run headless from the game folder:
  blender.exe -b --python tools/make_sprites.py -- assets
Writes assets/virus.png, firewall.png, fwcap.png, honeypot.png, antivirus.png (256x256) and server.png (256x512),
transparent background, plus sprites.blend.
"""
import math
import os
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, emit=0.0, rough=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


BLACK = mat("black", (0.006, 0.008, 0.012))


def put(obj, m, coll):
    obj.data.materials.clear()
    obj.data.materials.append(m)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def neon(obj, m, coll, thick=0.06):
    """TRON look: obj turns black and gets a glowing copy of its edges"""
    put(obj, BLACK, coll)
    e = obj.copy()
    e.data = obj.data.copy()
    put(e, m, coll)
    w = e.modifiers.new("edges", "WIREFRAME")
    w.thickness = thick
    w.use_even_offset = True
    return obj


def group(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def cube(loc, scale):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)  # so the wireframe stays even on stretched boxes
    return o


GREEN, ORANGE, AMBER, BLUE, CYAN = (0.05, 1, 0.3), (1, 0.12, 0.01), (1, 0.5, 0.02), (0.05, 0.35, 1), (0.05, 0.85, 1)

# virus (the player): black geodesic core with green edges and neon spikes
virus = group("virus")
g = mat("green", GREEN, emit=1.2)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.8)
core = neon(bpy.context.object, g, virus, 0.07)
for v in core.data.vertices:
    n = v.normal
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.05, depth=0.55, location=n * 1.05)
    s = bpy.context.object
    s.rotation_mode = "QUATERNION"
    s.rotation_quaternion = n.to_track_quat("Z", "Y")
    put(s, g, virus)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.12, location=n * 1.36)
    put(bpy.context.object, g, virus)

# firewall: black panel with orange neon rails and vent lines, tiled along each wall in game
fw = group("firewall")
o = mat("orange", ORANGE, emit=1.2)
put(cube((0, 0.1, 0), (2.9, 0.4, 3.2)), BLACK, fw)
for x in (-1.5, 1.5):
    put(cube((x, -0.15, 0), (0.16, 0.2, 3.2)), o, fw)
for z in (-1.2, -0.4, 0.4, 1.2):  # 0.8 apart and 0.4 from each edge, so tiles stack seamlessly
    put(cube((0, -0.15, z), (2.0, 0.1, 0.07)), o, fw)

# firewall cap: the emitter on the open end of each wall
fl = group("fwcap")
neon(cube((0, 0, -0.95), (3.2, 0.8, 1.1)), o, fl, 0.1)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.6, location=(0, 0, -0.15))
neon(bpy.context.object, o, fl, 0.07)
bpy.ops.mesh.primitive_torus_add(major_radius=0.85, minor_radius=0.05, location=(0, -0.2, -0.15), rotation=(math.radians(90), 0, 0))
put(bpy.context.object, o, fl)

# honeypot: black pot with amber edges, a dripping neon rim and a cyan data chip as bait
hp = group("honeypot")
a = mat("amber", AMBER, emit=1.2)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=7, radius=1.1, location=(0, 0, -0.3))
pot = bpy.context.object
pot.scale = (1, 1, 0.85)
bpy.ops.object.transform_apply(scale=True)
neon(pot, a, hp, 0.06)
bpy.ops.mesh.primitive_torus_add(major_radius=0.75, minor_radius=0.08, location=(0, 0, 0.55))
put(bpy.context.object, a, hp)
for x, l in ((-0.5, 0.6), (0.15, 0.9), (0.6, 0.45)):  # drips down the front
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.06, depth=l, location=(x, -0.8, 0.5 - l / 2))
    put(bpy.context.object, a, hp)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.1, location=(x, -0.8, 0.5 - l))
    put(bpy.context.object, a, hp)
chip = neon(cube((0, 0, 1.0), (0.55, 0.55, 0.12)), mat("cyan", CYAN, emit=1.5), hp, 0.06)
chip.rotation_euler = (math.radians(20), 0, math.radians(45))
hp.objects[-1].rotation_euler = chip.rotation_euler  # the chip's glowing edges turn with it

# antivirus: black shield outlined in blue with a neon padlock
av = group("antivirus")
b = mat("blue", BLUE, emit=1.5)
pts = [(0, 1.2), (0.95, 0.85), (0.9, -0.1), (0.5, -0.85), (0, -1.25), (-0.5, -0.85), (-0.9, -0.1), (-0.95, 0.85)]
me = bpy.data.meshes.new("shield")
me.from_pydata([(x, 0, z) for x, z in pts], [], [list(range(len(pts)))])
sh = bpy.data.objects.new("shield", me)
scene.collection.objects.link(sh)
sh.modifiers.new("solid", "SOLIDIFY").thickness = 0.3
neon(sh, b, av, 0.08)
# blue padlock centred on the shield (the shield is widest at the top, so its middle sits a little above 0): body in front, its shackle behind so the body hides the lower half of the ring
neon(cube((0, -0.55, -0.07), (0.8, 0.2, 0.6)), b, av, 0.07)
bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.07, location=(0, -0.45, 0.23), rotation=(math.radians(90), 0, 0))
put(bpy.context.object, b, av)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.08, depth=0.05, location=(0, -0.67, -0.02), rotation=(math.radians(90), 0, 0))
put(bpy.context.object, b, av)

# server: the protected target, a black rack outlined in cyan with a gold padlock
srv = group("server")
c = mat("cyanedge", CYAN, emit=1.2)
neon(cube((0, 0, 0), (1.6, 1.1, 3.6)), c, srv, 0.06)
for i in range(6):
    z = -1.45 + i * 0.58
    neon(cube((0, -0.58, z), (1.3, 0.04, 0.42)), c, srv, 0.035)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0.45, -0.62, z))
    put(bpy.context.object, mat(f"led{i}", (1, 0.1, 0.1) if i % 2 else GREEN, emit=2), srv)
gold = mat("gold", (1, 0.7, 0.05), emit=1.2)
neon(cube((0, -0.75, 2.15), (0.7, 0.2, 0.55)), gold, srv, 0.05)
bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.05, location=(0, -0.75, 2.45), rotation=(math.radians(90), 0, 0))
put(bpy.context.object, gold, srv)

# camera, lights, render settings: straight-on side view to match the side-scrolling game
bpy.ops.object.camera_add(location=(0, -10, 0), rotation=(math.radians(90), 0, 0))
cam = bpy.context.object
cam.data.type = "ORTHO"
scene.camera = cam
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0, 0, 0)  # no lights either: black bodies, only the neon shows
scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"  # keep the game's colours

# render relative to the saved .blend: Blender mangles \\wsl UNC paths in render output
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "sprites.blend"))
colls = [virus, fw, fl, hp, av, srv]


def render(show, scale, w=256, h=256):
    for coll in colls:
        coll.hide_render = coll is not show
    cam.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.filepath = "//" + show.name + ".png"
    bpy.ops.render.render(write_still=True)


render(virus, 3.0)
render(fw, 3.2)  # panel fills the frame top to bottom so it tiles
render(fl, 3.4)  # cap sits in the bottom half: its base is the wall end
render(hp, 3.0)
render(av, 2.7)  # the shield fills the frame
render(srv, 5.8, 256, 512)
