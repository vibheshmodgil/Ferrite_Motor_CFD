"""Independent check of the FEMM loss map at the CFD load points, from loaded rotating FEMM solutions.

eff_map.py (the loss map the CFD uses) takes iron loss from the NO-LOAD field scaled by |psi|^2/psi_m^2 and copper
loss as DC. This script instead solves the actual operating point (id, iq from eff.json) at 2 deg steps over
180 deg of rotation and, from those same solutions, computes:
  stator iron   per-point Bx(t), By(t) Fourier series over one electrical period, same KH/KE/BUILD as eff_map
  rotor iron    the same in the rotor frame (B is anti-periodic over 180 deg mech, so [B, -B] is one period)
  wire eddy     proximity loss of every 2.9 mm wire from the slot field at its centre,
                P' = pi sigma w^2 B^2 d^4 / 128 per harmonic (low-frequency limit; slightly high when d > skin depth)
  delta loop    zero-sequence (3rd, 9th) EMF from the loaded flux linkages, driving a circulating current through
                R + j w L0 per phase; L0 from a zero-sequence FEMM solve (2D only, so the current is on the high side)
  battery sag   minimum-loss d-q point re-optimised at lower DC voltage (eff_map method)
Plus a no-load sweep to compare against eff_map's single-snapshot no-load iron loss.

    python scripts/loss_check.py            # Windows, FEMM 4.2 + pyfemm; ~1 h with 2 workers -> results/loss_check.json
"""
import json, math, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FEMM_DIR = os.path.abspath(os.path.join(ROOT, "..", "OUTPUT", "femm_em"))
sys.path.insert(0, FEMM_DIR)
import femm_motor as M          # noqa: E402
import dq_study as D            # noqa: E402

NWORK = 2                       # ponytail: 2 FEMM workers so the WSL CFD run keeps its cores
STEP = float(os.environ.get("STEP", 2.0))   # deg mech per solve (STEP=36 for a smoke test)
SIGMA_CU = 58e6 / (1 + 0.00393 * 80)    # S/m at 100 C
D_WIRE = M.WIRE_D * 1e-3
DENS = 7650
POINTS = {"grade12": (37.0, 1782), "flat60": (3.24, 9339)}
SP = {}                         # sample points, set in each worker by init()


def sample_points():
    """Polar grids over half the machine (it repeats every 180 deg): stator steel, rotor steel (rotor frame), wires."""
    def grid(r0, r1):
        r, a = np.meshgrid(np.arange(r0 + .25, r1, .5), np.radians(np.arange(.25, 180, .5)), indexing="ij")
        return np.column_stack([(r * np.cos(a)).ravel(), (r * np.sin(a)).ravel()]), (r * .5 * math.radians(.5)).ravel()
    st, st_a = grid(M.R_BORE, 80.0)
    ro, ro_a = grid(15.0, 53.0)
    _, cond, _, _ = M.load_stator()
    wires = np.array([M.rot((s * x, y), 30 * (t - 1) - 90) for t in range(1, 13) for s in (1, -1) for x, y in cond])
    return dict(st=st, st_a=st_a, ro=ro, ro_a=ro_a, wires=wires)


def init():
    M.worker_init()
    SP.update(sample_points())


def fields_at(th, pts_by_name):
    """Element B at each sample point from the worker's .ans; also the material there (3 = steel)."""
    import matplotlib.tri as mtri
    from field_maps import read_ans, element_fields
    nodes, el, labs = read_ans(M.W["file"] + ".ans")
    _, _, mat, Bx, By, _ = element_fields(nodes, el, labs, full=True)
    tf = mtri.Triangulation(nodes[:, 0], nodes[:, 1], el[:, :3]).get_trifinder()
    out = {}
    for name, p in pts_by_name.items():
        k = tf(p[:, 0], p[:, 1])
        ok = k >= 0
        k = np.where(ok, k, 0)
        out[name] = (np.where(ok, Bx[k], 0).astype(np.float32), np.where(ok, By[k], 0).astype(np.float32),
                     np.where(ok, mat[k], 0).astype(np.int8))
    return out


def job(j):
    th, cur = j
    T, psi = M.solve(th, cur)
    a = math.radians(th); c, s = math.cos(a), math.sin(a)
    ro = SP["ro"] @ np.array([[c, s], [-s, c]])                      # rotor-frame points -> stator frame at th
    f = fields_at(th, dict(st=SP["st"], ro=ro, wires=SP["wires"]))
    # rotor B back into the rotor frame
    bx, by, m = f["ro"]
    f["ro"] = (bx * c + by * s, -bx * s + by * c, m)
    return T, psi, f


def harm_loss(Bx, By, f0, kh, ke):
    """Iron loss density [W/kg] per sample point: sum over harmonics of (KH f + KE f^2) (Bx_k^2 + By_k^2)."""
    n = Bx.shape[0]
    X, Y = np.fft.rfft(Bx, axis=0) * 2 / n, np.fft.rfft(By, axis=0) * 2 / n
    X[0] = Y[0] = 0                                                  # DC flux: no loss
    f = np.arange(X.shape[0])[:, None] * f0
    return ((kh * f + ke * f * f) * (abs(X) ** 2 + abs(Y) ** 2)).sum(0)


def wire_loss(Bx, By, f0):
    """Proximity loss [W] per wire over the 65 mm active length."""
    n = Bx.shape[0]
    X, Y = np.fft.rfft(Bx, axis=0) * 2 / n, np.fft.rfft(By, axis=0) * 2 / n
    X[0] = Y[0] = 0
    w = 2 * math.pi * np.arange(X.shape[0])[:, None] * f0
    return (math.pi * SIGMA_CU * w * w * (abs(X) ** 2 + abs(Y) ** 2) * D_WIRE ** 4 / 128).sum(0) * M.STACK * 1e-3


def interp(E, key, T, n):
    a, ts, ns = np.array(E[key], dtype=float), E["torques"], E["speeds"]
    i = min(max(np.searchsorted(ts, T) - 1, 0), len(ts) - 2); j = min(max(np.searchsorted(ns, n) - 1, 0), len(ns) - 2)
    u, v = (T - ts[i]) / (ts[i + 1] - ts[i]), (n - ns[j]) / (ns[j + 1] - ns[j])
    w = {(0, 0): (1 - u) * (1 - v), (1, 0): u * (1 - v), (0, 1): (1 - u) * v, (1, 1): u * v}
    return sum(wk * a[i + di, j + dj] for (di, dj), wk in w.items() if wk > 1e-12)


def min_loss_point(T, n, vdc):
    """eff_map's minimum-loss d-q choice at one (T, n), with the DC voltage changed. None = not reachable."""
    from scipy.interpolate import RegularGridInterpolator
    E = json.load(open(os.path.join(FEMM_DIR, "eff.json"))); m = json.load(open(os.path.join(FEMM_DIR, "dq.json")))
    md = E["model"]
    g = (np.array(m["id"]), np.array(m["iq"]))
    fd, fq, fT = (RegularGridInterpolator(g, np.array(m[k]), method="cubic") for k in ("psid", "psiq", "T"))
    psim = float(fd([[0, 0]])[0])
    i_d, i_q = np.meshgrid(np.linspace(-D.I_PEAK, 0, 301), np.linspace(0, D.I_PEAK, 301), indexing="ij")
    ok = np.hypot(i_d, i_q) <= D.I_PEAK
    P = np.column_stack([i_d[ok], i_q[ok]])
    psd, psq, Tq = fd(P), fq(P), fT(P)
    w = n * 2 * math.pi / 60 * M.P; f = w / 2 / math.pi
    v = np.hypot(D.R_PATH * P[:, 0] - w * psq, D.R_PATH * P[:, 1] + w * psd)
    pcu = 3 * D.R_PATH * (P[:, 0] ** 2 + P[:, 1] ** 2)
    pfe = (md["KH"] * f + md["KE"] * f * f) * md["stator_B2m_noload"] * (psd ** 2 + psq ** 2) / psim ** 2 \
        * md["BUILD"] * (1 + md["ROTOR_FE"])
    pme = md["MECH_A"] * n + md["MECH_B"] * n * n
    tsh = (Tq * n * 2 * math.pi / 60 - pme) / (n * 2 * math.pi / 60)
    c = np.flatnonzero((v <= 0.95 * vdc) & (abs(tsh - T) <= 0.1))
    if not len(c):
        return None
    k = c[np.argmin((pcu + pfe)[c])]
    return dict(vdc=vdc, id=float(P[k, 0]), iq=float(P[k, 1]), I_line_rms=float(np.hypot(*P[k]) * math.sqrt(6)),
                pcu=float(pcu[k]), pfe=float(pfe[k]))


def main():
    from multiprocessing import Pool
    E = json.load(open(os.path.join(FEMM_DIR, "eff.json"))); md = E["model"]
    r = json.load(open(os.path.join(FEMM_DIR, "results.json")))
    phi = r["noload"]["phi"]
    ths = np.arange(0, 180 + 1e-9, STEP)                             # 0..180 inclusive: last one checks anti-periodicity
    ops = {k: (interp(E, "id", T, n), interp(E, "iq", T, n)) for k, (T, n) in POINTS.items()}
    jobs = [(float(t), D.currents(t, phi, *ops[k])) for k in POINTS for t in ths]
    jobs += [(float(t), M.ZERO) for t in np.arange(0, 72, STEP)]     # no-load, one electrical period
    I0 = 10.0
    jobs += [(0.0, dict(R=I0, Y=I0, B=I0))]                          # zero sequence -> L0
    import pickle
    ck = os.path.join(ROOT, "results", "loss_check_solves_%g.pkl" % STEP)   # raw solves: reruns only redo the maths
    if os.path.exists(ck):
        out = pickle.load(open(ck, "rb"))
    else:
        with Pool(NWORK, initializer=init) as pool:
            out = pool.map(job, jobs, chunksize=1)
        pickle.dump(out, open(ck, "wb"))
    SPm = sample_points()
    nt = len(ths); res = {}
    nnl = len(np.arange(0, 72, STEP))
    noload = out[2 * nt:2 * nt + nnl]; zs = out[-1]
    psi0_nl = np.mean([noload[0][1][p] for p in "RYB"])
    L0_path = (np.mean([zs[1][p] for p in "RYB"]) - psi0_nl) / I0
    steel_st = noload[0][2]["st"][2] == 3
    steel_ro = noload[0][2]["ro"][2] == 3
    m_st = SPm["st_a"] * 1e-6 * M.STACK * 1e-3 * M.STACKING * DENS
    m_ro = SPm["ro_a"] * 1e-6 * M.STACK * 1e-3 * M.STACKING * DENS
    kh, ke, build = md["KH"], md["KE"], md["BUILD"]

    def stator_fe(sol, f_e):
        per = sol[:int(round(72 / STEP))]                            # one electrical period
        Bx = np.array([s[2]["st"][0] for s in per]); By = np.array([s[2]["st"][1] for s in per])
        return 2 * float((harm_loss(Bx, By, f_e, kh, ke) * m_st)[steel_st].sum()) * build

    for i, (k, (T, n)) in enumerate(POINTS.items()):
        sol = out[i * nt:(i + 1) * nt]
        f_e = n / 60 * M.P
        pst = stator_fe(sol, f_e)
        # rotor: anti-periodic over 180 deg -> period 360 deg = [B, -B]
        Bx = np.array([s[2]["ro"][0] for s in sol[:-1]]); By = np.array([s[2]["ro"][1] for s in sol[:-1]])
        anti = float(np.abs(sol[-1][2]["ro"][0] + sol[0][2]["ro"][0])[steel_ro].mean() /
                     np.abs(sol[0][2]["ro"][0])[steel_ro].mean())
        Bx, By = np.vstack([Bx, -Bx]), np.vstack([By, -By])
        pro = 2 * float((harm_loss(Bx, By, n / 60, kh, ke) * m_ro)[steel_ro].sum()) * build
        # wires: one electrical period, all 240 wires
        per = sol[:int(round(72 / STEP))]
        Wx = np.array([s[2]["wires"][0] for s in per]); Wy = np.array([s[2]["wires"][1] for s in per])
        pw = float(wire_loss(Wx, Wy, f_e).sum())
        # delta circulating current from zero-sequence flux harmonics (path = phase voltage in delta)
        psi0 = np.array([np.mean([s[1][p] for p in "RYB"]) for s in per])
        F = np.fft.rfft(psi0) * 2 / len(psi0)
        R_ph = D.R_PATH / 2; L0_ph = L0_path / 2
        circ = []
        for h in [h for h in (3, 9) if h < len(F)]:
            w = 2 * math.pi * f_e * h
            E0 = w * abs(F[h])                                       # path EMF = phase EMF (paths in parallel)
            Ipk = E0 / abs(complex(R_ph, w * L0_ph))
            circ.append(dict(h=h, E_peak_V=E0, I_rms=Ipk / math.sqrt(2), P_W=3 * R_ph * Ipk ** 2 / 2))
        T_femm = float(np.mean([s[0] for s in sol[:-1]])) * r["gamma_sweep"]["sign"]
        map_ = {kk: float(interp(E, kk, T, n)) for kk in ("pcu", "pfe", "pmech", "I_rms", "id", "iq")}
        res[k] = dict(torque=T, rpm=n, f_e_Hz=f_e, id=ops[k][0], iq=ops[k][1], T_em_femm_sweep=T_femm,
                      map=map_, stator_fe_loaded=pst, rotor_fe_loaded=pro, wire_proximity=pw,
                      delta_circulating=circ, rotor_antiperiodic_error=anti,
                      fe_map_stator=map_["pfe"] / (1 + md["ROTOR_FE"]),
                      fe_map_rotor=map_["pfe"] * md["ROTOR_FE"] / (1 + md["ROTOR_FE"]),
                      battery_sag=[min_loss_point(T, n, v) for v in (52.0, 48.0, 46.0, 44.0, 42.0)])
        print(json.dumps(res[k], indent=1, default=float))
    # no-load check: waveform-based stator iron loss vs eff_map's 2 x snapshot B^2 method, at 1000 rpm
    f1 = 1000 / 60 * M.P
    res["noload_1000rpm"] = dict(waveform=stator_fe(noload, f1),
                                 eff_map=(kh * f1 + ke * f1 * f1) * md["stator_B2m_noload"] * build)
    res["L0_path_H"] = L0_path
    print(res["noload_1000rpm"], "L0 path %.1f uH" % (L0_path * 1e6))
    json.dump(res, open(os.path.join(ROOT, "results", os.environ.get("OUT", "loss_check.json")), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
