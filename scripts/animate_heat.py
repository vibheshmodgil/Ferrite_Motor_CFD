"""Heat-transfer animation: the heat-path network through time (arrow width = watts) + running energy balance.

    .venv/Scripts/python -I scripts/animate_heat.py <result_case> <loadpoint> <out.mp4> "<title>" [seconds]

Uses results/<case>/heatflow_<t>.txt (source-side interface flows at every saved time) and the winding average
temperature for the copper loss at that moment; frames blend linearly between saved times.
"""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import imageio.v2 as imageio

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
case, lp, out, title = sys.argv[1:5]
SECONDS = float(sys.argv[5]) if len(sys.argv) > 5 else 12
FPS, K = 20, 273.15
R = os.path.join(ROOT, "results", case)
Q = json.load(open(os.path.join(ROOT, "loadpoints.json")))[lp]["Q"]


def hist(region, kind):
    d = os.path.join(R, "postProcessing", region, f"{kind}_{region}")
    a = np.vstack([np.atleast_2d(np.loadtxt(os.path.join(d, t, "volFieldValue.dat"), comments="#"))
                   for t in sorted(os.listdir(d), key=float)])
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    return a[:, 0], a[:, 1] - K


EDGES = [("w", "st", lambda h: -h[("winding", "winding_to_stator")]),
         ("w", "air", lambda h: -h[("winding", "winding_to_inair")]),
         ("air", "st", lambda h: -h[("inair", "inair_to_stator")]),
         ("air", "rot", lambda h: -h[("inair", "inair_to_rotor")]),
         ("air", "hous", lambda h: -h[("inair", "inair_to_housing")]),
         ("st", "hous", lambda h: h[("housing", "housing_to_stator")]),
         ("hous", "amb", lambda h: -h.get(("housing", "defaultFaces"), 0) - h.get(("shaft", "defaultFaces"), 0))]
times, flows = [0.0], [np.zeros(len(EDGES))]
for f in sorted(glob.glob(os.path.join(R, "heatflow_*.txt")), key=lambda p: float(p.rsplit("_", 1)[1][:-4])):
    h = {}
    for line in open(f):
        r, p, q = line.split(); h[(r, p)] = float(q)
    try:
        flows.append(np.array([fn(h) for _, _, fn in EDGES])); times.append(float(f.rsplit("_", 1)[1][:-4]))
    except KeyError:
        pass
times, flows = np.array(times), np.array(flows)
wt, wTa = hist("winding", "Tavg")
ht, hT = hist("winding", "T")
# report rule: the timeline ends when the winding hot spot reaches T_STOP (or at the last saved heat flow)
T_STOP = 180.0
i = int(np.argmax(hT >= T_STOP))
tend = times[-1] if hT[i] < T_STOP else (ht[0] if i == 0 else ht[i - 1] + (T_STOP - hT[i - 1]) * (ht[i] - ht[i - 1]) / (hT[i] - hT[i - 1]))
tend = min(tend, times[-1])
n = int(np.searchsorted(times, tend)) + 1          # keep the first saved time at/after tend for blending
times, flows = times[:n], flows[:n]
other = sum(v for k, v in Q.items() if k != "winding_100C" and isinstance(v, (int, float)))   # incl. winding_ac (fixed W)
gen_t = lambda t: Q["winding_100C"] * (1 + 0.00393 * (np.interp(t, wt, wTa) - 100)) + other
unit, scale = ("h", 3600.0) if tend > 3 * 3600 else ("min", 60.0) if tend > 900 else ("s", 1.0)

POS = {"w": (0.12, 0.55), "st": (0.38, 0.78), "air": (0.38, 0.32), "rot": (0.64, 0.12), "hous": (0.64, 0.62), "amb": (0.88, 0.62)}
NAME = {"w": "Winding", "st": "Stator", "air": "Internal air", "rot": "Rotor, magnets", "hous": "Housing", "amb": "Ambient air"}
SUB = {"w": "copper loss", "st": f"iron {Q['stator']:.0f} W", "air": "end spaces", "rot": f"{Q.get('rotor',0)+Q.get('bearings',0)+Q.get('inair',0):.0f} W",
       "hous": "fins, end shields", "amb": "convection + radiation"}
wmax = flows.max()

fig = plt.figure(figsize=(12, 7), dpi=85)
fig.text(0.02, 0.955, title, fontsize=14, fontweight="bold")
fig.text(0.02, 0.92, "heat flow between parts (arrow width ∝ watts, from OpenFOAM interface heat fluxes) · frames blended between saved solutions",
         fontsize=10, color="#555")
ax = fig.add_axes([0.02, 0.30, 0.96, 0.6]); ax.set_xlim(0, 1); ax.set_ylim(0, 0.92); ax.axis("off")
for k, (x, y) in POS.items():
    ax.add_patch(FancyBboxPatch((x - 0.075, y - 0.06), 0.15, 0.12, boxstyle="round,pad=0.01", fc="#f1f2f4", ec="#888", lw=1.2, zorder=3))
    ax.text(x, y + 0.015, NAME[k], ha="center", va="center", fontsize=11, fontweight="bold", zorder=4)
subtxt = {k: ax.text(POS[k][0], POS[k][1] - 0.03, SUB[k], ha="center", va="center", fontsize=9, color="#555", zorder=4) for k in POS}
arrows, labels = [], []
for a, b, _ in EDGES:
    (x1, y1), (x2, y2) = POS[a], POS[b]
    rad = 0.0 if x1 == x2 or y1 == y2 else (0.25 if y2 > y1 else -0.25)
    s, e = (x1 + (0.0 if x1 == x2 else 0.075), y1 + (0.06 if x1 == x2 and y2 > y1 else 0)), (x2 - (0.0 if x1 == x2 else 0.08), y2 - (0.06 if x1 == x2 and y2 > y1 else 0))
    ar = FancyArrowPatch(s, e, connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>", mutation_scale=18, color="#c2185b", alpha=0.55, lw=1, zorder=2)
    ax.add_patch(ar); arrows.append(ar)
    mx, my = (s[0] + e[0]) / 2, (s[1] + e[1]) / 2 + (0.05 if rad == 0 and x1 != x2 else 0)
    if x1 == x2: mx += 0.035
    labels.append(ax.text(mx, my, "", ha="center", va="center", fontsize=10.5, fontweight="bold", zorder=5,
                          bbox=dict(fc="white", ec="none", alpha=0.7, pad=1)))
axb = fig.add_axes([0.07, 0.07, 0.86, 0.17])
tg = np.linspace(0, tend, 200)
axb.plot(tg / scale, [gen_t(t) for t in tg], color="#333", lw=1.6, label="generated")
axb.plot(tg / scale, np.interp(tg, times, flows[:, -1]), color="#1f78b4", lw=1.6, label="leaving to ambient")
axb.fill_between(tg / scale, np.interp(tg, times, flows[:, -1]), [gen_t(t) for t in tg], color="#f4a261", alpha=0.35, label="stored in the motor")
axb.set_xlim(0, tend / scale); axb.set_xlabel(f"time [{unit}]"); axb.set_ylabel("W"); axb.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right")
axb.grid(alpha=0.3); marker = axb.axvline(0, color="#c2185b", lw=1.5)
clock = fig.text(0.07, 0.265, "", fontsize=12, fontweight="bold", color="#c2185b")

frames, nf = [], int(SECONDS * FPS)
for f in range(nf):
    t = tend * f / (nf - 1)
    i = min(np.searchsorted(times, t, side="right") - 1, len(times) - 2); w = (t - times[i]) / (times[i + 1] - times[i])
    q = (1 - w) * flows[i] + w * flows[i + 1]
    for ar, lab, v in zip(arrows, labels, q):
        ar.set_linewidth(0.5 + 22 * max(v, 0) / wmax); lab.set_text(f"{v:.0f} W")
    g = gen_t(t); subtxt["w"].set_text(f"copper {g - other + Q.get('winding_ac', 0):.0f} W")
    stored = g - q[-1]
    clock.set_text((f"t = {t/scale:.1f} {unit}" if unit != "s" else f"t = {t:.0f} s") + f"   stored {stored:.0f} W ({stored/g*100:.0f} %)")
    marker.set_xdata([t / scale, t / scale])
    fig.canvas.draw(); frames.append(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
plt.close(fig)
h, w_ = frames[0].shape[:2]
frames = [fr[: h - h % 2, : w_ - w_ % 2] for fr in frames]
imageio.mimwrite(out, frames, fps=FPS, codec="libx264", quality=5, pixelformat="yuv420p", macro_block_size=1)
print("wrote", out, len(frames), "frames, snapshots", len(times))
