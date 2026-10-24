"""Global energy balance of a finished U666 run: generation = outflow + storage (implicit-Euler sums).

    python3 u666_energy_balance.py <case_dir> <lp> <loadpoints.json>    (WSL, stdlib) -> <case>/energy_balance.json
Storage from the volIntegrate(T) monitors (per region, per cellZone where rho cv is zonal) against the uniform start
temperature; generation from the loss map (winding DC linear in T: zone volume averages make it exact); outflow from
the Qout_* wallHeatFlux monitors.
"""
import glob, json, os, sys

case = sys.argv[1]
P = json.load(open(os.path.join(case, "case_props.json")))
pp = os.path.join(case, "postProcessing")


def dat(region, name, col=1):
    f = sorted(glob.glob(os.path.join(pp, region, name, "*", "*.dat")))
    rows = {}
    for fn in f:     # continued runs: later folders overwrite
        for l in open(fn):
            if l.startswith("#") or not l.strip():
                continue
            p = l.split()
            rows[float(p[0])] = float(p[col])
    return sorted(rows.items())


T0, E_st, V = P["T0"], 0.0, {}
for r, rc in P["rhocv"].items():
    for z, rcz in (rc.items() if isinstance(rc, dict) else [(None, rc)]):
        key, pre = (z, "z") if z else (r, "")
        Ti, Ta = dat(r, f"Tint{pre}_{key}"), dat(r, f"Tavg{pre}_{key}")
        V[key] = Ti[0][1] / Ta[0][1]
        E_st += rcz * (Ti[-1][1] - T0 * V[key])
t_end = Ti[-1][0]
Q = P["Q"]
const = sum(v for k, v in Q.items() if k not in ("winding_dc",))
fV = sum(P["fill"][z] * V[z] for z in P["fill"])
hz = {z: dict(dat("winding", f"Tavgz_{z}")) for z in P["fill"]}
out = {r: dict(dat(r, f"Qout_{r}", 4)) for r in P["skin"]} if not os.environ.get("ADIAB") else {}
E_gen = E_out = 0.0
tp = 0.0
for t in sorted(hz[next(iter(hz))]):
    if t > t_end + 1e-9:
        break
    dt, tp = t - tp, t
    dc = Q.get("winding_dc", 0) * sum(P["fill"][z] * V[z] / fV * (1 + P["tc"] * (hz[z][t] - P["T_ref"])) for z in hz)
    E_gen += (dc + const) * dt
    E_out += sum(-o.get(t, 0.0) for o in out.values()) * dt     # wallHeatFlux: positive into the region
res = dict(t_end_s=t_end, generation_kJ=E_gen / 1e3, outflow_kJ=E_out / 1e3, storage_kJ=E_st / 1e3,
           error_pct=100 * (E_out + E_st - E_gen) / E_gen, volumes_cm3={k: v * 1e6 for k, v in V.items()})
# time series per region (BASE2): stored(t) vs injected(t) = Q_region t (constant losses, JOULE_TC=0 / ADIAB run)
RQ = {"winding_dc": "winding", "winding_ac": "winding", "bearing_f": "bearings", "bearing_r": "bearings"}
Qr = {}
for k, v in Q.items():
    Qr[RQ.get(k, k)] = Qr.get(RQ.get(k, k), 0.0) + v
rows = []
for r, rc in P["rhocv"].items():
    ser = {}
    for z, rcz in (rc.items() if isinstance(rc, dict) else [(None, rc)]):
        key, pre = (z, "z") if z else (r, "")
        for t, ti in dat(r, f"Tint{pre}_{key}"):
            ser[t] = ser.get(t, 0.0) + rcz * (ti - T0 * V[key])
    rows += [(t, r, e, Qr.get(r, 0.0) * t) for t, e in sorted(ser.items())]
with open(os.path.join(case, "energy_ts.csv"), "w") as f:
    f.write("t_s,region,stored_J,injected_J\n" + "".join("%g,%s,%.6g,%.6g\n" % x for x in rows))
# interface pairs: Q(a_to_b) + Q(b_to_a) at the last time (wallHeatFlux, positive into each region)
qi = {}
for fn in glob.glob(os.path.join(pp, "*", "Qif_*", "*", "*.dat")):
    for l in open(fn):
        p = l.split()
        if p and not l.startswith("#"):
            qi[p[1]] = (float(p[0]), float(p[4]))
pairs = {}
for n, (t, q) in qi.items():
    a, b = n.split("_to_")
    pairs.setdefault(tuple(sorted((a, b))), {})[n] = q
res["iface_W"] = {"%s|%s" % k: dict(v, sum=sum(v.values())) for k, v in sorted(pairs.items())}
json.dump(res, open(os.path.join(case, "energy_balance.json"), "w"), indent=1)
print(json.dumps(res))
