"""Boundary-condition diagram on the real axial cross-section (x = 0) of the thermal model.

    .venv/Scripts/python -I scripts/bc_schematic.py <slices_dir> <out.png>
"""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

src, out = sys.argv[1], sys.argv[2]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))
PART = {"housing": ("#a7adb5", "Housing + rear cover (AlSi10Mg)"), "stator": ("#6b7078", "Stator teeth (M235-35A)"),
        "winding": ("#c98b3c", "Winding (Cu + resin)"), "rotor": ("#50555c", "Rotor stack"), "magnets": ("#26282b", "Ferrite magnets"),
        "shaft": ("#868b92", "Shaft (steel)"), "bearings": ("#c3c7cc", "Bearings"), "inair": ("#dbe9f6", "Internal air (end spaces)")}


def read_vtk(path):
    tok = open(path).read().split()
    i = tok.index("POINTS"); n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3)
    i = tok.index("POLYGONS"); m = int(tok[i + 1]); j = i + 3; tris = []
    for _ in range(m):
        k = int(tok[j]); ids = [int(t) for t in tok[j + 1:j + 1 + k]]; j += 1 + k
        tris += [(ids[0], ids[q], ids[q + 1]) for q in range(1, k - 1)]
    return pts, np.array(tris)


fig, ax = plt.subplots(figsize=(13, 8.2), dpi=110)
for reg, (col, _) in PART.items():
    f = os.path.join(src, f"{reg}_x.vtk")
    if not os.path.exists(f):
        continue
    p, t = read_vtk(f); X, Y = -p[:, 2] * 1000, p[:, 1] * 1000
    ax.add_collection(PolyCollection(np.stack([np.column_stack([X[k], Y[k]]) for k in t.T], axis=1), facecolors=col, edgecolors=col, lw=0.2))
ax.set_aspect("equal"); ax.set_xlim(-210, 230); ax.set_ylim(-125, 125); ax.axis("off")
q = LP["continuous"]["Q"]
NOTE = dict(fontsize=8.6, va="center", bbox=dict(fc="white", ec="#888", lw=0.6, boxstyle="round,pad=0.3"))
ARW = dict(arrowstyle="-|>", color="#c2185b", lw=1.1)
notes = [  # (text, text xy, arrow target xy)
    ("OUTER SKIN (housing, fins, end shields, shaft)\nconvection: per-face CFD h, 0–22 W/m²K (mean 4.0)\n+ radiation ε = 0.7 to 40 °C surroundings",
     (-205, 112), (-30, 98)),
    ("WINDING: copper loss, uniform per volume,\nq = q₁₀₀·(1 + 0.00393·(T − 100 °C)) each cell",
     (120, 112), (39, 63)),
    ("BOBBIN WALL (winding → tooth):\n1.7 mm layer, k = 0.30 W/m·K (176 W/m²K)", (120, 72), (33, 60)),
    ("STATOR: iron loss, uniform per volume\n(91 % of the iron loss)", (120, 32), (0, 64)),
    ("SHRINK FIT (stator → housing):\n0.02 mm layer, k = 0.026 W/m·K (1300 W/m²K)", (-205, 66), (-15, 80.5)),
    ("AIR GAP 0.5 mm (rotor ↔ stator):\nlayer k_eff 0.030–0.070 W/m·K (Taylor–Couette)", (120, -8), (5, 53.5)),
    ("ROTOR: iron loss (9 %), magnets glued\n(0.1 mm, 0.20 W/m·K = 2000 W/m²K)", (120, -48), (10, 30)),
    ("END-SPACE AIR: solid with k_eff 0.47–1.18 W/m·K\n(h = 15 + 6.75·v⁰·⁶⁵); internal CFD checks this", (-205, 20), (-58, 38)),
    ("BEARINGS: friction 0.004·n W,\nsteel rings k = 15 W/m·K", (-205, -30), (-46, -21)),
    ("WINDAGE 2.2e-7·n² W into the end-space air;\ncavity cut faces (gland holes, shaft bore): adiabatic", (-205, -80), (-58, -62)),
    ("INITIAL: every region 40 °C at t = 0;\nambient 40 °C throughout", (120, -95), (60, -95)),
]
for text, xy, tgt in notes:
    ax.annotate(text, xy=tgt, xytext=xy, arrowprops=ARW, **NOTE)
handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for c, _ in PART.values()]
ax.legend(handles, [n for _, n in PART.values()], loc="lower center", ncol=4, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, -0.06))
ax.set_title("Boundary conditions, sources and contacts of the thermal model (axial section x = 0; rear left, drive end right)",
             loc="left", fontweight="bold", fontsize=12)
fig.savefig(out, bbox_inches="tight"); print("wrote", out)
