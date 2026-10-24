"""Plot (stored - injected) vs time per region + total from energy_ts.csv:  python u666_plot_balance.py ts.csv out.png"""
import csv, sys
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = defaultdict(dict)
for r in csv.DictReader(open(sys.argv[1])):
    d[r["region"]][float(r["t_s"])] = float(r["stored_J"]) - float(r["injected_J"])
ts = sorted({t for v in d.values() for t in v})
tot = [sum(v.get(t, 0) for v in d.values()) for t in ts]
inj = defaultdict(float)
for r in csv.DictReader(open(sys.argv[1])):
    inj[float(r["t_s"])] += float(r["injected_J"])
fig, ax = plt.subplots(figsize=(8, 5))
for n in sorted(d, key=lambda n: -abs(d[n][ts[-1]])):
    ax.plot(ts, [d[n].get(t, 0) / 1e3 for t in ts], lw=1.2, label=n)
ax.plot(ts, [x / 1e3 for x in tot], "k", lw=2.2, label="total (%.2f %% at %g s)" % (100 * tot[-1] / inj[ts[-1]], ts[-1]))
ax.axhline(0, color="0.6", lw=0.8)
ax.set_xlabel("simulated time [s]"); ax.set_ylabel("stored - injected [kJ]")
ax.set_title(sys.argv[3] if len(sys.argv) > 3 else "U666 adiabatic energy test")
ax.legend(fontsize=8, ncol=2); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=130)
print("total %.3f %%" % (100 * tot[-1] / inj[ts[-1]]))
