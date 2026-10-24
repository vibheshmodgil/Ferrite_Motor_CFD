# per-region check of ~/cfd/u666_e2: stored, injected, and region rate balance at the end (dE/dt vs Q + sum iface)
import csv, json, os, collections
C = os.path.expanduser("~/cfd/u666_e2")
d = json.load(open(C + "/energy_balance.json"))
ts = collections.defaultdict(dict)
for r in csv.DictReader(open(C + "/energy_ts.csv")):
    ts[r["region"]][float(r["t_s"])] = (float(r["stored_J"]), float(r["injected_J"]))
qin = collections.defaultdict(float)
for k, v in d["iface_W"].items():
    for n, q in v.items():
        if n != "sum":
            qin[n.split("_to_")[0]] += q
for r, s in sorted(ts.items()):
    t = sorted(s); t1, t0 = t[-1], t[-2]
    dEdt = (s[t1][0] - s[t0][0]) / (t1 - t0)
    Q = s[t1][1] / t1
    print("%-9s stored %8.0f J inj %8.0f J | dE/dt %7.1f  Q %7.1f  iface %7.1f  resid %6.1f W" % (r, s[t1][0], s[t1][1], dEdt, Q, qin[r], dEdt - Q - qin[r]))
