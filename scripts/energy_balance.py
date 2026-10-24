"""Global energy balance of a finished run: generation = outflow + storage, integrated over the whole run.

    .venv/Scripts/python -I scripts/energy_balance.py <lp>   -> results/<lp>/energy_balance.json
    .venv/Scripts/python -I scripts/energy_balance.py <results subdir> <lp>   (a rerun under another name)
Generation from the loss map (the winding Joule term is linear in T, so the volume-average history is exact),
outflow from the Qout_* wallHeatFlux monitors, storage from energy_T.txt (energy_check.sh at 0 and the last time).
Both histories are summed the implicit-Euler way: value at the end of each step x dt.
"""
import glob, json, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
lp = sys.argv[-1]
R = os.path.join(ROOT, "results", sys.argv[1])
P = os.path.join(R, "postProcessing")
Q = json.load(open(os.path.join(ROOT, "loadpoints.json")))[lp]["Q"]
RC = {"housing": 2680 * 900, "stator": 7650 * 460, "rotor": 7650 * 460, "magnets": 4900 * 800, "shaft": 7850 * 460,
      "bearings": 7850 * 460, "inair": 10 * 718, "winding": 0.51 * 8933 * 385 + 0.49 * 1200 * 1500,  # = energy_sum.py
      "copper": 8933 * 385, "bobbin": 1350 * 1500, "resin": 1200 * 1500}                               # detailed model
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))[lp]
DETAILED = os.path.isdir(os.path.join(P, "copper"))
# detailed (MERGE_CU) copper part zones in ~/cfd/base_detailed, m3 (volIntegrate select=cellZone, at uniform T)
V_ZONE = {"strap": 2.12897e-06, "tbar": 3.19863e-06}
P20 = {"busbar": LP.get("busbar_20C", 0)} | {z: 1.72e-8 * LP.get(f"J_{z}", 0) ** 2 * V_ZONE[z] for z in V_ZONE}


def dat(path):     # ponytail: single-start run (one time folder); stitch like post.py if runs get continued
    f = glob.glob(os.path.join(P, path, "0", "*.dat"))[0]
    return np.loadtxt(f, comments="#", dtype=str)


E_st, t2 = 0.0, None
for l in open(os.path.join(R, "energy_T.txt")):
    p = l.split()
    if len(p) == 5 and p[0] in RC:
        E_st += RC[p[0]] * (float(p[4]) - float(p[2]))
        t2 = float(p[3])                         # histories are cut at the storage time


def hist(path, col):
    a = dat(path)
    a = a[a[:, 0].astype(float) <= t2 + 1e-6]
    return a[:, 0].astype(float), a[:, col].astype(float)


tt, Tw = hist("copper/Tavg_coil" if DETAILED else "winding/Tavg_winding", 1)
dt, Tw = np.diff(tt), Tw[1:]
const = sum(v for k, v in Q.items() if k != "winding_100C")
gen = Q["winding_100C"] * (1 + 0.00393 * (Tw - 373.15)) + const
if DETAILED:   # small Cu parts: only their max T is logged, so bound their T between ambient and that max
    lo, hi = gen.copy(), gen.copy()
    for z, p20 in P20.items():
        Tz = hist(f"copper/T_{z}", 1)[1][1:]
        lo += p20 * (1 + 0.00393 * (313.15 - 293.15))
        hi += p20 * (1 + 0.00393 * (Tz - 293.15))
    gen = (lo + hi) / 2
out = 0
for r in ("housing", "shaft"):
    tq, q = hist(f"{r}/Qout_{r}", 4)
    assert np.allclose(tq, tt), r
    out = out - q[1:]                            # wallHeatFlux: positive into the region
E_gen, E_out = float(np.sum(gen * dt)), float(np.sum(out * dt))
t = tt
res = dict(t_end_s=float(t[-1]), generation_kJ=E_gen / 1e3,
           **(dict(gen_bound_kJ=float(np.sum((hi - lo) / 2 * dt)) / 1e3) if DETAILED else {}), outflow_kJ=E_out / 1e3, storage_kJ=E_st / 1e3,
           error_pct=100 * (E_out + E_st - E_gen) / E_gen, gen_end_W=float(gen[-1]), outflow_end_W=float(out[-1]))
json.dump(res, open(os.path.join(R, "energy_balance.json"), "w"), indent=1)
print(lp, json.dumps(res))
