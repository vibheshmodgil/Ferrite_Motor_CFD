"""Animated heat budget per component ("who heats whom"): own loss vs net heat received from the neighbours.

    .venv/Scripts/python -I scripts/animate_budget.py <case> <lp> <out.mp4> "<title>" [seconds]

Uses heat_budget.budget() at every saved heatflow time up to the moment the winding maximum reaches 180 C (report rule),
blended linearly from t = 0 (uniform 40 C: no interface flow, all own loss is stored).
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import imageio.v2 as imageio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I drops the script dir
from heat_budget import budget, hf_times, RES, K

case, lp, out, title = sys.argv[1:5]
SECONDS = float(sys.argv[5]) if len(sys.argv) > 5 else 10
FPS, T_STOP = 20, 180.0
ORDER = ["winding", "copper", "resin", "bobbin", "stator", "housing", "rotor", "magnets", "shaft", "bearings", "inair"]
NAME = {"winding": "Winding", "copper": "Copper", "resin": "Resin", "bobbin": "Bobbin", "stator": "Stator", "housing": "Housing",
        "rotor": "Rotor iron", "magnets": "Magnets", "shaft": "Shaft", "bearings": "Bearings", "inair": "Internal air"}


def wmax_cut():
    d = os.path.join(RES, case, "postProcessing", "winding", "T_winding")
    a = np.vstack([np.loadtxt(os.path.join(d, s, "volFieldValue.dat"), comments="#", ndmin=2) for s in sorted(os.listdir(d), key=float)])
    t, T = a[:, 0], a[:, 1] - K
    i = int(np.argmax(T >= T_STOP))
    return None if T[i] < T_STOP else t[i - 1] + (T_STOP - T[i - 1]) * (t[i] - t[i - 1]) / (T[i] - T[i - 1])


cut = wmax_cut()
times = [t for t in hf_times(case) if cut is None or t <= cut]
B = [budget(case, lp, t) for t in times]
regs = [r for r in ORDER if r in B[-1]]
own = np.array([[b[r]["own"] for r in regs] for b in B])
rec = np.array([[b[r]["received"] for r in regs] for b in B])
amb = np.array([[b[r]["ambient"] for r in regs] for b in B])
# t = 0: uniform temperature, no flows; own loss at the first saved value (copper changes slowly with T)
tt = np.r_[0.0, times]
own, rec, amb = np.vstack([own[:1], own]), np.vstack([np.zeros(len(regs)), rec]), np.vstack([np.zeros(len(regs)), amb])
tend = float(tt[-1])
lim = max(np.abs(own).max(), np.abs(rec).max()) * 1.15
unit, sc = ("min", 60.0) if tend > 900 else ("s", 1.0)

fig = plt.figure(figsize=(10, 6.2), dpi=80)
fig.text(0.02, 0.955, title, fontsize=13, fontweight="bold")
fig.text(0.02, 0.915, "orange: own loss · blue: heat received from neighbours · purple: heat passed on to neighbours · "
                      "black tick: stored (warming the part)", fontsize=9, color="#555")
ax = fig.add_axes([0.16, 0.1, 0.8, 0.76])
y = np.arange(len(regs))
b_own = ax.barh(y - 0.2, own[0], height=0.36, color="#ef8a3c")
b_rec = ax.barh(y + 0.2, rec[0], height=0.36, color="#3a78c2")
ticks = ax.scatter(own[0] + rec[0] + amb[0], y, marker="|", s=420, color="k", zorder=5)
lab = [ax.text(0, yy, "", va="center", fontsize=8.5) for yy in y]
ax.set_yticks(y, [NAME[r] for r in regs]); ax.invert_yaxis(); ax.axvline(0, color="#444", lw=0.8)
ax.set_xlim(-lim, lim); ax.set_xlabel("W"); ax.grid(axis="x", alpha=0.3)
clock = fig.text(0.78, 0.955, "", fontsize=13, fontweight="bold", color="#c2185b")

nf = int(SECONDS * FPS)
wr = imageio.get_writer(out, fps=FPS, codec="libx264", quality=5, pixelformat="yuv420p", macro_block_size=1)  # streamed: low RAM
for f in range(nf):
    t = tend * f / (nf - 1)
    i = min(np.searchsorted(tt, t, side="right") - 1, len(tt) - 2); w = (t - tt[i]) / (tt[i + 1] - tt[i])
    o, r, a = ((1 - w) * x[i] + w * x[i + 1] for x in (own, rec, amb))
    for k in range(len(regs)):
        b_own[k].set_width(o[k]); b_rec[k].set_width(r[k]); b_rec[k].set_color("#3a78c2" if r[k] >= 0 else "#8e44ad")
        lab[k].set_position((lim * 0.55, y[k])); lab[k].set_text(f"own {o[k]:.0f} · {'gets' if r[k] >= 0 else 'gives'} {abs(r[k]):.0f} · stores {o[k]+r[k]+a[k]:.0f} W")
    ticks.set_offsets(np.c_[o + r + a, y])
    clock.set_text(f"t = {t/sc:.1f} {unit}" if unit != "s" else f"t = {t:.0f} s")
    fig.canvas.draw(); fr = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    wr.append_data(np.ascontiguousarray(fr[: fr.shape[0] // 2 * 2, : fr.shape[1] // 2 * 2]))
plt.close(fig); wr.close()
print("wrote", out, nf, "frames, saved times", times)
