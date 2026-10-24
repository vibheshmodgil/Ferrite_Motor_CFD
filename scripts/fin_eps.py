"""Per-face emissivity factor for a fin array: radiation leaves only through the array envelope.

    python3 fin_eps.py <base_case> <h.json in> <h.json out> <R_tip_mm> <z0_mm> <z1_mm>

Faces of the housing skin (defaultFaces) inside the finned span z0..z1 with r < R_tip - 0.3 mm (fin flanks and the
channel bases) get the factor s = A_openings / A_(flanks+bases), A_openings = 2 pi R_tip (z1 - z0) - A_tips; tips and
every other face keep 1. make_case.py multiplies EMISSIVITY by the list "eps_defaultFaces" of the housing.
Above z 49 mm the gland sector (-5..110 deg) has no fins and stays at 1.
"""
import json, re, sys
import numpy as np

base, hin, hout = sys.argv[1:4]; RT, Z0, Z1 = (float(v) * 1e-3 for v in sys.argv[4:7]); R0 = 0.086
pm = f"{base}/constant/housing/polyMesh"


def body(path):
    t = open(path).read(); m = re.search(r"\n(\d+)\s*\n\(", t); return t[m.end():]


b = open(f"{pm}/boundary").read()
m = re.search(r"defaultFaces\s*\{[^}]*nFaces\s+(\d+);\s*startFace\s+(\d+);", b); n, s0 = int(m.group(1)), int(m.group(2))
t = body(f"{pm}/points"); P = np.array(t[: t.index("\n)")].replace("(", " ").replace(")", " ").split(), float).reshape(-1, 3)
t = body(f"{pm}/faces"); F = re.findall(r"\d+\(([\d ]+)\)", t[: t.index("\n)\n")])[s0: s0 + n]
A = np.zeros(n); C = np.zeros((n, 3))
for k, f in enumerate(F):
    v = P[list(map(int, f.split()))]; c = v.mean(0); C[k] = c
    A[k] = 0.5 * np.linalg.norm(sum(np.cross(v[i] - c, v[(i + 1) % len(v)] - c) for i in range(len(v))))
r = np.hypot(C[:, 0], C[:, 1]); z = C[:, 2]; ang = np.degrees(np.arctan2(C[:, 1], C[:, 0]))
gland = (z > 0.049) & (ang > -5) & (ang < 110)
span = (z > Z0) & (z < Z1) & (r > R0 - 0.0003) & ~gland
inner = span & (r < RT - 0.0003); tips = span & (r >= RT - 0.0003)
A_open = 2 * np.pi * RT * (Z1 - Z0) - A[tips].sum()
s = A_open / A[inner].sum()
eps = np.ones(n); eps[inner] = s
h = json.load(open(hin)); h["housing"]["eps_defaultFaces"] = eps.tolist(); json.dump(h, open(hout, "w"))
print(f"faces {n}, skin {A.sum()*1e4:.0f} cm2; flanks+bases {inner.sum()} faces {A[inner].sum()*1e4:.0f} cm2, "
      f"tips {A[tips].sum()*1e4:.0f} cm2, openings {A_open*1e4:.0f} cm2 -> eps factor {s:.3f}; "
      f"radiating area {np.sum(eps*A)*1e4:.0f} cm2")
