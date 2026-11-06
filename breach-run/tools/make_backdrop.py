"""Render the cyberspace backdrop for Breach Run: a sea of black wireframe blocks under a dark sky,
with a glowing data highway winding to the horizon.

Run headless from the game folder:
  blender.exe -b --python tools/make_backdrop.py -- assets
Writes assets/backdrop.jpg (3000x1000; the game pans across it), plus backdrop.blend.
"""
import math
import os
import random
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
random.seed(7)


def node_mat(name, build):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    nt.links.new(build(nt), nt.nodes["Material Output"].inputs["Surface"])
    return m


def emission(rgb, strength):
    def build(nt):
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*rgb, 1)
        e.inputs["Strength"].default_value = strength
        return e.outputs[0]
    return build


def depth_emission(near, far, strength, depth=70):
    """emission blending from the near colour to the far colour with distance from the camera (world y)"""
    def build(nt):
        tc, sep, mr = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeMapRange")
        mix, e = nt.nodes.new("ShaderNodeMix"), nt.nodes.new("ShaderNodeEmission")
        mix.data_type = "RGBA"
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        nt.links.new(sep.outputs["Y"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0, depth
        sock = lambda socks, ident: next(s for s in socks if s.identifier == ident)
        nt.links.new(mr.outputs["Result"], sock(mix.inputs, "Factor_Float"))
        sock(mix.inputs, "A_Color").default_value = (*near, 1)
        sock(mix.inputs, "B_Color").default_value = (*far, 1)
        nt.links.new(sock(mix.outputs, "Result_Color"), e.inputs["Color"])
        e.inputs["Strength"].default_value = strength
        return e.outputs[0]
    return build


def boxes(name, cells, m, wire=None, thick=0.03):
    """one mesh of boxes (x, y, w, h); with wire, the boxes are black and a glowing copy of their edges is added"""
    verts, faces = [], []
    for x, y, w, h in cells:
        i = len(verts)
        verts += [(x + dx * w, y + dy * w, z) for z in (0, h) for dx, dy in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))]
        faces += [(i, i + 1, i + 2, i + 3), (i + 4, i + 5, i + 6, i + 7)] + [(i + k, i + (k + 1) % 4, i + 4 + (k + 1) % 4, i + 4 + k) for k in range(4)]
    for mm, mod in ((m, False), (wire, True)):
        if mm is None:
            continue
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.materials.append(mm)
        o = bpy.data.objects.new(name, me)
        scene.collection.objects.link(o)
        if mod:
            wm = o.modifiers.new("edges", "WIREFRAME")
            wm.thickness = thick
            wm.use_even_offset = True


black = node_mat("black", emission((0.004, 0.008, 0.02), 1))
road_x = lambda y: 5 * math.sin(y / 14) + 2 * math.sin(y / 5.3)  # the data highway winding into the distance
city, road, lit = [], [], []
for j in range(8, 130):
    for i in range(-80, 81):
        x, y = float(i), float(j)
        if abs(x) > 0.85 * (y + 4) + 2 or y > 0 and 6 / (y + 4) > 0.4:  # outside the view, or below its bottom edge  # outside the camera's view
            continue
        if abs(x - road_x(y)) < 1.6:
            road.append((x, y, 0.92, 0.06))
            continue
        h = 0.1 + random.random() ** 3 * (0.4 + y / 30)
        (lit if random.random() < 0.035 else city).append((x, y, 0.88, h))

boxes("city", city, black, node_mat("wire", depth_emission((0.02, 0.1, 0.5), (0, 0.45, 0.45), 0.6, 110)))
boxes("road", road, node_mat("roadfill", emission((0, 0.1, 0.12), 1)), node_mat("roadwire", emission((0.1, 0.8, 0.75), 0.6)), 0.05)
# lit blocks in dim cyan: green is the player's colour
boxes("lit", lit, node_mat("litfill", depth_emission((0.02, 0.15, 0.3), (0.02, 0.3, 0.35), 0.6, 110)))

# sky: navy overhead with a teal haze on the horizon
w = scene.world = bpy.data.worlds.new("sky")
w.use_nodes = True
nt = w.node_tree
tc, sep, ramp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeValToRGB")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.0, 0.16, 0.19, 1)
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.2, (0.003, 0.006, 0.025, 1)
mid = ramp.color_ramp.elements.new(0.04)
mid.color = (0.01, 0.05, 0.1, 1)
nt.links.new(ramp.outputs["Color"], nt.nodes["Background"].inputs["Color"])

bpy.ops.object.camera_add(location=(0, -4, 6), rotation=(math.radians(84), 0, 0))
scene.camera = bpy.context.object
scene.camera.data.lens = 22
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 32
scene.render.resolution_x, scene.render.resolution_y = 3000, 1000
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 82
scene.view_settings.view_transform = "Standard"

# render relative to the saved .blend: Blender mangles \\wsl UNC paths in render output
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "backdrop.blend"))
scene.render.filepath = "//backdrop.jpg"
bpy.ops.render.render(write_still=True)
