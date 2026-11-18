# -*- coding: utf-8 -*-
"""
Canh 3D: hai kiem si danh nhau bang kiem (~20 giay, 480 frame @ 24 fps).

Chay:
    blender -b --python scene.py -- [thu_muc_frames]

- Khong truyen thu muc thi mac dinh la "frames" canh noi chay script.
- Bien moi truong SCENE_CHECK=1: chi dung canh + in khoang cach hai luoi
  kiem tai cac frame cham kiem (khong render) - dung de kiem tra so hoc.
- Bien moi truong SCENE_NO_RENDER=1: chi dung canh, khong render.

Canh tu chua hoan toan: chi dung bpy + mathutils + stdlib.
Nhan vat dung tu khoi nguyen thuy (box/prism), moi bo phan la 1 mesh rieng,
origin dat tai khop, parent theo tang Empty lam khop. Kiem gan cung vao
tay phai, khong roi tay trong suot video.
"""

import bpy
import os
import sys
import time
from math import sin, cos, pi, atan2, radians
from mathutils import Vector

START_TIME = time.time()
FPS = 24
FRAME_START = 1
FRAME_END = 480

# ---------------------------------------------------------------- argv / env
argv = sys.argv
OUT_DIR = "frames"
if "--" in argv:
    _rest = argv[argv.index("--") + 1:]
    if _rest:
        OUT_DIR = _rest[0]
if not os.path.isabs(OUT_DIR):
    OUT_DIR = os.path.abspath(OUT_DIR)
CHECK_MODE = os.environ.get("SCENE_CHECK") == "1"
NO_RENDER = CHECK_MODE or os.environ.get("SCENE_NO_RENDER") == "1"

# Cac frame hai luoi kiem cham nhau (de kiem tra so hoc + dat tia lua)
CLASH_FRAMES = [120, 207, 300, 417]

# Reset ve scene rong TRUOC khi tao bat ky data-block nao (material, mesh...),
# vi read_factory_settings se xoa sach data-block da tao truoc do.
bpy.ops.wm.read_factory_settings(use_empty=True)

# ------------------------------------------------------------------ vat lieu
def make_mat(name, color, metallic=0.0, rough=0.85, emission=None, e_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emission is not None:
        for sock in ("Emission Color", "Emission"):
            if sock in bsdf.inputs:
                bsdf.inputs[sock].default_value = (*emission, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = e_strength
    return m

MAT_STONE   = make_mat("Stone",   (0.32, 0.31, 0.30), rough=0.95)
MAT_STONE_D = make_mat("StoneD",  (0.20, 0.19, 0.19), rough=0.97)
MAT_GROUND  = make_mat("Ground",  (0.05, 0.055, 0.07), rough=1.0)
MAT_TRUNK   = make_mat("Trunk",   (0.16, 0.10, 0.06), rough=1.0)
MAT_LEAF    = make_mat("Leaf",    (0.06, 0.14, 0.05), rough=1.0)
MAT_BLUE    = make_mat("Blue",    (0.10, 0.25, 0.90), rough=0.7)
MAT_BLUE_D  = make_mat("BlueD",   (0.05, 0.12, 0.45), rough=0.75)
MAT_RED     = make_mat("Red",     (0.90, 0.15, 0.10), rough=0.7)
MAT_RED_D   = make_mat("RedD",    (0.45, 0.07, 0.05), rough=0.75)
MAT_BLADE   = make_mat("Blade",   (0.75, 0.78, 0.82), metallic=0.9, rough=0.35)
MAT_GRIP    = make_mat("Grip",    (0.25, 0.15, 0.08), rough=0.9)
MAT_SPARK   = make_mat("Spark",   (1.0, 0.55, 0.10), rough=0.4,
                       emission=(1.0, 0.45, 0.05), e_strength=6.0)

# ------------------------------------------------------------- mesh builders
def box_mesh(name, dims, offset=(0.0, 0.0, 0.0)):
    """Hop chu nhat: dims=(x,y,z), offset = tam hop so voi origin."""
    hx, hy, hz = dims[0] / 2.0, dims[1] / 2.0, dims[2] / 2.0
    ox, oy, oz = offset
    verts = [
        ( hx + ox,  hy + oy, -hz + oz),
        ( hx + ox, -hy + oy, -hz + oz),
        (-hx + ox, -hy + oy, -hz + oz),
        (-hx + ox,  hy + oy, -hz + oz),
        ( hx + ox,  hy + oy,  hz + oz),
        ( hx + ox, -hy + oy,  hz + oz),
        (-hx + ox, -hy + oy,  hz + oz),
        (-hx + ox,  hy + oy,  hz + oz),
    ]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me

def prism_mesh(name, r_top, r_bot, height, sides=10, offset=(0.0, 0.0, 0.0)):
    """Lang tru dung (truc Z): day duoi tai z=-h/2+oz, day tren +h/2+oz."""
    ox, oy, oz = offset
    verts = []
    for i in range(sides):
        a = 2.0 * pi * i / sides
        verts.append((r_bot * cos(a) + ox, r_bot * sin(a) + oy, -height / 2.0 + oz))
    for i in range(sides):
        a = 2.0 * pi * i / sides
        verts.append((r_top * cos(a) + ox, r_top * sin(a) + oy, height / 2.0 + oz))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    faces.append(tuple(range(sides - 1, -1, -1)))          # day duoi
    faces.append(tuple(range(sides, 2 * sides)))           # day tren
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me

def place(mesh, name, parent=None, loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), mat=None):
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    if mat is not None:
        mesh.materials.append(mat)
    if parent is not None:
        ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob

def joint(name, parent, loc):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob

# ------------------------------------------------------------------ san dau
def build_arena():
    # Nen lon toi bao quanh
    place(prism_mesh("Ground", 40, 40, 0.1, 24), "Ground", loc=(0, 0, -0.36), mat=MAT_GROUND)
    # Be da tron: viền duoi + mat tren
    place(prism_mesh("Trim", 3.45, 3.6, 0.2, 36), "Trim", loc=(0, 0, -0.26), mat=MAT_STONE_D)
    place(prism_mesh("Platform", 3.2, 3.2, 0.3, 36), "Platform", loc=(0, 0, -0.15), mat=MAT_STONE)
    # Vong tron trang tri tren mat be
    place(prism_mesh("Ring", 1.6, 1.6, 0.02, 32), "Ring", loc=(0, 0, 0.005), mat=MAT_STONE_D)
    # Cot da quanh be (2 cot gay)
    pillar_angles = [15, 80, 145, 215, 285, 330]
    for i, deg in enumerate(pillar_angles):
        a = radians(deg)
        x, y = 4.1 * cos(a), 4.1 * sin(a)
        h = 1.4 if i in (1, 4) else 2.7
        place(box_mesh("Pillar", (0.55, 0.55, h)), "Pillar%d" % i,
              loc=(x, y, h / 2.0 - 0.16), rot=(0, 0, a), mat=MAT_STONE)
        if h > 2.0:
            place(box_mesh("PillarCap", (0.75, 0.75, 0.18)), "PillarCap%d" % i,
                  loc=(x, y, h - 0.07), rot=(0, 0, a), mat=MAT_STONE_D)
    # Vai hon da
    for i, (deg, r, s) in enumerate([(45, 5.2, 0.5), (190, 5.6, 0.7), (300, 5.0, 0.4)]):
        a = radians(deg)
        place(box_mesh("Rock", (s, s * 0.8, s * 0.7)), "Rock%d" % i,
              loc=(r * cos(a), r * sin(a), s * 0.2 - 0.16), rot=(0.2, 0.1, a), mat=MAT_STONE_D)
    # Cay don gian xa xa lam nen
    for i, (deg, r) in enumerate([(100, 10.5), (215, 11.0), (335, 10.0)]):
        a = radians(deg)
        x, y = r * cos(a), r * sin(a)
        place(prism_mesh("Trunk", 0.14, 0.2, 2.4, 7), "Trunk%d" % i,
              loc=(x, y, 1.0), mat=MAT_TRUNK)
        place(prism_mesh("Leaf", 0.3, 1.5, 1.6, 8), "Leaf%d" % i,
              loc=(x, y, 2.9), mat=MAT_LEAF)
        place(prism_mesh("Leaf2", 0.2, 1.0, 1.2, 8), "Leaf2%d" % i,
              loc=(x + 0.5, y + 0.3, 3.6), mat=MAT_LEAF)

# ----------------------------------------------------------------- kiem si
def build_sword(hand, prefix):
    """Kiem gan cung vao khop tay: luoi chay doc -Z cua khung tay."""
    place(prism_mesh(prefix + "Grip", 0.021, 0.021, 0.17, 8, (0, 0, -0.06)),
          prefix + "Grip", parent=hand, mat=MAT_GRIP)
    place(box_mesh(prefix + "Guard", (0.17, 0.05, 0.028), (0, 0, -0.155)),
          prefix + "Guard", parent=hand, mat=MAT_BLADE)
    place(box_mesh(prefix + "Blade", (0.062, 0.014, 0.86), (0, 0, -0.60)),
          prefix + "Blade", parent=hand, mat=MAT_BLADE)

def build_fighter(prefix, mat_main, mat_dark):
    """Tra ve dict cac khop. Mo hinh huong +Y, cao ~1.75, kiem o tay +X."""
    F = {}
    root = joint(prefix + "Root", None, (0, 0, 0))
    F["root"] = root
    pelvis = joint(prefix + "Pelvis", root, (0, 0, 0.93))
    F["pelvis"] = pelvis
    place(box_mesh(prefix + "PelvisM", (0.34, 0.22, 0.18), (0, 0, -0.02)),
          prefix + "PelvisM", parent=pelvis, mat=mat_dark)
    spine = joint(prefix + "Spine", pelvis, (0, 0, 0.06))
    F["spine"] = spine
    place(box_mesh(prefix + "Chest", (0.40, 0.24, 0.52), (0, 0, 0.26)),
          prefix + "Chest", parent=spine, mat=mat_main)
    neck = joint(prefix + "Neck", spine, (0, 0, 0.54))
    F["neck"] = neck
    place(box_mesh(prefix + "Head", (0.21, 0.22, 0.26), (0, 0, 0.11)),
          prefix + "Head", parent=neck, mat=mat_main)
    place(box_mesh(prefix + "Crest", (0.03, 0.24, 0.10), (0, 0, 0.27)),
          prefix + "Crest", parent=neck, mat=mat_dark)

    # Tay phai (+X) cam kiem
    shR = joint(prefix + "ShR", spine, (0.25, 0, 0.46)); F["shR"] = shR
    place(box_mesh(prefix + "UpArmR", (0.11, 0.11, 0.30), (0, 0, -0.15)),
          prefix + "UpArmR", parent=shR, mat=mat_main)
    elR = joint(prefix + "ElR", shR, (0, 0, -0.30)); F["elR"] = elR
    place(box_mesh(prefix + "FoArmR", (0.10, 0.10, 0.28), (0, 0, -0.14)),
          prefix + "FoArmR", parent=elR, mat=mat_dark)
    handR = joint(prefix + "HandR", elR, (0, 0, -0.28)); F["handR"] = handR
    build_sword(handR, prefix)

    # Tay trai (-X) cam khien tron nho
    shL = joint(prefix + "ShL", spine, (-0.25, 0, 0.46)); F["shL"] = shL
    place(box_mesh(prefix + "UpArmL", (0.11, 0.11, 0.30), (0, 0, -0.15)),
          prefix + "UpArmL", parent=shL, mat=mat_main)
    elL = joint(prefix + "ElL", shL, (0, 0, -0.30)); F["elL"] = elL
    place(box_mesh(prefix + "FoArmL", (0.10, 0.10, 0.28), (0, 0, -0.14)),
          prefix + "FoArmL", parent=elL, mat=mat_dark)
    place(prism_mesh(prefix + "Shield", 0.20, 0.20, 0.035, 14),
          prefix + "Shield", parent=elL, loc=(0, 0.03, -0.17),
          rot=(pi / 2.0, 0, 0), mat=mat_dark)

    # Chan
    for side, sx in (("R", 0.11), ("L", -0.11)):
        hip = joint(prefix + "Hip" + side, pelvis, (sx, 0, -0.04))
        F["hip" + side] = hip
        place(box_mesh(prefix + "Thigh" + side, (0.14, 0.14, 0.45), (0, 0, -0.225)),
              prefix + "Thigh" + side, parent=hip, mat=mat_dark)
        knee = joint(prefix + "Knee" + side, hip, (0, 0, -0.45))
        F["knee" + side] = knee
        place(box_mesh(prefix + "Shin" + side, (0.12, 0.12, 0.43), (0, 0, -0.215)),
              prefix + "Shin" + side, parent=knee, mat=mat_main)
        place(box_mesh(prefix + "Foot" + side, (0.11, 0.26, 0.07), (0, 0.03, -0.035)),
              prefix + "Foot" + side, parent=knee, loc=(0, 0.02, -0.415), mat=mat_dark)
    return F

# ------------------------------------------------------------------ tia lua
SPARK_DEFS = [
    # (frame cham, vi tri, he so to) - vi tri = diem cham do bang SCENE_CHECK
    (120, (-0.07,  0.14, 1.10), 1.0),
    (207, (-0.13, -0.16, 1.69), 1.0),
    (300, ( 0.03,  0.14, 0.69), 0.9),
    (417, ( 0.12,  0.19, 1.56), 1.7),
]
SHARD_ROTS = [(0.3, 0.1, 0.0), (1.2, 0.4, 0.8), (2.2, -0.3, 1.6),
              (0.8, 1.1, 2.4), (1.9, 0.9, 3.1), (2.8, -0.8, 4.0),
              (0.5, 2.0, 4.7), (1.5, -1.4, 5.5), (2.5, 1.8, 5.9)]

def build_sparks():
    for idx, (frame, pos, scale) in enumerate(SPARK_DEFS):
        grp = joint("Spark%d" % idx, None, pos)
        for k, rot in enumerate(SHARD_ROTS):
            place(box_mesh("Shard", (0.018, 0.018, 0.30), (0, 0, 0.15)),
                  "Shard%d_%d" % (idx, k), parent=grp, rot=rot, mat=MAT_SPARK)
        light_data = bpy.data.lights.new("SparkLight%d" % idx, "POINT")
        light_data.energy = 0.0
        light_data.color = (1.0, 0.6, 0.2)
        lo = bpy.data.objects.new("SparkLight%d" % idx, light_data)
        bpy.context.collection.objects.link(lo)
        lo.location = pos
        for f, s in ((frame - 2, 0.001), (frame, scale), (frame + 5, 0.001),
                     (frame + 6, 0.001)):
            grp.scale = (s, s, s)
            grp.keyframe_insert("scale", frame=f)
        for f, e in ((frame - 2, 0.0), (frame, 500.0), (frame + 5, 0.0)):
            light_data.energy = e
            light_data.keyframe_insert("energy", frame=f)
        grp.scale = (0.001, 0.001, 0.001)

# -------------------------------------------------------------------- poses
# Moi pose: pelvis_z + euler (x,y,z) cho tung khop. Truc cuc bo cua nhan vat:
# rx duong o vai/khuyu = tay dua ra truoc/len; rx am o lung = cuoi ve truoc;
# khop goi rx am = can chan gap ra sau (dung tu nhien cua goi).
POSES = {
    "GUARD": dict(pelvis_z=0.93,
        spine=(-0.10, 0, 0.05), neck=(0.08, 0, 0),
        shR=(1.85, 0, -0.20), elR=(0.40, 0, 0),
        shL=(0.55, 0.30, 0), elL=(0.70, 0, 0),
        hipR=(0.38, 0, 0), kneeR=(-0.48, 0, 0),
        hipL=(-0.30, 0, 0), kneeL=(-0.30, 0, 0)),
    "WINDUP": dict(pelvis_z=0.95,
        spine=(-0.02, 0, -0.30), neck=(0.05, 0, 0.1),
        shR=(2.80, -0.10, -0.15), elR=(0.50, 0, 0),
        shL=(0.30, 0.45, 0), elL=(0.90, 0, 0),
        hipR=(0.30, 0, 0), kneeR=(-0.40, 0, 0),
        hipL=(-0.38, 0, 0), kneeL=(-0.20, 0, 0)),
    "WINDUP_BIG": dict(pelvis_z=0.97,
        spine=(0.02, 0, -0.42), neck=(0.05, 0, 0.12),
        shR=(3.00, -0.10, -0.15), elR=(0.55, 0, 0),
        shL=(0.25, 0.50, 0), elL=(0.95, 0, 0),
        hipR=(0.28, 0, 0), kneeR=(-0.38, 0, 0),
        hipL=(-0.40, 0, 0), kneeL=(-0.20, 0, 0)),
    "CHOP": dict(pelvis_z=0.90,
        spine=(-0.22, 0, 0.22), neck=(0.10, 0, 0),
        shR=(1.28, -0.05, 0.18), elR=(0.07, 0, 0),
        shL=(0.15, 0.55, 0), elL=(1.00, 0, 0),
        hipR=(0.50, 0, 0), kneeR=(-0.35, 0, 0),
        hipL=(-0.42, 0, 0), kneeL=(-0.28, 0, 0)),
    "CHOP_BIG": dict(pelvis_z=0.88,
        spine=(-0.30, 0, 0.30), neck=(0.12, 0, 0),
        shR=(1.95, -0.05, 0.30), elR=(0.20, 0, 0),
        shL=(0.10, 0.60, 0), elL=(1.05, 0, 0),
        hipR=(0.55, 0, 0), kneeR=(-0.38, 0, 0),
        hipL=(-0.45, 0, 0), kneeL=(-0.30, 0, 0)),
    "BLOCK_MID": dict(pelvis_z=0.92,
        spine=(-0.06, 0, -0.12), neck=(0.06, 0, 0),
        shR=(1.28, -0.05, 0.18), elR=(0.07, 0, 0),
        shL=(0.80, 0.25, 0), elL=(0.80, 0, 0),
        hipR=(0.36, 0, 0), kneeR=(-0.45, 0, 0),
        hipL=(-0.32, 0, 0), kneeL=(-0.28, 0, 0)),
    "BLOCK_HIGH": dict(pelvis_z=0.93,
        spine=(-0.02, 0, -0.06), neck=(0.05, 0, 0),
        shR=(1.88, -0.05, 0.18), elR=(0.07, 0, 0),
        shL=(0.85, 0.25, 0), elL=(0.80, 0, 0),
        hipR=(0.36, 0, 0), kneeR=(-0.45, 0, 0),
        hipL=(-0.32, 0, 0), kneeL=(-0.28, 0, 0)),
    "CHOP_HIGH": dict(pelvis_z=0.91,
        spine=(-0.10, 0, 0.28), neck=(0.08, 0, 0),
        shR=(1.88, -0.05, 0.18), elR=(0.07, 0, 0),
        shL=(0.15, 0.55, 0), elL=(1.00, 0, 0),
        hipR=(0.50, 0, 0), kneeR=(-0.35, 0, 0),
        hipL=(-0.42, 0, 0), kneeL=(-0.28, 0, 0)),
    "BLOCK_V2": dict(pelvis_z=0.93,
        spine=(-0.04, 0, 0.10), neck=(0.05, 0, 0),
        shR=(1.62, -0.05, 0.12), elR=(0.28, 0, 0),
        shL=(0.80, 0.25, 0), elL=(0.80, 0, 0),
        hipR=(0.36, 0, 0), kneeR=(-0.45, 0, 0),
        hipL=(-0.32, 0, 0), kneeL=(-0.28, 0, 0)),
    "BLOCK_V": dict(pelvis_z=0.93,
        spine=(-0.04, 0, 0.10), neck=(0.05, 0, 0),
        shR=(1.70, -0.15, 0), elR=(1.30, 0, 0),
        shL=(0.80, 0.25, 0), elL=(0.80, 0, 0),
        hipR=(0.36, 0, 0), kneeR=(-0.45, 0, 0),
        hipL=(-0.32, 0, 0), kneeL=(-0.28, 0, 0)),
    "BLOCK_LOW": dict(pelvis_z=0.80,
        spine=(-0.28, 0, 0), neck=(0.14, 0, 0),
        shR=(1.08, 0.05, 0.15), elR=(0.07, 0, 0),
        shL=(0.70, 0.30, 0), elL=(0.85, 0, 0),
        hipR=(0.55, 0, 0), kneeR=(-0.75, 0, 0),
        hipL=(-0.45, 0, 0), kneeL=(-0.50, 0, 0)),
    "CROUCH_GUARD": dict(pelvis_z=0.80,
        spine=(-0.20, 0, 0.05), neck=(0.12, 0, 0),
        shR=(1.75, 0, -0.20), elR=(0.45, 0, 0),
        shL=(0.60, 0.30, 0), elL=(0.75, 0, 0),
        hipR=(0.55, 0, 0), kneeR=(-0.75, 0, 0),
        hipL=(-0.45, 0, 0), kneeL=(-0.50, 0, 0)),
    "LOW_WINDUP": dict(pelvis_z=0.82,
        spine=(-0.18, 0, -0.40), neck=(0.10, 0, 0.1),
        shR=(0.75, -0.55, -0.10), elR=(0.25, 0, 0),
        shL=(0.55, 0.35, 0), elL=(0.80, 0, 0),
        hipR=(0.52, 0, 0), kneeR=(-0.70, 0, 0),
        hipL=(-0.42, 0, 0), kneeL=(-0.48, 0, 0)),
    "LOW_SLASH": dict(pelvis_z=0.81,
        spine=(-0.24, 0, 0.38), neck=(0.12, 0, -0.08),
        shR=(1.08, -0.05, 0.15), elR=(0.07, 0, 0),
        shL=(0.20, 0.55, 0), elL=(0.95, 0, 0),
        hipR=(0.55, 0, 0), kneeR=(-0.68, 0, 0),
        hipL=(-0.48, 0, 0), kneeL=(-0.45, 0, 0)),
    "RECOVER": dict(pelvis_z=0.93,
        spine=(-0.06, 0, 0), neck=(0.07, 0, 0),
        shR=(1.45, 0, -0.15), elR=(0.50, 0, 0),
        shL=(0.55, 0.30, 0), elL=(0.70, 0, 0),
        hipR=(0.38, 0, 0), kneeR=(-0.48, 0, 0),
        hipL=(-0.30, 0, 0), kneeL=(-0.30, 0, 0)),
    "FOLLOW": dict(pelvis_z=0.91,
        spine=(-0.18, 0, 0.15), neck=(0.09, 0, 0),
        shR=(1.15, 0, -0.05), elR=(0.15, 0, 0),
        shL=(0.25, 0.50, 0), elL=(0.90, 0, 0),
        hipR=(0.48, 0, 0), kneeR=(-0.36, 0, 0),
        hipL=(-0.40, 0, 0), kneeL=(-0.28, 0, 0)),
    "LOWER": dict(pelvis_z=0.93,
        spine=(-0.12, 0, 0.05), neck=(0.10, 0, 0),
        shR=(0.75, 0, -0.05), elR=(0.30, 0, 0),
        shL=(0.40, 0.35, 0), elL=(0.60, 0, 0),
        hipR=(0.32, 0, 0), kneeR=(-0.40, 0, 0),
        hipL=(-0.28, 0, 0), kneeL=(-0.26, 0, 0)),
    "LOWERED": dict(pelvis_z=0.94,
        spine=(-0.16, 0, 0), neck=(-0.22, 0, 0),
        shR=(0.38, 0, -0.05), elR=(0.28, 0, 0),
        shL=(0.35, 0.35, 0), elL=(0.55, 0, 0),
        hipR=(0.25, 0, 0), kneeR=(-0.30, 0, 0),
        hipL=(-0.22, 0, 0), kneeL=(-0.22, 0, 0)),
    "KNOCKED": dict(pelvis_z=0.94,
        spine=(0.28, 0, -0.15), neck=(-0.10, 0, 0),
        shR=(1.05, -1.00, 0), elR=(0.30, 0, 0),
        shL=(0.50, 0.70, 0), elL=(0.40, 0, 0),
        hipR=(0.20, 0, 0), kneeR=(-0.30, 0, 0),
        hipL=(-0.15, 0, 0), kneeL=(-0.35, 0, 0)),
    "STAGGER": dict(pelvis_z=0.92,
        spine=(0.34, 0, 0.12), neck=(-0.12, 0, 0),
        shR=(0.80, -0.80, 0), elR=(0.35, 0, 0),
        shL=(0.90, 0.60, 0), elL=(0.30, 0, 0),
        hipR=(0.45, 0, 0), kneeR=(-0.50, 0, 0),
        hipL=(-0.50, 0, 0), kneeL=(-0.40, 0, 0)),
    "FALL_MID": dict(pelvis_z=0.93,
        spine=(0.15, 0, 0), neck=(-0.08, 0, 0),
        shR=(2.40, -0.60, 0), elR=(0.30, 0, 0),
        shL=(2.20, 0.60, 0), elL=(0.30, 0, 0),
        hipR=(0.30, 0, 0), kneeR=(-0.50, 0, 0),
        hipL=(0.10, 0, 0), kneeL=(-0.60, 0, 0)),
    "FALLEN": dict(pelvis_z=0.93,
        spine=(0.05, 0, 0), neck=(-0.05, 0, 0),
        shR=(2.90, -0.30, 0), elR=(0.20, 0, 0),
        shL=(0.40, 0.90, 0), elL=(0.25, 0, 0),
        hipR=(0.25, 0, 0), kneeR=(-0.35, 0, 0),
        hipL=(0.05, 0, 0), kneeL=(-0.15, 0, 0)),
}
JOINT_KEYS = ["spine", "neck", "shR", "elR", "shL", "elL",
              "hipR", "kneeR", "hipL", "kneeL"]

# --------------------------------------------------------------------- beats
# (frame, A dict, B dict) - dict: pos=(x,y), pose=ten, root_rx/root_z tuy chon
def B_(pos, pose, **kw):
    d = {"pos": pos, "pose": pose}
    d.update(kw)
    return d

BEATS = [
    (1,   B_((-1.35, 0.00), "GUARD"),       B_((1.35, 0.00), "GUARD")),
    (48,  B_((-1.28, 0.18), "GUARD"),       B_((1.28, -0.18), "GUARD")),
    (96,  B_((-1.15, 0.30), "GUARD"),       B_((1.15, -0.30), "GUARD")),
    (106, B_((-0.98, 0.16), "WINDUP"),      B_((0.92, -0.16), "GUARD")),
    (120, B_((-0.85, 0.12), "CHOP"),        B_((0.85, -0.12), "BLOCK_MID")),
    (132, B_((-0.95, 0.14), "RECOVER"),     B_((0.95, -0.14), "RECOVER")),
    (160, B_((-1.05, 0.20), "GUARD"),       B_((1.05, -0.20), "GUARD")),
    (186, B_((-1.00, 0.15), "GUARD"),       B_((0.95, -0.12), "WINDUP")),
    (198, B_((-0.88, 0.12), "BLOCK_HIGH"),  B_((0.92, -0.14), "WINDUP")),
    (207, B_((-0.85, 0.12), "BLOCK_HIGH"),  B_((0.85, -0.12), "CHOP_HIGH")),
    (220, B_((-1.02, 0.14), "RECOVER"),     B_((0.98, -0.12), "RECOVER")),
    (248, B_((-1.02, 0.12), "GUARD"),       B_((1.00, -0.12), "GUARD")),
    (272, B_((-0.98, 0.08), "CROUCH_GUARD"), B_((0.98, -0.08), "CROUCH_GUARD")),
    (288, B_((-0.92, 0.12), "LOW_WINDUP"),  B_((0.90, -0.10), "CROUCH_GUARD")),
    (300, B_((-0.85, 0.10), "LOW_SLASH"),   B_((0.85, -0.10), "BLOCK_LOW")),
    (314, B_((-0.95, 0.08), "CROUCH_GUARD"), B_((1.00, -0.06), "CROUCH_GUARD")),
    (344, B_((-0.95, 0.05), "GUARD"),       B_((0.95, -0.05), "GUARD")),
    (368, B_((-0.80, 0.02), "GUARD"),       B_((0.85, -0.02), "GUARD")),
    (392, B_((-0.85, 0.02), "WINDUP_BIG"),  B_((0.88, -0.02), "GUARD")),
    (406, B_((-0.78, 0.04), "WINDUP_BIG"),  B_((0.86, -0.04), "BLOCK_V2")),
    (417, B_((-0.64, 0.14), "CHOP_BIG"),    B_((0.80, -0.04), "BLOCK_V2")),
    (424, B_((-0.60, 0.00), "FOLLOW"),      B_((0.94, 0.00), "KNOCKED")),
    (436, B_((-0.62, 0.00), "GUARD"),       B_((1.02, 0.04), "STAGGER")),
    (448, B_((-0.60, 0.00), "GUARD"),       B_((1.10, 0.05), "STAGGER", root_rx=0.25)),
    (460, B_((-0.55, 0.00), "LOWER"),       B_((1.14, 0.05), "FALL_MID", root_rx=0.85)),
    (472, B_((-0.52, 0.00), "LOWERED"),     B_((1.16, 0.05), "FALLEN", root_rx=1.42, root_z=0.03)),
    (480, B_((-0.52, 0.00), "LOWERED"),     B_((1.16, 0.05), "FALLEN", root_rx=1.42, root_z=0.03)),
]

def apply_beats(figA, figB):
    for frame, da, db in BEATS:
        for fig, d, opp in ((figA, da, db), (figB, db, da)):
            pose = POSES[d["pose"]]
            x, y = d["pos"]
            ox, oy = opp["pos"]
            theta = atan2(-(ox - x), (oy - y))  # huong mat ve phia doi thu
            root = fig["root"]
            root.location = (x, y, d.get("root_z", 0.0))
            root.rotation_euler = (d.get("root_rx", 0.0), 0.0, theta)
            root.keyframe_insert("location", frame=frame)
            root.keyframe_insert("rotation_euler", frame=frame)
            fig["pelvis"].location = (0.0, 0.0, pose["pelvis_z"])
            fig["pelvis"].keyframe_insert("location", frame=frame)
            for jk in JOINT_KEYS:
                ob = fig[jk]
                ob.rotation_euler = pose[jk]
                ob.keyframe_insert("rotation_euler", frame=frame)

# ------------------------------------------------------------------- camera
CAM_KEYS = [
    (1,   (5.4, -5.4, 2.7)),
    (160, (6.6, 2.8, 2.3)),
    (320, (1.8, 6.3, 2.1)),
    (480, (-3.4, 4.6, 1.8)),
]

def build_camera():
    target = joint("CamTarget", None, (0, 0, 1.05))
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 42.0
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    for f, loc in CAM_KEYS:
        cam.location = loc
        cam.keyframe_insert("location", frame=f)
    bpy.context.scene.camera = cam
    return cam

# -------------------------------------------------------------------- lights
def build_lights():
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.012, 0.015, 0.028, 1.0)
    bg.inputs[1].default_value = 0.35
    bpy.context.scene.world = world

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = 0.35
    sun_data.color = (1.0, 0.92, 0.82)
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (radians(52), radians(8), radians(-38))

    fill_data = bpy.data.lights.new("Fill", "POINT")
    fill_data.energy = 260.0
    fill_data.color = (0.75, 0.85, 1.0)
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (0, 0, 4.6)

    rim_data = bpy.data.lights.new("Rim", "SUN")
    rim_data.energy = 1.4
    rim_data.color = (0.55, 0.7, 1.0)
    rim = bpy.data.objects.new("Rim", rim_data)
    bpy.context.collection.objects.link(rim)
    rim.rotation_euler = (radians(65), 0, radians(140))

# ------------------------------------------------------------------ kiem tra
def seg_seg_dist(p1, q1, p2, q2):
    """Khoang cach nho nhat giua 2 doan thang (chuan Ericson)."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1.dot(d1), d2.dot(d2), d2.dot(r)
    c = d1.dot(r)
    b = d1.dot(d2)
    denom = a * e - b * b
    s = max(0.0, min(1.0, (b * f - c * e) / denom)) if denom > 1e-9 else 0.0
    t = (b * s + f) / e if e > 1e-9 else 0.0
    t = max(0.0, min(1.0, t))
    s = max(0.0, min(1.0, (b * t - c) / a)) if a > 1e-9 else 0.0
    t = max(0.0, min(1.0, (b * s + f) / e)) if e > 1e-9 else 0.0
    c1, c2 = p1 + d1 * s, p2 + d2 * t
    return (c1 - c2).length, (c1 + c2) / 2.0

def run_checks(figA, figB):
    scene = bpy.context.scene
    print("=== SCENE CHECK ===")
    for f in CLASH_FRAMES:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        segs = []
        for fig in (figA, figB):
            mw = fig["handR"].matrix_world
            base = mw @ Vector((0, 0, -0.17))
            tip = mw @ Vector((0, 0, -1.03))
            segs.append((base, tip))
        dist, mid = seg_seg_dist(segs[0][0], segs[0][1], segs[1][0], segs[1][1])
        print("CLASH f=%d dist=%.3f mid=(%.2f, %.2f, %.2f)" %
              (f, dist, mid.x, mid.y, mid.z))
        if dist > 0.30:
            for tag, (b0, b1) in zip(("A", "B"), segs):
                print("  blade%s base=(%.2f, %.2f, %.2f) tip=(%.2f, %.2f, %.2f)"
                      % (tag, b0.x, b0.y, b0.z, b1.x, b1.y, b1.z))
    print("objects:", len(bpy.data.objects))
    print("=== CHECK DONE ===")

# ----------------------------------------------------------------------- main
def main():
    scene = bpy.context.scene

    build_arena()
    figA = build_fighter("A_", MAT_BLUE, MAT_BLUE_D)
    figB = build_fighter("B_", MAT_RED, MAT_RED_D)
    build_sparks()
    apply_beats(figA, figB)
    build_camera()
    build_lights()

    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_motion_blur = False

    scene.render.engine = "CYCLES"
    cyc = scene.cycles
    cyc.device = "CPU"
    cyc.samples = 32
    cyc.use_adaptive_sampling = True
    cyc.adaptive_threshold = 0.05
    cyc.max_bounces = 4
    cyc.diffuse_bounces = 2
    cyc.glossy_bounces = 2
    cyc.transmission_bounces = 0
    try:
        cyc.use_denoising = True
        cyc.denoiser = "OPENIMAGEDENOISE"
    except Exception as exc:
        print("denoise khong bat duoc:", exc)
    scene.render.use_persistent_data = True

    if CHECK_MODE:
        run_checks(figA, figB)
    if NO_RENDER:
        print("NO_RENDER: da dung canh xong, bo qua render. Tong %.1fs"
              % (time.time() - START_TIME))
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    scene.render.filepath = os.path.join(OUT_DIR, "f")
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE frames=%d-%d vao %s trong %.1fs (tong %.1fs)"
          % (FRAME_START, FRAME_END, OUT_DIR, time.time() - t0,
             time.time() - START_TIME))

main()
