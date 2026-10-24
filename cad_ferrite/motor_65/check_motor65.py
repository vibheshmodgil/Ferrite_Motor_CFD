"""Whole-motor check, variant 65 (65 mm stator, 66 mm rotor, terminals inside the housing) -> CHECKS_motor65.txt
1. interference volume between every pair of solids whose boxes touch (coils excluded: checked by centreline)
2. clearances that matter (air gap, end windings, busbar, terminal bars, seals)
3. coil wire (centreline, r 1.5) against every new part
4. masses, length, IP67 sealing list
    python check_motor65.py
"""
import json, math, os, itertools, time
import numpy as np
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.gp import gp_Trsf, gp_Mat, gp_XYZ
from OCP.TopLoc import TopLoc_Location

D = os.path.dirname(os.path.abspath(__file__))
I = json.load(open(os.path.join(D, "instances.json")))
G = json.load(open(os.path.join(D, "geom_sp.json")))
DIMS, RW = I["dims"], 1.5
STATOR_STEP = {}
cache = {}


def load(name):
    if name not in cache:
        f = STATOR_STEP.get(name, name + ".step")
        cache[name] = cq.importers.importStep(os.path.join(D, f)).val()
    return cache[name]


def placed(i):
    R, t = i["R"], i["t"]
    tr = gp_Trsf()
    tr.SetValues(R[0][0], R[0][1], R[0][2], t[0], R[1][0], R[1][1], R[1][2], t[1], R[2][0], R[2][1], R[2][2], t[2])
    return cq.Shape.cast(load(i["part"]).wrapped.Moved(TopLoc_Location(tr)))


def dist(a, b, margin=10.0):     # distance on the local piece of a big part; "10" means >= 10 mm
    vol = lambda x: x.Volume() if x.Solids() else 0.0          # point sets (coil centrelines) have no volume
    va, vb = vol(a), vol(b)
    if va > 5 * max(vb, 1e-9) or vb > 5 * max(va, 1e-9):
        big, small = (a, b) if va > vb else (b, a)
        piece = clip(big, small, margin)
        if piece.isNull() or not piece.Solids():
            return margin
        a, b = piece, small
    return BRepExtrema_DistShapeShape(a.wrapped, b.wrapped).Value()


def clip(big, small, m=1.0):    # the piece of a big part near a small one: keeps booleans with the finned housing fast
    b = small.BoundingBox()
    win = cq.Solid.makeBox(b.xlen + 2 * m, b.ylen + 2 * m, b.zlen + 2 * m, cq.Vector(b.xmin - m, b.ymin - m, b.zmin - m))
    return cq.Shape.cast(BRepAlgoAPI_Common(big.wrapped, win.wrapped).Shape())


def cvol(a, b):
    if a.Volume() > 5 * b.Volume():
        a = clip(a, b)
    elif b.Volume() > 5 * a.Volume():
        b = clip(b, a)
    c, g = BRepAlgoAPI_Common(a.wrapped, b.wrapped).Shape(), GProp_GProps()
    BRepGProp.VolumeProperties_s(c, g)
    return g.Mass()


t0 = time.time()
solids = []                                                   # (label, shape, part)
count = {}
for i in I["instances"]:
    if i["part"] == "04_coil_65":
        continue
    count[i["part"]] = count.get(i["part"], 0) + 1
    solids.append(("%s#%d" % (i["part"], count[i["part"]]), placed(i), i["part"]))
lines, bad = [], 0


def rep(name, val, lim, note="", hi=None):
    global bad
    ok = val >= lim - 1e-6 and (hi is None or val <= hi + 1e-6)
    bad += not ok
    lines.append("  %-58s %9.3f  %s %s" % (name, val, "OK" if ok else "FAIL (%s)" % ("min %.2f" % lim if hi is None else "%.2f..%.2f" % (lim, hi)), note))


lines.append("V7 MOTOR variant 65: stator 65 mm, rotor 66 mm (0.5 mm overhang each side), terminals inside the housing, radial wall glands")
# ---------------------------------------------------------------- 1. interference
# designed overlaps: O-ring squeeze; everything else must be 0 (touching faces are fits)
STATOR_OLD = {"tooth_65", "bobbin_A_65", "bobbin_B_65", "busbar_L1_65", "busbar_L2_65", "busbar_L3_65", "link_strap_65"}
SQUEEZE = {("oring_cover_2.5", "housing"), ("oring_cover_2.5", "rear_cover")}
lines.append("INTERFERENCE (volume of overlap, mm3; every pair of solids whose bounding boxes meet)")
bbs = [(l, s, p, s.BoundingBox()) for l, s, p in solids]
npair, worst = 0, []
for (la, sa, pa, ba), (lb, sb, pb, bb) in itertools.combinations(bbs, 2):
    if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
        continue
    if pa in STATOR_OLD and pb in STATOR_OLD:   # stator-to-stator: verified in ../single_plane_B and the v7 CAD checks
        continue
    npair += 1
    if npair % 50 == 0:
        print("  ... %d pairs, %.0f s" % (npair, time.time() - t0), flush=True)
    ca, cb = sa, sb                   # distance on the local piece of the bigger part (finned housing is slow whole)
    if sa.Volume() > 5 * sb.Volume():
        ca = clip(sa, sb)
    elif sb.Volume() > 5 * sa.Volume():
        cb = clip(sb, sa)
    if ca.isNull() or cb.isNull() or not ca.Solids() or not cb.Solids() or dist(ca, cb) > 1e-3:   # apart: no boolean needed
        continue
    tp = time.time()
    v = cvol(sa, sb)
    print("  %-60s %10.4f mm3  %.1f s" % (la + " x " + lb, v, time.time() - tp), flush=True)
    if v > 1e-3:
        key = tuple(sorted((pa, pb)))
        if key in {tuple(sorted(k)) for k in SQUEEZE}:
            lines.append("  %-58s %9.3f  OK O-ring squeeze (designed)" % (la + " x " + lb, v))
        else:
            worst.append((v, la, lb))
for v, la, lb in sorted(worst, reverse=True):
    rep(la + " x " + lb, -v, 0.0)
lines.append("  %d pairs with touching boxes checked, %d overlapping (excluding designed O-ring squeeze); stator-to-stator pairs: exact 1 mm stretch of the checked variant-B stator (../single_plane_B/CHECKS_spb.txt)" % (npair, len(worst)))
S = {l: s for l, s, p in solids}
first = lambda part: S[part + "#1"]
# ---------------------------------------------------------------- 2. clearances
lines.append("CLEARANCE (true minimum distance, mm)")
rep("air gap: rotor lamination x stator teeth", min(dist(first("rotor_lamination_stack"), S["tooth_65#%d" % k]) for k in (1, 4, 7)), 0.45, "", 0.55)
rb, tb = first("rotor_lamination_stack").BoundingBox(), S["tooth_65#1"].BoundingBox()
rep("rotor overhang beyond the stator, front", tb.zmin - rb.zmin, 0.45, "", 0.55)
rep("rotor overhang beyond the stator, rear", rb.zmax - tb.zmax, 0.45, "", 0.55)
for n in ("L1", "L2", "L3"):
    bar = first("terminal_bar_" + n)
    for m in ("L1", "L2", "L3"):
        if m != n:
            rep("terminal bar %s x busbar plate %s" % (n, m), dist(bar, first("busbar_%s_65" % m)), 2.0, "bar over the other nets, insulated")
            rep("terminal bar %s x terminal bar %s" % (n, m), dist(bar, first("terminal_bar_" + m)), 2.0)
    rep("terminal bar %s x straps" % n, min(dist(bar, S["link_strap_65#%d" % k]) for k in range(1, 7)), 2.0)
    rep("terminal bar %s x housing" % n, dist(bar, first("housing")), 2.0)
    rep("terminal bar %s x rear cover" % n, dist(bar, first("rear_cover")), 2.0)
for n in ("L1", "L2", "L3"):
    for part in ("housing", "rear_cover"):
        rep("busbar plate %s x %s" % (n, part), dist(first("busbar_%s_65" % n), first(part)), 2.0)
rep("straps x housing", min(dist(S["link_strap_65#%d" % k], first("housing")) for k in range(1, 7)), 2.0)
rep("lugs / studs / nuts x housing (live parts to the housing)", min(dist(S[p + "#%d" % k], first("housing")) for p in ("cable_lug_35mm2_M8", "stud_M8_press_in", "nut_M8_thin") for k in (1, 2, 3)), 0.8, "52 V: IEC 60664-1 needs ~0.2")
rep("lugs / studs / nuts x rear cover", min(dist(S[p + "#%d" % k], first("rear_cover")) for p in ("cable_lug_35mm2_M8", "stud_M8_press_in", "nut_M8_thin") for k in (1, 2, 3)), 1.5)
for k in (1, 2, 3):
    lug = S["cable_lug_35mm2_M8#%d" % k]
    rep("cable lug %d x busbar plates (any net)" % k, min(dist(lug, first("busbar_%s_65" % m)) for m in ("L1", "L2", "L3")), 2.0)
    others = [dist(lug, first("terminal_bar_" + m)) for m in ("L1", "L2", "L3")]
    rep("cable lug %d x terminal bars of other phases" % k, sorted(others)[1], 2.0, "own bar: palm sits on it")
lg = [S["cable_lug_35mm2_M8#%d" % k] for k in (1, 2, 3)]
rep("cable lug x cable lug (different phases)", min(dist(a, b) for a, b in itertools.combinations(lg, 2)), 3.0)
rep("rotor end plate x front bearing boss (axial)", dist(S["rotor_end_plate#2"], first("housing")), 1.5)
rep("rotor end plate x rear bearing boss (axial)", dist(S["rotor_end_plate#1"], first("rear_cover")), 1.5)
rep("encoder magnet x encoder PCB (sensor air gap)", dist(first("encoder_magnet_8x2"), first("encoder_pcb")), 0.5, "", 2.0)
rep("rotor x housing", dist(first("rotor_lamination_stack"), first("housing")), 2.0)
# ---------------------------------------------------------------- 3. coils (centreline) against the new parts
W = np.load(os.path.join(D, "coil_65_centreline.npy"))
ZTOP = DIMS["plane_top"]                                      # plane top 53.5 = F-lead ends
NEW = ["housing", "rear_cover", "rotor_lamination_stack", "rotor_end_plate", "terminal_bar_L1", "terminal_bar_L2", "terminal_bar_L3",
       "cable_lug_35mm2_M8", "bearing_52x30x15", "shaft"]
lines.append("COIL WIRE (centreline r 1.5) x new parts, worst over the 12 coils")
worst_c = {}
for k in range(1, 13):
    th = math.radians(30 * (k - 1) - 90)
    X = np.c_[W[:, 0] * math.cos(th) - W[:, 1] * math.sin(th), W[:, 0] * math.sin(th) + W[:, 1] * math.cos(th), W[:, 2]]
    X = X[::4]
    V = cq.Compound.makeCompound([cq.Vertex.makeVertex(*map(float, p)) for p in X])
    Vb = cq.Compound.makeCompound([cq.Vertex.makeVertex(*map(float, p)) for p in X[X[:, 2] <= ZTOP - RW]])   # lead ends are cut flat
    for l, s, p in solids:
        if p in NEW:
            d = dist(Vb if p.startswith(("terminal_bar", "cable_lug")) else V, s) - RW
            worst_c[p] = min(worst_c.get(p, 1e9), d)
rep("coil lead flat end faces (plate top) x terminal bars (other nets)", DIMS["bar_z"][0] - ZTOP, 0.8, "weld bead must stay under 0.8 mm")
for p, d in worst_c.items():
    lim = 0.8 if p.startswith(("terminal_bar", "cable_lug")) else 1.5
    note = "F-lead tips are flush with the plate top; weld bead <= 0.8 mm" if p.startswith("terminal_bar") else ""
    rep("coil wire x %s" % p, d, lim, note)
# ---------------------------------------------------------------- 4. summary
lines.append("SIZE")
hub, rear, fins, gl = DIMS["hub_face"], DIMS["rear_face"], DIMS["fin_r"], DIMS["gland_r"]
lines.append("  body length (drive-end hub face z %.1f to rear cover z %.1f): %.1f mm; output shaft %.1f mm beyond" % (hub, rear, rear - hub, hub - DIMS["shaft_end_front"]))
lines.append("  housing face to face (z %.1f to %.1f): %.1f mm; fin diameter %.0f mm; gland seats at r %.0f, gland domes to r %.0f" % (DIMS["housing_front_face"], rear, rear - DIMS["housing_front_face"], 2 * fins, gl, gl + 22))
lines.append("  terminal studs, lugs and nuts are inside the housing; cables leave radially through the wall glands")
lines.append("MASS (g, all instances; stator parts from their own volumes)")
mass, dens = {}, {"Cu": 8.96e-3, "lam": 7.65e-3, "PA66GF30": 1.36e-3}
STATOR_MAT = {"tooth_65": "lam", "bobbin_A_65": "PA66GF30", "bobbin_B_65": "PA66GF30",
              "busbar_L1_65": "Cu", "busbar_L2_65": "Cu", "busbar_L3_65": "Cu", "link_strap_65": "Cu"}
for l, s, p in solids:
    if p in I["parts"]:
        m, mat = I["parts"][p]["mass_g"], I["parts"][p]["mat"]
    else:
        mat = STATOR_MAT[p]; m = s.Volume() * dens[mat]
    grp = {"lam": "steel laminations", "steel": "steel (shaft, bearings, hardware)", "Al": "aluminium (housing, cover, cap, end plates)",
           "ferrite": "ferrite magnets", "Cu": "copper (busbar, straps, terminals, lugs)"}.get(mat, "plastics / rubber / PCB")
    mass[grp] = mass.get(grp, 0) + m
coil_m = math.pi * (G["wire"]["bare"] / 2) ** 2 * np.sum(np.linalg.norm(np.diff(W, axis=0), axis=1)) * 8.96e-3 * 12
mass["copper (12 coils)"] = coil_m
for k, v in sorted(mass.items(), key=lambda x: -x[1]):
    lines.append("  %-45s %8.0f" % (k, v))
lines.append("  %-45s %8.0f   (cables outside the glands excluded)" % ("TOTAL", sum(mass.values())))
lines.append("IP67 SEALING (every path from outside to inside)")
for s in ["drive-end shaft: radial lip seal 30x47x7 (NBR / FKM for > 100 C), runs on the ground shaft, outboard of the locating bearing",
          "rear: cover spigot in the housing bore, radial O-ring 2.5 cord (squeeze checked above), 5 x M5; no shaft exit (closed end)",
          "phase cables: 3 x M20 IP68 glands screwed into flat bosses on the housing wall (O-ring under the gland body); terminals stay inside",
          "encoder cable: 1 x M16 IP68 gland in a wall boss",
          "castings: housing and cover in AlSi10Mg, impregnated (vacuum) against porosity; validate with 1 m / 30 min immersion test (IEC 60529)",
          "breathing: add a PTFE vent membrane (M12, IP68) in the cap if the motor sees fast temperature cycles in water"]:
    lines.append("  - " + s)
lines.append("VERDICT: %s   (%.0f s)" % ("ALL OK" if bad == 0 else "%d FAIL" % bad, time.time() - t0))
open(os.path.join(D, "CHECKS_motor65.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
