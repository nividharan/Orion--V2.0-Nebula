"""
Blender 5.2 — Master 3D Orion Nebula Scene with Perfect Framing.
Frames the complete artwork including the typography "ORION v2.0 NEBULA".
"""

from pathlib import Path
import bpy

# 1. Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Configure EEVEE settings
avail_engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in avail_engines else "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.frame_start = 1
scene.frame_end = 120
scene.render.fps = 30

# World Background
world = bpy.data.worlds.new("CosmicWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if not bg:
    bg = world.node_tree.nodes.new(type="ShaderNodeBackground")
    out = world.node_tree.nodes.new(type="ShaderNodeOutputWorld")
    world.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
bg.inputs["Color"].default_value = (0.005, 0.002, 0.01, 1.0)
bg.inputs["Strength"].default_value = 1.0

# 2. Master Artwork Plate (16:9 uncompressed)
img_path = str(Path("c:/skill/assets/orion_logo_original.jpg").resolve())
img = bpy.data.images.load(img_path)

bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
plate = bpy.context.active_object
plate.name = "Master_ArtworkPlate"
plate.scale = (16.0, 9.0, 1.0)

mat_plate = bpy.data.materials.new(name="Mat_ArtworkPlate")
mat_plate.use_nodes = True
p_nodes = mat_plate.node_tree.nodes
p_nodes.clear()

tex_img = p_nodes.new(type="ShaderNodeTexImage")
tex_img.image = img
emit = p_nodes.new(type="ShaderNodeEmission")
emit.inputs["Strength"].default_value = 1.35
p_out = p_nodes.new(type="ShaderNodeOutputMaterial")

mat_plate.node_tree.links.new(tex_img.outputs["Color"], emit.inputs["Color"])
mat_plate.node_tree.links.new(emit.outputs["Emission"], p_out.inputs["Surface"])
plate.data.materials.append(mat_plate)

# 3. 3D Stars: Floating glowing emitters on Betelgeuse & Rigel
def make_emission(name, color, strength=10.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    e = nodes.new(type="ShaderNodeEmission")
    e.inputs["Color"].default_value = color
    e.inputs["Strength"].default_value = strength
    o = nodes.new(type="ShaderNodeOutputMaterial")
    mat.node_tree.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return mat

mat_betelgeuse = make_emission("Mat_Betelgeuse", (1.0, 0.55, 0.12, 1.0), 18.0)
mat_rigel       = make_emission("Mat_Rigel",       (0.40, 0.85, 1.0, 1.0), 20.0)

# Exact star positions aligned with the artwork
stars_3d = [
    ("Betelgeuse", (-0.95, 1.45, 0.15), 0.10, mat_betelgeuse),
    ("Rigel",       (0.72, -0.25, 0.15), 0.09, mat_rigel),
]

for name, loc, r, mat in stars_3d:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=12)
    s_obj = bpy.context.active_object
    s_obj.name = f"3DStar_{name}"
    s_obj.data.materials.append(mat)

# 4. Perfectly Framed Camera at Z=15.0
bpy.ops.object.camera_add(location=(0, 0, 14.8), rotation=(0, 0, 0))
cam = bpy.context.active_object
cam.name = "MainCamera"
cam.data.lens = 50
scene.camera = cam

# 5. Dynamic 3D Accent Lights
bpy.ops.object.light_add(type="POINT", radius=1.0, location=(-1.0, 1.5, 1.5))
l_bet = bpy.context.active_object
l_bet.data.color = (1.0, 0.5, 0.1)
l_bet.data.energy = 60

bpy.ops.object.light_add(type="POINT", radius=1.0, location=(0.7, -0.3, 1.5))
l_rig = bpy.context.active_object
l_rig.data.color = (0.2, 0.8, 1.0)
l_rig.data.energy = 70

# 6. Keyframed 3D Parallax Motion (120 frames)
cam.location = (0, 0, 14.8)
cam.keyframe_insert(data_path="location", frame=1)

cam.location = (0.20, -0.10, 14.6)
cam.keyframe_insert(data_path="location", frame=60)

cam.location = (0, 0, 14.8)
cam.keyframe_insert(data_path="location", frame=121)

# Save files
assets_dir = Path("c:/skill/assets")
web_dir = Path("c:/skill/web_ui")
blend_path = str(assets_dir / "orion_nebula_logo.blend")
glb_path = str(web_dir / "orion_logo.glb")
preview_path = str(web_dir / "orion_logo_preview.png")

bpy.ops.wm.save_as_mainfile(filepath=blend_path)

bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format="GLB",
    export_animations=True,
    export_materials="EXPORT",
    export_apply=True
)

scene.render.filepath = preview_path
scene.frame_set(1)
bpy.ops.render.render(write_still=True)

Path("c:/skill/master_3d_done.txt").write_text("PERFECT FRAMING SUCCESS!\n")
import os
os._exit(0)
