"""Housing fin variants from the CAD housing (motor_65/housing.step) -> mesh/fins/<name>/housing.step + info.json

    .venv/Scripts/python -I scripts/make_housing_fins.py <name>        names: see VARIANTS

The 10 CAD fins are cut off (r > 86, z -44.5..30.5) and replaced by tapered fins, 4 mm at the root (r 86) and 2.5 mm
at the tip, root sunk 0.5 mm into the barrel, over z -44.25..67.5: rings (revolved) or axial (extruded). Every fin is
cut back to r 18 mm round the 4 gland axes (L1/L3/L2 at 12/50.5/72 deg, encoder 92 deg, z 62.25).
"""
import gmsh, json, math, os, sys

CAD = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
R0, TB, TT = 86.0, 4.0, 2.5                    # mm: barrel radius, fin root / tip thickness
Z0, Z1 = -44.25, 67.5                           # finned span (user: z -43..67.5; rear flange r 90 from 67.5)
GLANDS, Z_GLAND, R_CUT = (12.0, 50.5, 72.0, 92.0), 62.25, 18.0   # gland axes (deg), axis z, cut-out radius round each
VARIANTS = {   # kind, height H, count/pitch
    "ring_h16_p11.5": ("ring", 16.0, [Z0 + TB / 2 + 11.5 * k for k in range(10)]),
    "axial_h16_n68":  ("axial", 16.0, 68),
    "axial_h12_n70":  ("axial", 12.0, 70),
}
name = sys.argv[1]; kind, H, arg = VARIANTS[name]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh", "fins", name); os.makedirs(OUT, exist_ok=True)

occ = gmsh.model.occ
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-3)
house = [(d, t) for d, t in occ.importShapes(os.path.join(CAD, "housing.step")) if d == 3]
occ.synchronize(); v0 = sum(occ.getMass(3, t) for _, t in house)
# the 10 CAD fins out (r > 86, z -44.5..30.5; nothing else of the housing is there)
ring = occ.cut([(3, occ.addCylinder(0, 0, -44.5, 0, 0, 75.0, 100.0))], [(3, occ.addCylinder(0, 0, -45, 0, 0, 76, R0))])[0]
house, _ = occ.cut(house, ring)


def surf(pts, plane):
    p = [occ.addPoint(*((x, 0, z) if plane == "rz" else (x, y, 0))) for x, *rest in pts for z in [rest[0]] for y in [rest[0]]]
    return occ.addPlaneSurface([occ.addCurveLoop([occ.addLine(p[i], p[(i + 1) % len(p)]) for i in range(len(p))])])


fins = []
if kind == "ring":
    for zc in arg:   # (r, z) profile: 0.5 mm root inside the barrel, then the taper 4 -> 2.5 mm
        s2 = surf([(R0 - 0.5, zc - TB / 2), (R0, zc - TB / 2), (R0 + H, zc - TT / 2), (R0 + H, zc + TT / 2),
                   (R0, zc + TB / 2), (R0 - 0.5, zc + TB / 2)], "rz")
        fins += [e for e in occ.revolve([(2, s2)], 0, 0, 0, 0, 0, 1, 2 * math.pi) if e[0] == 3]
else:
    for k in range(arg):   # (x, y) section on the +x axis, extruded along z, then rotated into place
        s2 = surf([(R0 - 0.5, -TB / 2), (R0, -TB / 2), (R0 + H, -TT / 2), (R0 + H, TT / 2), (R0, TB / 2), (R0 - 0.5, TB / 2)], "xy")
        occ.translate([(2, s2)], 0, 0, Z0)
        v = [e for e in occ.extrude([(2, s2)], 0, 0, Z1 - Z0) if e[0] == 3]
        occ.rotate(v, 0, 0, 0, 0, 0, 1, 2 * math.pi * k / arg)
        fins += v
# cut-outs round the cable glands (seat r 13 + room for the gland nut and a spanner)
cuts = []
for a in GLANDS:
    c = occ.addCylinder(70, 0, Z_GLAND, 50, 0, 0, R_CUT)
    occ.rotate([(3, c)], 0, 0, 0, 0, 0, 1, math.radians(a)); cuts.append((3, c))
fins, _ = occ.cut(fins, cuts)
house, _ = occ.fuse(house, fins)
occ.removeAllDuplicates(); occ.synchronize()
house = [(3, t) for _, t in gmsh.model.getEntities(3)]
islands = [e for e in house if occ.getMass(*e) < 1000]        # fin slivers cut loose between two gland cut-outs
print("dropped islands mm3:", [round(occ.getMass(*e), 1) for e in islands])
occ.remove(islands, recursive=True); occ.synchronize(); house = [e for e in house if e not in islands]
if len(house) > 1:
    print("VOLS", [(t, occ.getMass(3, t), gmsh.model.getBoundingBox(3, t)) for _, t in house])
assert len(house) == 1, house
v1 = occ.getMass(3, house[0][1])
gmsh.write(os.path.join(OUT, "housing.step"))
info = dict(name=name, kind=kind, H_mm=H, tip_r_mm=R0 + H, span_z_mm=[Z0, Z1], fins=arg, gland_cut_r_mm=R_CUT,
            housing_volume_cm3=v1 / 1e3, d_volume_cm3=(v1 - v0) / 1e3, d_mass_kg=(v1 - v0) * 2.68e-6,
            d_C_kJK=(v1 - v0) * 2.68e-6 * 0.9)
json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
print(info)
