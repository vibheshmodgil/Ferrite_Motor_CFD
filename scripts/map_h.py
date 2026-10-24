"""h on the motor skin from the external-air CFD, mapped onto the thermal model's outside patches.

    python3 map_h.py <air_case> <time> <base_solids> <out.json> [T_wall_K]

Needs (ascii) <air_case>/<time>/wallHeatFlux and C, and <base_solids>/0/<region>/C for housing and shaft
(foamPostProcess -func writeCellCentres). Writes {"housing": {"defaultFaces": [h...]}, "shaft": {...}}.
"""
import json, re, sys
import numpy as np
from scipy.spatial import cKDTree

air, time, base, out = sys.argv[1:5]
TW, TA = (float(sys.argv[5]) if len(sys.argv) > 5 else 373.15), 313.15


def patch_values(path, patch):
    txt = open(path).read()
    i = txt.index("boundaryField")
    j = re.search(r"\n\s*%s\s*\n\s*\{" % patch, txt[i:]).end() + i
    m = re.search(r"value\s+nonuniform\s+List<(scalar|vector)>\s*(\d+)\s*\(", txt[j:])
    n, start = int(m.group(2)), j + m.end()
    body = txt[start: txt.index("\n)", start)]
    v = np.array(body.replace("(", " ").replace(")", " ").split(), dtype=float)
    return v.reshape(n, -1) if m.group(1) == "vector" else v


q = np.abs(patch_values(f"{air}/{time}/wallHeatFlux", "motor"))
xa = patch_values(f"{air}/{time}/C", "motor")
h = q / (TW - TA)
tree = cKDTree(xa)
res = {}
for r in ("housing", "shaft"):
    xs = patch_values(f"{base}/0/{r}/C", "defaultFaces")
    d, k = tree.query(xs)
    res[r] = {"defaultFaces": h[k].tolist()}
    print(f"{r}: {len(xs)} faces, mapped from {len(xa)}; max map distance {d.max()*1e3:.2f} mm; "
          f"h mean {h[k].mean():.2f}  min {h[k].min():.2f}  max {h[k].max():.2f} W/m2K")
json.dump(res, open(out, "w"))
print("area-weighting skipped: h mean above is per face")   # ponytail: faces are ~uniform size on the skin
