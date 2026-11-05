"""Render the block and zero-day icons for Defend Zero Days.

Run headless from the game folder:
  blender.exe -b --python tools/make_icons.py -- assets
Writes assets/network.png, compute.png, database.png, code.png, and 0day_low/high/critical.png
(256x256, transparent background), plus icons.blend.
"""
import math
import os
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, emit=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def put(obj, m, coll):
    obj.data.materials.append(m)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def group(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def shade_smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


CYAN, GREEN, BLUE = (0.1, 0.85, 1.0), (0.02, 0.8, 0.25), (0.25, 0.45, 1.0)
dark = mat("dark", (0.04, 0.06, 0.1), metal=0.6)

# network: wireframe globe with an orbit ring and three nodes
net = group("network")
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1)
g = put(bpy.context.object, mat("globe", CYAN, emit=0.8), net)
g.modifiers.new("wire", "WIREFRAME").thickness = 0.06
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9)
put(bpy.context.object, mat("core", (0.02, 0.12, 0.2)), net)
bpy.ops.mesh.primitive_torus_add(major_radius=1.35, minor_radius=0.04, rotation=(math.radians(70), math.radians(20), 0))
ring = put(bpy.context.object, mat("ring", CYAN, emit=1.2), net)
for a in (0.3, 2.4, 4.3):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14)
    n = put(bpy.context.object, mat("node", (1, 1, 1), emit=2), net)
    n.parent = ring
    n.location = (1.35 * math.cos(a), 1.35 * math.sin(a), 0)

# compute: server rack, three units with LED strips
comp = group("compute")
bpy.ops.mesh.primitive_cube_add(size=1)
rack = put(bpy.context.object, dark, comp)
rack.scale = (1.5, 1.1, 2.1)
led, led2 = mat("led", GREEN, emit=1.2), mat("led2", (1, 0.75, 0.2), emit=1.2)
for i, z in enumerate((-0.65, 0, 0.65)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.56, z))
    unit = put(bpy.context.object, mat(f"unit{i}", (0.15, 0.2, 0.28), metal=0.4), comp)
    unit.scale = (1.35, 0.04, 0.5)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.25, -0.59, z))
    put(bpy.context.object, led, comp).scale = (0.65, 0.03, 0.08)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0.5, -0.59, z))
    put(bpy.context.object, led2 if i == 1 else led, comp)

# database: three stacked discs with glowing seams
db = group("database")
body = mat("disc", BLUE, metal=0.3)
for z in (-0.75, 0, 0.75):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1.1, depth=0.6, location=(0, 0, z))
    shade_smooth(put(bpy.context.object, body, db))
seam = mat("seam", CYAN, emit=1)
for z in (-0.375, 0.375, 1.06):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.1 if z < 1 else 0.7, minor_radius=0.05, location=(0, 0, z))
    put(bpy.context.object, seam, db)

# code: extruded </> glyph
code = group("code")
bpy.ops.object.text_add(rotation=(math.radians(90), 0, 0))
t = bpy.context.object
t.data.body = "</>"
t.data.extrude = 0.12
t.data.align_x, t.data.align_y = "CENTER", "CENTER"
t.data.size = 1.6
put(t, mat("glyph", GREEN, emit=0.6), code)

# zero-day: spiky virus, one material per severity
zd = group("0day")
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.85)
core = bpy.context.object
shade_smooth(core)
virus = mat("virus", (1, 1, 1), emit=0.35)
put(core, virus, zd)
for v in list(core.data.vertices)[::2]:  # spikes along every other vertex normal, capped with a knob
    n = v.normal
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.06, depth=0.5, location=n * 1.05)
    s = bpy.context.object
    s.rotation_mode = "QUATERNION"
    s.rotation_quaternion = n.to_track_quat("Z", "Y")
    put(s, virus, zd)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=n * 1.33)
    put(bpy.context.object, virus, zd)

# camera, lights, render settings
bpy.ops.object.camera_add(location=(0, -8, 4))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 3.4
cam.rotation_euler = (math.radians(63.4), 0, 0)  # looks at the origin from 8 m out and 4 m up
scene.camera = cam
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(-20), math.radians(-30)))
bpy.context.object.data.energy = 4
bpy.ops.object.light_add(type="AREA", location=(3, -3, 2))
bpy.context.object.data.energy = 300
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.02, 0.03, 0.05)
scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 256
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"  # keep the game's colours (Filmic/AgX would wash them out)

# render relative to the saved .blend: Blender mangles \\wsl UNC paths in render output
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "icons.blend"))
colls = [net, comp, db, code, zd]


def render(show, name):
    for c in colls:
        c.hide_render = c is not show
    scene.render.filepath = "//" + name + ".png"
    bpy.ops.render.render(write_still=True)


for c in (net, comp, db, code):
    render(c, c.name)
bsdf = virus.node_tree.nodes["Principled BSDF"]
# linear colours: sRGB output brightens them
for name, rgb in (("low", (1, 0.62, 0.0)), ("high", (1, 0.18, 0.0)), ("critical", (0.85, 0.0, 0.03))):
    bsdf.inputs["Base Color"].default_value = bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
    render(zd, "0day_" + name)
