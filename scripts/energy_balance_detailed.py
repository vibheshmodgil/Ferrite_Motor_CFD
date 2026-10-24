"""Global energy balance of a detailed run (results/detailed/<lp>): generation vs outflow + storage.
    .venv/Scripts/python -I scripts/energy_balance_detailed.py <lp>  -> results/detailed/<lp>/energy_balance.json
Coil Joule from Tavg_coil (exact: linear in T). busbar/strap/tbar only have T max monitors, so their Joule heat is
bracketed between the 20 C value (low) and T_max (high) -> an error range."""
import glob, json, os, sys
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); lp = sys.argv[1]
R = os.path.join(ROOT, "results", "detailed", lp); P = os.path.join(R, "postProcessing")
L = json.load(open(os.path.join(ROOT, "loadpoints.json")))[lp]; Q = L["Q"]
reg = json.load(open(os.path.join(ROOT, "mesh", "motor_detailed_regions.json")))
RC = {"housing": 2680 * 900, "stator": 7650 * 460, "rotor": 7650 * 460, "magnets": 4900 * 800, "shaft": 7850 * 460,
      "bearings": 7850 * 460, "inair": 10 * 718, "bobbin": 1350 * 1500, "resin": 1200 * 1500, "copper": 8933 * 385}
E_st = 0.0
for l in open(os.path.join(R, "energy_T.txt")):
    p = l.split()
    if len(p) == 5 and p[0] in RC:
        E_st += RC[p[0]] * (float(p[4]) - float(p[2])); t2 = float(p[3])
def hist(path, col=1):
    a = np.loadtxt(glob.glob(os.path.join(P, path, "0", "*.dat"))[0], comments="#", usecols=(0, col))
    a = a[a[:, 0] <= t2 + 1e-6]; return a[:, 0], a[:, 1]
tt, Tc = hist("copper/Tavg_coil"); dt = np.diff(tt)
gen = Q["winding_100C"] * (1 + 0.00393 * (Tc[1:] - 373.15)) + sum(v for k, v in Q.items() if k != "winding_100C")
q20 = {"busbar": L["busbar_20C"], "strap": 1.72e-8 * L["J_strap"] ** 2 * reg["strap"],
       "tbar": 1.72e-8 * L["J_tbar"] ** 2 * reg["tbar"]}
lo = hi = 0.0
for z, q in q20.items():
    Tm = hist(f"copper/T_{z}")[1]
    lo += np.sum(q * dt); hi += np.sum(q * (1 + 0.00393 * (Tm[1:] - 293.15)) * dt)
out = 0
for r in ("housing", "shaft"):
    tq, q = hist(f"{r}/Qout_{r}", 4); assert np.allclose(tq, tt); out = out - q[1:]
E_gen, E_out = float(np.sum(gen * dt)), float(np.sum(out * dt))
res = {"t_end_s": float(tt[-1]), "storage_kJ": E_st / 1e3, "outflow_kJ": E_out / 1e3,
       "generation_kJ_range": [(E_gen + lo) / 1e3, (E_gen + hi) / 1e3],
       "error_pct_range": [100 * (E_out + E_st - E_gen - hi) / (E_gen + hi), 100 * (E_out + E_st - E_gen - lo) / (E_gen + lo)]}
json.dump(res, open(os.path.join(R, "energy_balance.json"), "w"), indent=1); print(lp, json.dumps(res))
