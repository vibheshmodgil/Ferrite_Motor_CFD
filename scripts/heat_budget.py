"""Who heats whom: per-region heat budget at a saved time, from the OpenFOAM interface heat flows.

    .venv/Scripts/python -I scripts/heat_budget.py              # self-check on the results present

For region r at time t (results/<case>/heatflow_<t>.txt, + = into the region):
    received = sum of r's interface flows        (+ = heated by neighbours, - = passes heat on to them)
    ambient  = r's outer-skin flow (defaultFaces) (- = to the surroundings)
    own      = r's own loss from loadpoints.json  (copper: DC scaled with the winding mean T, plus AC; detailed copper
               also the busbar plates; the strap / t-bar J^2 sources, a few W, are not included)
    stored   = own + received + ambient           (= rho c V dT/dt of the region)
"""
import glob, json, os
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES, K, TC = os.path.join(ROOT, "results"), 273.15, 0.00393
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))


def read_hf(case, t):
    try:
        return {(r, p): float(q) for r, p, q in (l.split() for l in open(os.path.join(RES, case, f"heatflow_{t}.txt")) if l.strip())}
    except (OSError, ValueError):
        return None


def hf_times(case):
    return sorted(int(f.rsplit("_", 1)[1][:-4]) for f in glob.glob(os.path.join(RES, case, "heatflow_*.txt")))


def tavg(case, region, fn, t):
    d = os.path.join(RES, case, "postProcessing", region, fn)
    try:
        segs = [np.loadtxt(os.path.join(d, s, "volFieldValue.dat"), comments="#", ndmin=2) for s in sorted(os.listdir(d), key=float)]
        a = np.vstack([s for s in segs if s.size])
    except (OSError, ValueError):
        return None
    return float(np.interp(t, a[:, 0], a[:, 1])) - K


def budget(case, lp, t):
    """{region: {own, received, ambient, stored}} in W at saved time t, or None without a heatflow file."""
    hf = read_hf(case, t)
    if not hf:
        return None
    Q = LP[lp]["Q"]
    # regions whose wallHeatFlux is missing (stator, rotor in these runs) take the mirror of their neighbours' "<nb>_to_<r>" flows
    have = {r for r, _ in hf}
    for (r, p), q in list(hf.items()):
        nb = p.split("_to_", 1)[1] if "_to_" in p else None
        if nb and nb not in have:
            hf[(nb, f"{nb}_to_{r}")] = -q
    regs = sorted({r for r, _ in hf})
    det = "copper" in regs
    w = "copper" if det else "winding"
    Tw = tavg(case, w, "Tavg_coil" if det else "Tavg_winding", t)
    Tw = 100.0 if Tw is None else Tw
    own = {w: Q["winding_100C"] * (1 + TC * (Tw - 100)) + Q.get("winding_ac", 0)
              + (LP[lp].get("busbar_20C", 0) * (1 + TC * (Tw - 20)) if det else 0),
           "stator": Q.get("stator", 0), "rotor": Q.get("rotor", 0), "bearings": Q.get("bearings", 0), "inair": Q.get("inair", 0)}
    out = {}
    for r in regs:
        rec = sum(q for (rr, p), q in hf.items() if rr == r and p != "defaultFaces")
        amb = hf.get((r, "defaultFaces"), 0.0)
        o = own.get(r, 0.0)
        out[r] = dict(own=o, received=rec, ambient=amb, stored=o + rec + amb)
    return out


if __name__ == "__main__":
    for case, lp in (("duty1", "duty1"), ("detailed/duty1", "duty1"), ("duty4", "duty4"), ("detailed/duty4", "duty4")):
        for t in hf_times(case)[-1:]:
            b = budget(case, lp, t)
            # interface flows are internal: summed over all regions they cancel (each face counted from both sides)
            tot_rec = sum(v["received"] for v in b.values())
            assert abs(tot_rec) < 0.03 * sum(v["own"] for v in b.values()), (case, t, tot_rec)
            print(case, t, f"sum received {tot_rec:+.1f} W (should be ~0)")
            for r, v in b.items():
                print(f"  {r:9s} own {v['own']:7.1f}  received {v['received']:+8.1f}  ambient {v['ambient']:+8.1f}  stored {v['stored']:7.1f}")
