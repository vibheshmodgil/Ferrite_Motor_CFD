"""65 mm stator from the 63 mm variant-B parts: everything at z > 0 moves +1 mm, everything at z < 0 moves -1 mm,
and the 2 mm gap is filled with the parts' own (constant) slot cross-section.
    python build_stator65.py   # -> *_65.step, coil_65_centreline.npy, stator65_placements.json
"""
import json, os
import numpy as np
import cadquery as cq

D = os.path.dirname(os.path.abspath(__file__))
DZ = 1.0
V = cq.Vector
ld = lambda f: cq.importers.importStep(os.path.join(D, f)).val()
slab = lambda z0, z1: cq.Solid.makeBox(400, 400, z1 - z0, V(-200, -200, z0))


def save(name, s, ref_vol=None):
    assert len(s.Solids()) == 1 and s.isValid(), name
    cq.exporters.export(cq.Workplane().add(s), os.path.join(D, name + ".step"))
    b = s.BoundingBox()
    print("%-22s vol %9.1f%s  z %.2f..%.2f" % (name, s.Volume(), "" if ref_vol is None else " (63 mm part %.1f)" % ref_vol, b.zmin, b.zmax))


t = ld("01_tooth_segment_v7.stp")                 # prism z -31.5..31.5
save("tooth_65", t.translate(V(0, 0, DZ)).fuse(t.translate(V(0, 0, -DZ))).clean(), t.Volume())
a = ld("02_bobbin_half_A_v7.stp")                 # z 0..35.45, slot section constant from z 0
save("bobbin_A_65", a.translate(V(0, 0, DZ)).fuse(a.intersect(slab(0, DZ + 0.01))).clean(), a.Volume())
b = ld("03_bobbin_half_B_v7.stp")                 # z -36.1..0
save("bobbin_B_65", b.translate(V(0, 0, -DZ)).fuse(b.intersect(slab(-DZ - 0.01, 0))).clean(), b.Volume())
for n in ("busbar_L1_B", "busbar_L2_B", "busbar_L3_B"):
    s = ld(n + ".step")
    save(n.replace("_B", "_65"), s.translate(V(0, 0, DZ)))
save("link_strap_65", ld("link_strap.step").translate(V(0, 0, DZ)))

W = np.load(os.path.join(D, "coil_spb_centreline.npy"))   # tooth-local; the slot runs cross z = 0 axially
W2 = W.copy()
W2[:, 2] += np.where(W[:, 2] > 0, DZ, np.where(W[:, 2] < 0, -DZ, 0.0))
np.save(os.path.join(D, "coil_65_centreline.npy"), W2)
L = lambda X: np.sum(np.linalg.norm(np.diff(X, axis=0), axis=1))
print("coil centreline %.1f mm (63 mm stator: %.1f mm, +%.1f)  z %.2f..%.2f" % (L(W2), L(W), L(W2) - L(W), W2[:, 2].min(), W2[:, 2].max()))
crossings = np.sum(np.sign(W[:-1, 2]) != np.sign(W[1:, 2]))
print("slot crossings of z = 0:", crossings)
SP = json.load(open(os.path.join(D, "stator_placements.json")))
SP["plane_z"] = [z + DZ for z in SP["plane_z"]]
SP["strap_z"] = [z + DZ for z in SP["strap_z"]]
SP["stack"] = 65.0
json.dump(SP, open(os.path.join(D, "stator65_placements.json"), "w"), indent=1)
