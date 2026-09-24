# Desk stand for a round panel-mount thermo-hygrometer (Ø41 body, Ø45 front flange).
# The sensor clicks into a Ø41 hole in a tilted face plate like into a panel; the flange rests on the front.
# Run: blender -b -P build_holder.py   (or exec in Blender / via blender-mcp). Units = mm.
import bpy, bmesh, math, os

BODY_D   = 41.0   # measured
HOLE_D   = BODY_D + 0.4  # fit clearance; clips still grip. Tune after a test print
FLANGE_D = 45.0   # measured
BODY_LEN = 20.0   # ponytail: guessed, measure body depth behind the flange
PLATE_T  = 3.0    # "panel" thickness; clips on the body need a thin panel
RIM      = 6.0    # bezel visible around the flange
R        = FLANGE_D / 2 + RIM
TILT     = 15.0   # lean back from vertical, like a phone stand
BASE_W, BASE_D, BASE_T = 64.0, 62.0, 4.0
CLIP_W   = 5.0    # two spring clips on the body, strictly top and bottom
CLIP_H   = 1.5    # notch depth past the hole; clips stick out ~2 and don't press flush -> 0.5 mm squeeze. Tune
LEG_W    = 5.0    # side struts (behind plate, outside body)
t = math.radians(TILT)

def cyl(r, depth, loc, rot=(0, 0, 0), v=128):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=depth, location=loc, rotation=rot)
    return bpy.context.object

def bevel(o, w, seg=4, limit='ANGLE'):
    m = o.modifiers.new('bev', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = limit
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=m.name)

def boolean(target, cutter, op):
    m = target.modifiers.new(op, 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter)

def prism(name, pts_yz, x0, x1):
    # extrude a YZ polygon along X
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in pts_yz]
    b = [bm.verts.new((x1, y, z)) for y, z in pts_yz]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(a)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def plate_pt(ly, lz, zc):
    # local plate coords (ly: thickness axis, +back; lz: up the plate) -> world (y, z)
    return ly * math.cos(t) + lz * math.sin(t), -ly * math.sin(t) + lz * math.cos(t) + zc

def build(name='holder'):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    # plate centre height: disc bottom sinks 1 mm into base, body's low back edge clears base top by 1.5
    zc = max(BASE_T + R * math.cos(t) - 1, BASE_T + 1.5 + BODY_D / 2 * math.cos(t) + BODY_LEN * math.sin(t))
    rot = (math.pi / 2 - t, 0, 0)  # cylinder axis Z -> plate normal, top leaning back
    plate = cyl(R, PLATE_T, (0, 0, zc), rot); bevel(plate, 1.2)
    plate.name = name
    by0 = plate_pt(0, -R, zc)[0] - 6          # base front edge a bit ahead of the plate
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, by0 + BASE_D / 2, BASE_T / 2))
    base = bpy.context.object; base.scale = (BASE_W, BASE_D, BASE_T)
    bpy.ops.object.transform_apply(scale=True); bevel(base, 1.5)
    # kickstand struts: from plate back (around centre height) down to the rear of the base
    top = plate_pt(PLATE_T / 2 - 0.5, 6, zc); low = plate_pt(PLATE_T / 2 - 0.5, -R + 4, zc)
    pts = [low, top, (by0 + BASE_D - 4, BASE_T - 0.5), (low[0], BASE_T - 0.5)]
    xi = BODY_D / 2 + 1
    legs = [prism('leg', pts, s * xi, s * (xi + LEG_W)) for s in (1, -1)]
    for o in [base] + legs: boolean(plate, o, 'UNION')
    # panel hole + clearance for the body behind the plate
    boolean(plate, cyl(HOLE_D / 2, PLATE_T + 2, (0, 0, zc), rot), 'DIFFERENCE')
    cy, cz = plate_pt(PLATE_T / 2 + 15, 0, zc)
    boolean(plate, cyl(BODY_D / 2 + 1, 30, (0, cy, cz), rot), 'DIFFERENCE')
    # clip notches, hidden behind the flange (hole r + CLIP_H < flange r), run back past the plate
    L = 25
    for sg in (1, -1):
        ly, lz = (L - PLATE_T) / 2 - 1, sg * (HOLE_D / 2 + (CLIP_H - 1) / 2)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, *plate_pt(ly, lz, zc)), rotation=(-t, 0, 0))
        n = bpy.context.object; n.scale = (CLIP_W + 1, L, CLIP_H + 1)
        bpy.ops.object.transform_apply(scale=True); boolean(plate, n, 'DIFFERENCE')
    return plate

if __name__ == '__main__':
    o = build()
    here = os.path.dirname(os.path.abspath(__file__))
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.wm.stl_export(filepath=os.path.join(here, 'holder.stl'), export_selected_objects=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, 'holder.blend'))
    bm = bmesh.new(); bm.from_mesh(o.data)
    print('NONMANIFOLD', sum(not e.is_manifold for e in bm.edges), 'DIMS', tuple(round(d, 1) for d in o.dimensions))
