"""Why the rear (non-drive-end) end winding runs hotter than the front one: detailed-model numbers.

    .venv/Scripts/python -I scripts/endwinding_asym.py <case_label> <vtk_dir> <lp> [patch_vtk_dir]

<vtk_dir> holds the region volume VTKs (export3d.sh / foamToVTK: copper, inair, ...). <patch_vtk_dir> (optional)
holds foamToVTK patch files (<region>/<patch>/<patch>_N.vtk) with wallHeatFlux, for the heat flows per end.
Coil cells are told apart from busbar/strap/tbar with the copper cellZones (cu_zones.json next to the VTKs).
Front = drive end (z < 0), rear = non-drive end (z > 0); end turns |z| > 32.5 mm (stack half length).
Prints a JSON block.
"""
import glob, json, os, re, sys
import numpy as np
import meshio

label, vd, lp = sys.argv[1:4]; pd = sys.argv[4] if len(sys.argv) > 4 else None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))[lp]; Q = LP["Q"]
ZS = 0.0325; A_TC = 0.00393


def vol(path):
    m = meshio.read(path); c = m.cells_dict["tetra"]; p = m.points[c]
    V = np.abs(np.einsum("ij,ij->i", p[:, 1] - p[:, 0], np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]))) / 6
    return p.mean(1), V, {k: v[0] for k, v in m.cell_data.items()}


def poly(path):
    """legacy binary POLYDATA (foamToVTK): face centres, areas, cell fields"""
    b = open(path, "rb").read()
    m = re.search(rb"POINTS (\d+) float\n", b); n = int(m.group(1)); i = m.end()
    P = np.frombuffer(b, ">f4", 3 * n, i).reshape(n, 3).astype(float)
    m = re.search(rb"POLYGONS (\d+) (\d+)\n", b); nf, sz = int(m.group(1)), int(m.group(2))
    L = np.frombuffer(b, ">i4", sz, m.end())
    C = np.zeros((nf, 3)); A = np.zeros(nf); k = 0
    for f in range(nf):
        c = L[k]; v = P[L[k + 1: k + 1 + c]]; k += 1 + c; cc = v.mean(0); C[f] = cc
        A[f] = 0.5 * np.linalg.norm(np.cross(v - cc, np.roll(v, -1, 0) - cc).sum(0))
    F = {}
    for m in re.finditer(rb"\n(\w+) 1 (\d+) float\n", b):
        F[m.group(1).decode()] = np.frombuffer(b, ">f4", int(m.group(2)), m.end()).astype(float)
    return C, A, F


out = {"case": label}
xc, V, d = vol(glob.glob(os.path.join(vd, "copper*.vtk"))[0])
T = d["T"] - 273.15; cid = d["cellID"].astype(int)
zones = json.load(open(os.path.join(os.path.dirname(os.path.abspath(vd)) if not os.path.exists(os.path.join(vd, "cu_zones.json")) else vd, "cu_zones.json")))
zid = np.full(len(T), "", object)
for zn, cells in zones.items():
    zid[np.isin(cid, cells)] = zn
coil = zid == "coil"; z = xc[:, 2]
Vc = V[coil].sum()
qref = Q["winding_100C"] / Vc; qac = Q.get("winding_ac", 0) / Vc
qcell = np.where(coil, V * (qac + qref * (1 + A_TC * (T + 273.15 - 373.15))), 0.0)
RHO20 = 1.72e-8
for zn, q20 in (("busbar", None), ("strap", RHO20 * LP["J_strap"] ** 2), ("tbar", RHO20 * LP["J_tbar"] ** 2)):
    mk = zid == zn
    q20 = LP["busbar_20C"] / V[mk].sum() if q20 is None else q20
    qcell[mk] = V[mk] * q20 * (1 + A_TC * (T[mk] - 20.0))


def stats(mk):
    return {"T_max_C": round(float(T[mk].max()), 1), "T_mean_C": round(float(np.sum(T[mk] * V[mk]) / V[mk].sum()), 1),
            "volume_cm3": round(float(V[mk].sum() * 1e6), 1), "joule_W": round(float(qcell[mk].sum()), 1)}


out["coil_front_half"] = stats(coil & (z < 0)); out["coil_rear_half"] = stats(coil & (z > 0))
out["endturns_front"] = stats(coil & (z < -ZS)); out["endturns_rear"] = stats(coil & (z > ZS))
out["coil_slot_part"] = stats(coil & (np.abs(z) <= ZS))
for zn in ("busbar", "strap", "tbar"):
    mk = zid == zn
    out[zn] = stats(mk) | {"z_mm": [round(float(z[mk].min() * 1e3), 1), round(float(z[mk].max() * 1e3), 1)]}
out["bearings_W_each_side"] = round(Q.get("bearings", 0) / 2, 1)     # heatSource over both equal rings
xi, Vi, di = vol(glob.glob(os.path.join(vd, "inair*.vtk"))[0])
out["inair_end_space_cm3"] = {"front": round(float(Vi[xi[:, 2] < -ZS].sum() * 1e6), 1), "rear": round(float(Vi[xi[:, 2] > ZS].sum() * 1e6), 1)}
Ti = di["T"] - 273.15
out["inair_mean_C"] = {"front": round(float(np.sum((Ti * Vi)[xi[:, 2] < -ZS]) / Vi[xi[:, 2] < -ZS].sum()), 1),
                       "rear": round(float(np.sum((Ti * Vi)[xi[:, 2] > ZS]) / Vi[xi[:, 2] > ZS].sum()), 1)}
xh, Vh, dh = vol(glob.glob(os.path.join(vd, "housing*.vtk"))[0]); Th = dh["T"] - 273.15
out["housing_mean_C"] = {k: round(float(np.sum((Th * Vh)[mk]) / Vh[mk].sum()), 1) for k, mk in
                         (("front_end_z<-32.5", xh[:, 2] < -ZS), ("stack", np.abs(xh[:, 2]) <= ZS), ("rear_end_z>32.5", xh[:, 2] > ZS))}
if pd:
    flows = {}
    for f in sorted(glob.glob(os.path.join(pd, "*", "*", "*.vtk"))):
        r, p = f.split(os.sep)[-3:-1]
        if p.startswith("det_"):
            continue
        C, A, F = poly(f)
        if "wallHeatFlux" not in F:
            continue
        q = F["wallHeatFlux"] * A; zz = C[:, 2]
        flows[f"{r}:{p}"] = {"front_z<-32.5": round(float(q[zz < -ZS].sum()), 1), "stack": round(float(q[np.abs(zz) <= ZS].sum()), 1),
                             "rear_z>32.5": round(float(q[zz > ZS].sum()), 1)}
    out["heat_W_into_region_by_zone"] = flows
print(json.dumps(out, indent=1))
