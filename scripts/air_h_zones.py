"""Area-weighted h of the external-air CFD per skin zone (fins, barrel, faces...), to calibrate fin_screen.py.
    python3 air_h_zones.py <air_case> <time> [T_wall_K]      (ascii polyMesh + <time>/wallHeatFlux)"""
import re, sys
import numpy as np
air, time = sys.argv[1:3]; TW = float(sys.argv[3]) if len(sys.argv) > 3 else 373.15; TA = 313.15


def flist(path):
    t = open(path).read(); m = re.search(r"\n(\d+)\s*\n\(", t); return t[m.end():], int(m.group(1))


def patch(path, name):
    t = open(path).read(); i = t.index("boundaryField"); j = re.search(r"\n\s*%s\s*\n\s*\{" % name, t[i:]).end() + i
    m = re.search(r"value\s+nonuniform\s+List<scalar>\s*(\d+)\s*\(", t[j:]); s = j + m.end()
    return np.array(t[s: t.index("\n)", s)].split(), float)


b = open(f"{air}/constant/polyMesh/boundary").read()
m = re.search(r"motor\s*\{[^}]*nFaces\s+(\d+);\s*startFace\s+(\d+);", b); n, s0 = int(m.group(1)), int(m.group(2))
body, _ = flist(f"{air}/constant/polyMesh/points")
P = np.array(body[: body.index("\n)")].replace("(", " ").replace(")", " ").split(), float).reshape(-1, 3)
body, _ = flist(f"{air}/constant/polyMesh/faces")
F = re.findall(r"\d+\(([\d ]+)\)", body[: body.index("\n)\n")])[s0: s0 + n]
A = np.zeros(n); C = np.zeros((n, 3))
for k, f in enumerate(F):
    v = P[list(map(int, f.split()))]; c = v.mean(0)
    A[k] = 0.5 * np.linalg.norm(sum(np.cross(v[i] - c, v[(i + 1) % len(v)] - c) for i in range(len(v)))); C[k] = c
q = np.abs(patch(f"{air}/{time}/wallHeatFlux", "motor")); h = q / (TW - TA)
x, y, z = (C * 1e3).T if C.max() < 1 else C.T; r = np.hypot(x, y)
zones = {"fin flanks+tips (r>86.6, z -45..31)": (r > 86.6) & (z > -45) & (z < 31),
         "barrel between fins (r<=86.6, z -45..31)": (r <= 86.6) & (r > 80) & (z > -45) & (z < 31),
         "bare barrel front (z<-45, r>80)": (z <= -45) & (r > 80) & (z > -52.0),
         "bare barrel rear + bosses (z 31..67.5, r>80)": (z >= 31) & (z < 67.4) & (r > 80),
         "rear flange r90 (z 67.5..75.5)": (z >= 67.4) & (z <= 75.6) & (r > 85),
         "drive-end face (z<=-52)": z <= -52.0, "rear cover face (z>75.6)": z > 75.6}
tot = 0
for k, mk in zones.items():
    tot += mk.sum()
    print(f"{k:46s} A {A[mk].sum()*1e4:8.1f} cm2  h {np.sum(h[mk]*A[mk])/max(A[mk].sum(),1e-12):6.2f}  G {np.sum(h[mk]*A[mk]):6.3f} W/K")
o = ~np.any(list(zones.values()), axis=0)
print(f"{'other':46s} A {A[o].sum()*1e4:8.1f} cm2  h {np.sum(h[o]*A[o])/max(A[o].sum(),1e-12):6.2f}  G {np.sum(h[o]*A[o]):6.3f} W/K")
print(f"TOTAL A {A.sum()*1e4:.1f} cm2  hA {np.sum(h*A):.3f} W/K  h_mean {np.sum(h*A)/A.sum():.2f}; units scale {'mm' if C.max()>1 else 'm'}")
