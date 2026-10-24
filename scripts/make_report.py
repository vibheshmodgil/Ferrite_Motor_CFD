"""Build the self-contained HTML report from the result files.

    .venv/Scripts/python -I scripts/make_report.py      # -> Report/Motor65_Thermal_CFD_Report.html

Everything (figures, charts) is embedded, so the single .html file can be opened, mailed or archived on its own.
Rerun after new results land; sections whose data is missing say so.
"""
import base64, datetime, html, io, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES, FIG = os.path.join(ROOT, "results"), os.path.join(ROOT, "results", "figs")
OUT = os.path.join(ROOT, "Report")
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))
SUM = json.load(open(os.path.join(RES, "summary.json")))
K = 273.15
NAMES = {"peak_torque": "Peak torque", "continuous": "Continuous", "peak_power": "Peak power",
         "cruise": "Cruise", "max_speed": "Max speed"}
ORDER = ["peak_torque", "continuous", "peak_power", "max_speed", "cruise"]
COL = {"peak_torque": "#1f4e8c", "continuous": "#c2185b", "peak_power": "#2e7d32", "max_speed": "#ef6c00",
       "cruise": "#6a1b9a"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.8})


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s))


def img(name, alt):
    p = os.path.join(FIG, name)
    if not os.path.exists(p):
        return f'<p class="todo">Figure {esc(name)} not available yet.</p>'
    b = base64.b64encode(open(p, "rb").read()).decode()
    return f'<figure><img src="data:image/png;base64,{b}" alt="{esc(alt)}"><figcaption>{esc(alt)}</figcaption></figure>'


def inputs(rows, title="Simulation inputs"):
    """Compact key/value box placed directly above a plot: what produced it."""
    r = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f'<div class="inputs"><div class="ih">{esc(title)}</div><table>{r}</table></div>'


def lp_line(lp):
    d = LP[lp]; q = d["Q"]
    return (f"{d['torque']:.0f} N·m @ {d['rpm']} rpm, {d['I_line']:.0f} A rms line · Cu {q['winding_100C']:.0f} W at 100 °C (×(1+0.00393(T−100)) per cell) · "
            f"stator iron {q['stator']:.0f} W · rotor iron {q['rotor']:.0f} W · bearings {q['bearings']:.0f} W · windage {q['inair']:.0f} W")


THERMAL_COMMON = [
    ("Model", "baseline 3D thermal model, 8 conformal solid regions, 2.39 M tetrahedra (gmsh) — OpenFOAM 12 foamMultiRun, solid module"),
    ("Start / ambient", "uniform 40 °C at t = 0; surroundings 40 °C"),
    ("Contacts", "bobbin 1.7 mm @ 0.30 W/m·K · shrink fit 0.02 mm @ 0.026 · magnet glue 0.1 mm @ 0.20"),
    ("Materials", "AlSi10Mg 150 W/m·K · laminations 28/1.5 (in-plane/axial) · winding 1.0 isotropic, ρc 2.63 MJ/m³K · ferrite 4 · steel 45"),
]


def vid(name, caption):
    p = os.path.join(RES, "anim", name)
    if not os.path.exists(p):
        return f'<p class="todo">Animation {esc(name)} not available yet.</p>'
    b = base64.b64encode(open(p, "rb").read()).decode()
    return (f'<figure><video autoplay loop muted playsinline controls src="data:video/mp4;base64,{b}"></video>'
            f'<figcaption>{esc(caption)}</figcaption></figure>')


def svg(fig, caption):
    buf = io.StringIO(); fig.savefig(buf, format="svg", bbox_inches="tight"); plt.close(fig)
    s = buf.getvalue(); s = s[s.index("<svg"):]
    return f'<figure class="chart">{s}<figcaption>{esc(caption)}</figcaption></figure>'


def table(head, rows, cls=""):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def hist(lp, region, kind="T"):
    base = os.path.join(RES, lp, "postProcessing", region, f"{kind}_{region}")
    if region == "winding" and not os.path.isdir(base):
        return None
    a = np.vstack([np.atleast_2d(np.loadtxt(os.path.join(base, t, "volFieldValue.dat"), comments="#"))
                   for t in sorted(os.listdir(base), key=float)])
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    return a[:, 0], a[:, 1] - K


def at(lp, region, t0, kind="T"):
    t, T = hist(lp, region, kind)
    return float(np.interp(t0, t, T))


def heatflow(lp, t):
    f = os.path.join(RES, lp, f"heatflow_{t}.txt")
    if not os.path.exists(f):
        return None
    d = {}
    for line in open(f):
        r, p, q = line.split()
        d[(r, p)] = float(q)
    return d


def hrs(s):
    return f"{s/60:.1f} min" if s < 3600 else f"{s/3600:.1f} h"


done = [lp for lp in ORDER if lp in SUM]
# time each point is evaluated at: its first limit, or the end of the run
T_EVAL = {lp: (SUM[lp]["run_time_s"] or SUM[lp]["t_end_s"]) for lp in done}

# ---------------------------------------------------------------- charts
def chart_losses():
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    pts = sorted(done, key=lambda lp: -sum(LP[lp]["Q"].values()))
    parts = [("Copper (100 °C)", lambda q: q["winding_100C"], "#3a78c2"),
             ("Iron, stator + rotor", lambda q: q["stator"] + q["rotor"], "#e07b39"),
             ("Bearings + windage", lambda q: q["bearings"] + q["inair"], "#3fae7a")]
    left = np.zeros(len(pts))
    for name, f, c in parts:
        v = np.array([f(LP[lp]["Q"]) for lp in pts]); ax.barh(range(len(pts)), v, left=left, color=c, label=name)
        left += v
    for i, lp in enumerate(pts):
        ax.text(left[i] + 8, i, f"{left[i]:.0f} W", va="center", fontweight="bold" if i == 0 else None)
    ax.set_yticks(range(len(pts)), [f"{NAMES[lp]}, {LP[lp]['torque']:.0f} N·m @ {LP[lp]['rpm']}" for lp in pts])
    ax.invert_yaxis(); ax.set_xlabel("heat generated [W]"); ax.grid(axis="y", visible=False)
    ax.legend(ncol=3, loc="lower right", frameon=False, fontsize=9); ax.set_xlim(0, left.max() * 1.15)
    ax.set_title("Peak torque dissipates ~925 W, nearly all copper loss", loc="left", fontweight="bold")
    return svg(fig, "Losses from the calibrated FEMM map (femm_em/eff.json), bilinear on the torque × speed grid.")


def chart_histories():
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharex=True)
    for lp in done:
        for ax, r in zip(axs, ("winding", "magnets")):
            t, T = hist(lp, r)
            ax.plot(t / 3600, T, color=COL[lp], lw=2 if lp == "peak_torque" else 1.6, label=NAMES[lp])
    for ax, lim, name in zip(axs, (155, 100), ("winding hot spot", "magnet maximum")):
        ax.axhline(lim, color="#c62828", ls="--", lw=1); ax.text(0.1, lim + 2, f"limit {lim} °C", color="#c62828", fontsize=9)
        ax.set_title(f"{name} [°C]", loc="left", fontweight="bold"); ax.set_xlabel("time from cold start [h]")
        ax.set_xlim(0, 12)
    axs[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.suptitle("Long runs keep heating for 10+ h in still air; the magnets reach 100 °C first", x=0.01, ha="left",
                 fontweight="bold", y=1.03)
    return svg(fig, "OpenFOAM monitor histories (maximum of each region) from a 40 °C cold start, 0–12 h of motor time.")


def chart_peak():
    t, Tw = hist("peak_torque", "winding"); _, Ta = hist("peak_torque", "winding", "Tavg")
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    ax.plot(t, Tw, color="#1f4e8c", lw=2.4, label="winding hot spot")
    ax.plot(t, Ta, color="#888", lw=1.4, ls="--", label="winding average")
    for r, lab in (("stator", "stator max"), ("magnets", "magnet max"), ("housing", "housing max")):
        tt, T = hist("peak_torque", r); ax.plot(tt, T, color="#aaa", lw=1.2); ax.text(tt[-1] + 3, T[-1], lab, fontsize=8.5, color="#666", va="center")
    ax.axhline(155, color="#c62828", ls="--", lw=1); ax.axvline(SUM["peak_torque"]["run_time_s"], color="#c62828", ls=":", lw=1)
    ax.text(SUM["peak_torque"]["run_time_s"] + 3, 45, f"{SUM['peak_torque']['run_time_s']:.0f} s", color="#c62828", fontweight="bold")
    ax.set_xlabel("time from cold start [s]"); ax.set_ylabel("°C"); ax.set_xlim(0, 285); ax.legend(frameon=False, loc="upper left")
    ax.set_title("At peak torque the winding hot spot reaches 155 °C after 183 s", loc="left", fontweight="bold")
    return svg(fig, "45 N·m @ 2000 rpm from 40 °C, natural convection.")


def chart_components():
    regs = ["winding", "inair", "stator", "rotor", "magnets", "housing", "bearings", "shaft"]
    lab = ["Winding", "Internal air", "Stator", "Rotor", "Magnets", "Housing", "Bearings", "Shaft"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    for j, lp in enumerate(done):
        v = [at(lp, r, T_EVAL[lp]) for r in regs]
        ax.scatter(v, np.arange(len(regs)) + (j - 2) * 0.09, s=55, color=COL[lp], zorder=3,
                   label=f"{NAMES[lp]} at {hrs(T_EVAL[lp])}")
    ax.plot([155, 155], [-0.4, 0.4], color="#c62828", lw=2); ax.text(156, -0.25, "limit 155", color="#c62828", fontsize=8.5)
    ax.plot([100, 100], [3.6, 4.4], color="#c62828", lw=2); ax.text(101, 3.75, "limit 100", color="#c62828", fontsize=8.5)
    ax.set_yticks(range(len(regs)), lab); ax.invert_yaxis(); ax.set_xlabel("maximum temperature [°C]")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3)
    ax.set_title("Short bursts heat only the copper; long runs soak the whole motor to ~100 °C\n", loc="left", fontweight="bold")
    return svg(fig, "Region maxima at each load point's limit time (cruise: end of the 12 h run).")


def heatpath_svg(lp, t):
    """Box-and-arrow heat-flow diagram, arrow width proportional to watts (source-side interface flows)."""
    hf = heatflow(lp, t)
    if not hf:
        return '<p class="todo">Heat-path data not available yet.</p>'
    Q = LP[lp]["Q"]; Tw = at(lp, "winding", t, "Tavg")
    cu = Q["winding_100C"] * (1 + 0.00393 * (Tw - 100)); gen = cu + Q["stator"] + Q["rotor"] + Q["bearings"] + Q["inair"]
    out = -hf.get(("housing", "defaultFaces"), 0) - hf.get(("shaft", "defaultFaces"), 0)
    E = [("w", "st", -hf[("winding", "winding_to_stator")]), ("w", "air", -hf[("winding", "winding_to_inair")]),
         ("air", "st", -hf[("inair", "inair_to_stator")]), ("air", "rot", -hf[("inair", "inair_to_rotor")]),
         ("air", "hous", -hf[("inair", "inair_to_housing")]), ("st", "hous", hf[("housing", "housing_to_stator")]),
         ("hous", "amb", out)]
    N = {"w": (95, 215, "Winding", f"makes {cu:.0f} W (copper)"), "st": (300, 130, "Stator", f"makes {Q['stator']:.0f} W (iron)"),
         "air": (300, 300, "Internal air", "end spaces"), "rot": (505, 380, "Rotor, magnets", f"makes {Q['rotor']+Q['bearings']+Q['inair']:.0f} W"),
         "hous": (505, 180, "Housing", "fins, end shields"), "amb": (675, 180, "Ambient air", "convection + radiation")}
    BW, BH = 140, 50
    s = ['<svg viewBox="0 0 760 460" class="diagram" role="img" aria-label="heat paths">',
         '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0L10 5L0 10z" fill="#c2185b"/></marker></defs>']
    for a, b, w in E:
        x1, y1, *_ = N[a]; x2, y2, *_ = N[b]
        if x1 == x2:
            dpath = f"M{x1} {y1 - BH/2}L{x2} {y2 + BH/2 + 4}"; lx, ly, anc = x1 + 14, (y1 + y2) / 2 + 4, "start"
        else:
            sx, ex = x1 + BW / 2, x2 - BW / 2 - 4; mx = (sx + ex) / 2
            dpath = f"M{sx} {y1}C{mx} {y1} {mx} {y2} {ex} {y2}"; lx, ly, anc = mx, (y1 + y2) / 2 - (1.5 + w * 0.11) / 2 - 6, "middle"
            if (a, b) == ("hous", "amb"): ly = y1 - 34
            if (a, b) == ("air", "rot"): lx, ly = mx - 34, (y1 + y2) / 2 + 22
            if (a, b) == ("st", "hous"): ly -= 10
        s.append(f'<path d="{dpath}" fill="none" stroke="#c2185b" stroke-opacity="0.45" stroke-width="{1.5 + max(w, 0) * 0.11:.1f}" marker-end="url(#ar)"/>')
        s.append(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="{anc}" class="lbl">{w:.0f} W</text>')
    for k, (x, y, name, sub) in N.items():
        s.append(f'<rect x="{x-BW/2}" y="{y-BH/2}" width="{BW}" height="{BH}" rx="8" class="node"/>')
        s.append(f'<text x="{x}" y="{y-4}" text-anchor="middle" class="nname">{name}</text><text x="{x}" y="{y+13}" text-anchor="middle" class="nsub">{sub}</text>')
    s.append(f'<text x="24" y="445" class="nsub">Generated {gen:.0f} W − leaving to ambient {out:.0f} W = {gen-out:.0f} W stored in the motor mass ({(gen-out)/gen*100:.0f} %)</text></svg>')
    return "".join(s), gen, out, cu


# ---------------------------------------------------------------- content
def results_table():
    rows = []
    for lp in ORDER:
        d = LP[lp]; s = SUM.get(lp)
        heat = sum(d["Q"].values())
        if not s:
            rows.append([NAMES[lp], f"{d['torque']:.0f}", d["rpm"], f"{heat:.0f}", "<i>running</i>", "", ""]); continue
        rt = f"<b>{hrs(s['run_time_s'])}</b>" if s["run_time_s"] else "<b>continuous</b> (no limit in 12 h)"
        by = {"winding": "winding 155 °C", "magnets": "magnets 100 °C"}.get(s["limited_by"], "—")
        tw = s["time_to_winding_limit_s"]
        rows.append([NAMES[lp], f"{d['torque']:.0f}", d["rpm"], f"{heat:.0f}", rt, by,
                     hrs(tw) if tw else f"not within 12 h ({s['winding_max_end_C']:.0f} °C)"])
    return table(["Load point", "Torque (N·m)", "Speed (rpm)", "Heat at 100 °C Cu (W)", "Run time to first limit",
                  "Limited by", "Winding reaches 155 °C"], rows)


def gen_table():
    rows, heads = [], ["Source"] + [f"{NAMES[lp]}, {hrs(T_EVAL[lp])}" for lp in done]
    tot = []
    for name, f in (("Copper, winding (at actual T)", None), ("Iron, stator", "stator"), ("Iron, rotor", "rotor"),
                    ("Bearings (friction)", "bearings"), ("Windage (internal air)", "inair")):
        r = [name]
        for lp in done:
            Q = LP[lp]["Q"]
            v = Q["winding_100C"] * (1 + 0.00393 * (at(lp, "winding", T_EVAL[lp], "Tavg") - 100)) if f is None else Q[f]
            r.append(f"{v:.0f}")
        rows.append(r)
    rows.append(["<b>Total</b>"] + [f"<b>{sum(float(rw[i+1]) for rw in rows):.0f}</b>" for i in range(len(done))])
    return table(heads, rows)


def path_table():
    keys = [("Winding → stator (bobbin wall)", lambda h: -h[("winding", "winding_to_stator")]),
            ("Winding → internal air", lambda h: -h[("winding", "winding_to_inair")]),
            ("Internal air → housing", lambda h: -h[("inair", "inair_to_housing")]),
            ("Internal air → rotor", lambda h: -h[("inair", "inair_to_rotor")]),
            ("Stator → housing (shrink fit)", lambda h: h[("housing", "housing_to_stator")]),
            ("Housing + shaft → ambient", lambda h: -h.get(("housing", "defaultFaces"), 0) - h.get(("shaft", "defaultFaces"), 0))]
    sets = [("peak_torque", 200), ("continuous", 18000), ("peak_power", 36000), ("max_speed", 43200), ("cruise", 43200)]
    sets = [(lp, t) for lp, t in sets if heatflow(lp, t)]
    rows = [[k] + [f"{f(heatflow(lp, t)):.0f}" for lp, t in sets] for k, f in keys]
    return table(["Heat path (W)"] + [f"{NAMES[lp]}, {hrs(t)}" for lp, t in sets], rows)


def internal_air():
    f = os.path.join(RES, "inair_continuous", "wall_q.txt")
    if not os.path.exists(f):
        return ('<p class="todo">The internal-air CFD (rotor and shaft spinning at 3000 rpm in the real end-space volume, '
                'walls at the thermal solution\'s temperatures) is running. Its flow pictures and the CFD heat-transfer '
                'coefficient on each internal surface will appear here.</p>')
    rows, air = [], None
    lines = [l.split() for l in open(f) if l.strip()]
    for l in lines:
        if l[0] == "air": air = float(l[1])
    if air is None or len(lines) < 3:
        return '<p class="todo">The internal-air CFD is still running; its results will appear here.</p>'
    corr = LP["continuous"]["h_endspace"]
    box = inputs([
        ("Fluid volume", "the connected end-space air inside the motor (505 k of the 536 k internal-air cells; shaft bore and slot slivers excluded); the 0.5 mm air gap is not in this mesh"),
        ("Rotation", "rotor and shaft walls at 3000 rpm (ω = 314.16 rad/s), continuous load point"),
        ("Wall temperatures", ", ".join(f"{l[0]} {float(l[1])-K:.0f} °C" for l in lines if l[0] != "air" and len(l) > 1) + " — from the continuous thermal solution at 5 h"),
        ("Physics / solver", "steady, turbulent k-ω SST with wall functions, no gravity (forced convection); ideal-gas air; SIMPLE, restarted at iteration 500 with upwind U and 0.2/0.3 relaxation; 2000 iterations"),
        ("h definition", "h = Q_wall / (A_wall · (T_wall − T_air,mean))")])
    model = {"winding": 127, "housing": 74, "rotor": 39, "stator": 10}       # baseline thermal model, continuous 5 h (W)
    for l in lines:
        if l[0] == "air" or len(l) < 4: continue
        tw, q, a = float(l[1]), float(l[2]), float(l[3]); dT = tw - air
        h = abs(q) / (a * abs(dT)) if abs(dT) > 3 else float("nan")
        rows.append([l[0], f"{tw-K:.1f}", f"{a*1e4:.0f}", f"{q:+.1f}", "—" if h != h else f"{h:.0f}", f"{corr:.0f}",
                     f"{model[l[0]]:.0f}" if l[0] in model else "—"])
    out = box + (f"""<p class="lead">The spinning rotor drags the end-space air into a swirling ring (up to ~3 m/s, about 20 % of the 16.6 m/s
rotor tip speed) inside the ring of end windings, and drives one recirculating vortex in each end space, fed by a fast jet (up to 13 m/s)
flung off the rotor end faces. The air between the end windings and the housing wall is almost stagnant.</p>
<p>Mean internal air temperature {air-K:.1f} °C. Positive Q = heat from the wall into the air.</p>"""
           + table(["Surface", "Wall T (°C)", "Area (cm²)", "Q into air (W)", "CFD h (W/m²K)", "Correlation h (W/m²K)",
                    "Baseline model flow (W)"], rows)
           + """<p><b>Finding.</b> The CFD end-winding coefficient (≈ 28 W/m²K) is about half the correlation (57), and with the same wall
temperatures the CFD carries only ~24 W from the winding into the air, where the baseline thermal model's effective-conductivity air carries
~127 W. Representing the air as a conducting solid over-cools wherever the gaps are only a few millimetres. <b>The baseline run times are
therefore optimistic</b>; the thermal model should be re-run with the internal air calibrated to this CFD (see Limitations).</p>
<p class="note">Converged CFD state at 2000 iterations (continuity error 3×10⁻⁴; the winding heat flow changed by &lt; 4 % between iterations 1000 and 2000).
The stator face has only ~2 K difference to the air, so its h is not meaningful.</p>""")
    out += img("flow_int_z.png", "Streamlines inside the motor, radial plane in the drive-end space (z = −40 mm): the swirl ring between the bearing hub and the end windings; parts labelled")
    out += img("flow_int_x.png", "Streamlines inside the motor, axial mid-plane: one recirculating vortex in each end space, between the rotor ends, end windings and housing")
    out += vid("inair_z.mp4", "Animation: air inside the motor, radial plane in the drive-end space (slow motion)")
    out += vid("inair_x.mp4", "Animation: air inside the motor, axial mid-plane (slow motion)")
    for ax, cap in (("z", "Internal air speed, radial plane in the drive-end space"), ("x", "Internal air speed, axial mid-plane")):
        out += img(f"inair_speed_{ax}.png", cap)
    out += img("inair_temp_x.png", "Internal air temperature, axial mid-plane")
    return out


def card(title, rows):
    r = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f'<div class="card"><h3>{esc(title)}</h3><table>{r}</table></div>'


def setup_section():
    lpr = "".join(f"<li><b>{NAMES[lp]}</b>: {lp_line(lp)}</li>" for lp in ORDER)
    return (img("bc_schematic.png", "Where each boundary condition, heat source and contact layer acts (axial section of the thermal model)")
        + card("1 · Transient thermal model (all five load points)", [
            ("Purpose", "temperature of every part versus time from a cold start; time to the 155 °C winding / 100 °C magnet limits"),
            ("Geometry", "motor_65 CAD: housing + rear cover, 12 stator teeth, 12 winding blocks, rotor stack, 20 magnets, shaft, 2 bearings, internal air (8 regions)"),
            ("Mesh", "2.39 M conformal tetrahedra (gmsh), 3 mm base size with curvature refinement"),
            ("Materials", "housing AlSi10Mg k 150 · laminations k 28 in-plane / 1.5 axial · winding k 1.0, ρc 2.63 MJ/m³K · ferrite k 4 · steel k 45 · bearings k 15 · internal air k_eff 0.47–1.18"),
            ("Heat sources", f"<ul>{lpr}</ul>"),
            ("Outer boundary", "housing and shaft skin: per-face CFD h (0–22, mean 4.0 W/m²K; peak torque: uniform 6) + radiation ε 0.7 to 40 °C"),
            ("Internal interfaces", "coupled temperature + layers: bobbin 1.7 mm/0.30 · shrink fit 0.02 mm/0.026 · glue 0.1 mm/0.20 · air gap 0.5 mm/Taylor–Couette k_eff"),
            ("Other boundaries", "cavity cut faces (gland holes, shaft bore end): adiabatic"),
            ("Initial condition", "all regions 40 °C at t = 0"),
            ("Solver", "OpenFOAM 12 foamMultiRun (solid), implicit Euler; peak Δt 1 s × 2 coupling iterations; long runs Δt 60–120 s × 1 iteration, 12 h"),
            ("Outputs", "max / mean temperature of every region each step; saved fields for sections, heat paths and animations")])
        + card("2 · External natural-convection CFD (cooling of the outer skin)", [
            ("Purpose", "the convective h on every face of the housing and shaft, used by model 1"),
            ("Geometry", "air around the motor in a closed box 0.6 × 0.8 × 0.65 m; motor surfaces from the same CAD"),
            ("Mesh", "0.81 M tetrahedra, 2.5 mm at the skin and in the fin gaps → 40 mm at the walls"),
            ("Fluid", "air, ideal gas, Cp 1007 J/kg·K, μ 1.95e-5 Pa·s, Pr 0.71; gravity −9.81 m/s² (shaft horizontal)"),
            ("Boundaries", "motor skin: no-slip, fixed 100 °C · box walls: no-slip, fixed 40 °C"),
            ("Solver", "steady laminar buoyant (OpenFOAM fluid, SIMPLE), 3000 iterations; checks: peak speed 0.56 m/s vs buoyancy scale 0.57, mean h 4.0 vs Churchill–Chu 3–6"),
            ("Outputs", "air speed and temperature fields; h = q_wall / (100 − 40 °C) per face")])
        + card("3 · Internal air CFD (air inside the motor, 3000 rpm)", [
            ("Purpose", "show the rotor-driven airflow in the end spaces and check the end-space h used in model 1"),
            ("Geometry", "connected end-space air (505 k of 536 k internal-air cells); air gap not included"),
            ("Fluid", "air, ideal gas, same properties; no gravity (forced convection)"),
            ("Boundaries", "rotor and shaft walls rotate at 314.16 rad/s; all walls held at model 1's temperatures at 5 h of the continuous run: "
                           "winding 121 °C, stator 106 °C, rotor 98 °C, housing 97 °C, bearings 93 °C, shaft 92 °C"),
            ("Solver", "steady RANS k-ω SST with wall functions (OpenFOAM fluid, SIMPLE), restarted at iteration 500 with upwind U, 2000 iterations"),
            ("Outputs", "internal air speed and temperature; h = Q_wall / (A·(T_wall − T_air)) per surface")]))


def build():
    hp = heatpath_svg("continuous", 18000)
    hp_svg = hp[0] if isinstance(hp, tuple) else hp
    hpp = heatpath_svg("peak_torque", 200)
    hp_svg = ("<h3>Peak torque, 45 N·m @ 2000 rpm, at 200 s (limit at 183 s)</h3>"
              + (hpp[0] if isinstance(hpp, tuple) else hpp)
              + "<p>At peak torque almost all the heat stays in the copper: of ~1000 W generated, about 650 W has left the coils by 200 s "
                "(half through the bobbin wall into the teeth, half into the end-space air) and only ~40 W has reached the room. "
                "The winding heats itself up; the housing and fins play no part in a 3-minute burst.</p>"
              + "<h3>Continuous, 24 N·m @ 3000 rpm, at 5.0 h</h3>" + hp_svg)
    det = os.path.isdir(os.path.join(RES, "detailed"))
    secs = []
    secs.append(("summary", "Executive summary", f"""
<p class="lead">In still air at 40 °C, motor_65 can deliver <b>peak torque (45 N·m @ 2000 rpm) for 3.0 minutes</b> from a cold
start before the winding hot spot reaches 155 °C. At the continuous point (24 N·m @ 3000 rpm) it runs <b>4.9 h</b> before
the magnets reach 100 °C (the winding would reach 155 °C at 7.7 h). Cruise (8 N·m @ 6000 rpm) can run indefinitely.</p>
{results_table()}
<p class="note"><b>Provisional.</b> These baseline run times are optimistic: the internal-air CFD shows the end windings are cooled less than the
baseline model assumed, and the long runs used a time step that under-predicts the heating rate by up to ~30 %. They will be re-computed
with the new FEMM loss model and the real CAD (see "Internal airflow: implications" and "Limitations").</p>
<ul>
<li><b>Short bursts are copper-limited.</b> 93 % of peak-torque heat is copper loss and almost none of it leaves the coils in 3 minutes.</li>
<li><b>Long runs are soak-limited.</b> Still-air cooling (4 W/m²K convection + radiation) removes only ~130 W at a 60 K rise, so the whole
motor slowly soaks to ~100 °C and the magnets reach their limit first.</li>
<li><b>The 100 °C magnet limit drives every long-run rating.</b> Sintered ferrite itself tolerates 150 °C+; if 100 °C comes from the glue
or bearings, the winding becomes the limit (continuous: 7.7 h; peak power and cruise: no limit in 12 h).</li>
<li><b>Any airflow over the fins changes the picture</b>: the motor is still storing 58–61 % of its heat after 5–10 h.</li>
</ul>"""))
    secs.append(("scope", "Scope and load points", """
<p>Transient 3D thermal analysis of the motor_65 variant (12-slot/10-pole spoke-ferrite PMSM, 65 mm stator, 52 V, finned AlSi10Mg
housing) from a 40 °C cold start, cooled only by natural convection and radiation (motor standing in still air, shaft horizontal).
Limits: winding hot spot 155 °C, magnets 100 °C. Long runs are computed to 12 h of motor time.</p>"""
        + table(["Load point", "Torque (N·m)", "Speed (rpm)", "Shaft power (kW)", "Line current (A rms)"],
                [[NAMES[lp], f"{LP[lp]['torque']:.0f}", LP[lp]["rpm"], f"{LP[lp]['P_shaft_kW']:.2f}", f"{LP[lp]['I_line']:.0f}"] for lp in ORDER])))
    secs.append(("setup", "Simulation set-up and boundary conditions", setup_section()))
    secs.append(("workflow", "Software and workflow", """
<p>All tools are free and open source and run on the 4-core / 16 GB laptop.</p>"""
        + table(["Tool", "Used for"], [["gmsh 4 (Python API, OpenCASCADE)", "STEP import, booleans, conformal multi-region tetrahedral meshing"],
                                      ["OpenFOAM 12 (openfoam.org)", "multi-region transient conduction (foamMultiRun); buoyant and rotating air CFD (fluid)"],
                                      ["Ubuntu 24.04 on WSL2", "Linux runtime, 4 MPI ranks"], ["ParaView 6.2", "section and field pictures"],
                                      ["Python, NumPy, SciPy, Matplotlib", "load-point losses, h mapping, post-processing, this report"]])
        + """
<svg viewBox="0 0 760 300" class="diagram" role="img" aria-label="workflow">
<defs><marker id="wf" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#777"/></marker></defs>
<g fill="none" stroke="#999" stroke-width="1.3">
<path d="M184 70H208" marker-end="url(#wf)"/><path d="M104 96V160H208" marker-end="url(#wf)"/><path d="M184 250H208" marker-end="url(#wf)"/>
<path d="M368 70H392" marker-end="url(#wf)"/><path d="M368 160H392" marker-end="url(#wf)"/><path d="M368 250H392" marker-end="url(#wf)"/><path d="M552 160H576" marker-end="url(#wf)"/></g>
<rect x="24" y="44" width="160" height="52" rx="8" class="node"/><text x="104" y="66" class="nname" text-anchor="middle">Motor CAD</text><text x="104" y="84" class="nsub" text-anchor="middle">motor_65 STEP parts</text>
<rect x="24" y="224" width="160" height="52" rx="8" class="node"/><text x="104" y="246" class="nname" text-anchor="middle">FEMM loss map</text><text x="104" y="264" class="nsub" text-anchor="middle">eff.json, T × n grid</text>
<rect x="208" y="44" width="160" height="52" rx="8" class="node"/><text x="288" y="66" class="nname" text-anchor="middle">Solid mesh</text><text x="288" y="84" class="nsub" text-anchor="middle">gmsh, 8 regions, 2.39 M</text>
<rect x="208" y="134" width="160" height="52" rx="8" class="node"/><text x="288" y="156" class="nname" text-anchor="middle">Air CFD</text><text x="288" y="174" class="nsub" text-anchor="middle">outside + inside, h per face</text>
<rect x="208" y="224" width="160" height="52" rx="8" class="node"/><text x="288" y="246" class="nname" text-anchor="middle">Load-point losses</text><text x="288" y="264" class="nsub" text-anchor="middle">Cu(T), iron, mechanical</text>
<rect x="392" y="44" width="160" height="232" rx="8" class="node accent"/><text x="472" y="70" class="nname" text-anchor="middle">Transient thermal</text>
<text x="472" y="94" class="nsub" text-anchor="middle">OpenFOAM foamMultiRun</text><text x="472" y="124" class="nsub" text-anchor="middle">8 coupled solid regions</text>
<text x="472" y="144" class="nsub" text-anchor="middle">contact layers, air gap</text><text x="472" y="164" class="nsub" text-anchor="middle">copper loss rises with T</text>
<text x="472" y="184" class="nsub" text-anchor="middle">CFD h + radiation outside</text><text x="472" y="204" class="nsub" text-anchor="middle">40 °C cold start, 0–12 h</text>
<rect x="576" y="134" width="160" height="52" rx="8" class="node"/><text x="656" y="156" class="nname" text-anchor="middle">Run time per point</text><text x="656" y="174" class="nsub" text-anchor="middle">first of 155 / 100 °C</text>
</svg>"""))
    secs.append(("model", "Thermal model", """
<p>The model is the full 3D motor_65 CAD (<code>cad/motor_65</code>, placed by <code>instances.json</code>), split into eight conformal
solid regions coupled through their interfaces.</p>"""
        + table(["Region", "Built from", "Volume (cm³)"], [["Housing", "housing + rear cover + O-ring seat, fused", "753"],
            ["Stator", "12 tooth segments, fused", "463"], ["Winding", "12 homogenised coil blocks around the tooth necks", "348"],
            ["Rotor", "lamination stack, OD grown to the 107 mm bore", "278"], ["Magnets", "20 ferrite blocks", "268"],
            ["Shaft", "hollow Ø30 / Ø14", "89"], ["Bearings", "two 52/30 × 15 rings", "43"],
            ["Internal air", "everything inside the housing not occupied by a part", "981"]])
        + """<ul><li><b>Winding:</b> each swept-wire coil is replaced by a block around the tooth neck, clipped to its slot; copper fill 0.51.</li>
<li><b>Air gap:</b> rotor grown 0.5 mm to the bore; the gap is a thermal layer with speed-dependent conductivity.</li>
<li><b>Internal air:</b> closed cavity minus all parts; convection represented as an effective conductivity (checked by internal CFD).</li>
<li><b>Removed (thermally minor):</b> shaft seal, cable glands, terminal bars, busbars (28 W, in the detailed model), encoder, fasteners.</li></ul>"""))
    secs.append(("mesh", "Mesh", """<p>2.39 M tetrahedra in the solid model (3 mm base size, curvature refinement) and 0.81 M in the external-air CFD
(2.5 mm at the skin, 40 mm at the box walls). checkMesh: valid; max skewness 3.19; mean non-orthogonality 24°.</p>"""
        + table(["Region", "Cells"], [["Stator", "1,168,891"], ["Internal air", "536,238"], ["Housing", "349,305"], ["Winding", "177,331"],
                                      ["Rotor", "75,139"], ["Magnets", "56,358"], ["Shaft", "19,307"], ["Bearings", "8,568"]])))
    secs.append(("materials", "Materials and interfaces", table(
        ["Region", "Material", "ρ (kg/m³)", "c (J/kg·K)", "k (W/m·K)"],
        [["Housing", "AlSi10Mg", "2680", "900", "150"], ["Stator, rotor", "M235-35A stack", "7650", "460", "28 in-plane / 1.5 axial"],
         ["Winding", "Cu (0.51) + resin", "5144", "513", "1.0 (isotropic)"], ["Magnets", "sintered ferrite", "4900", "800", "4"],
         ["Shaft", "steel", "7850", "460", "45"], ["Bearings", "steel ring (ball contacts)", "7850", "460", "15"],
         ["Internal air", "air, effective", "10", "718", "0.47–1.18 (speed)"]])
        + table(["Interface", "Layer", "Thickness (mm)", "k (W/m·K)", "Conductance (W/m²K)"],
                [["Winding → stator", "bobbin wall + resin", "1.7", "0.30", "176"], ["Stator → housing", "shrink fit", "0.02", "0.026", "1300"],
                 ["Magnet → rotor", "glue", "0.1", "0.20", "2000"], ["Rotor → stator", "0.5 mm air gap", "0.5", "0.030–0.070", "60–140"]])))
    secs.append(("losses", "Heat sources", inputs([
        ("Source", "femm_em/eff.json — FEMM 4.2 2D magnetostatic study, calibrated to Motor-CAD (45 N·m at 360 A rms)"),
        ("Copper", "DC, R at 100 °C (6.732 mΩ per coil); AC/skin and PWM losses not included"),
        ("Iron", "Steinmetz fit KH 0.0177, KE 6.2e-5, build factor 1.5; rotor = 10 % of stator"),
        ("Mechanical", "0.004·n (bearings) + 2.2e-7·n² (windage) W, n in rpm"),
        ("Interpolation", "bilinear on the 46 torque × 48 speed grid")]) + chart_losses() + """<p>Copper loss goes into the winding as q = q<sub>100</sub>(1 + 0.00393 (T − 100 °C)) per cell,
so a hot winding makes more heat. Iron is split 91 % stator / 9 % rotor; bearing friction (0.004 W/rpm) into the bearings and windage
(2.2×10⁻⁷ W/rpm²) into the internal air. AC copper and PWM losses are not included (high-speed results are optimistic).</p>"""))
    secs.append(("external", "External natural-convection CFD and airflow", """
<p>In still air the finned housing is cooled at an average of <b>4.0 W/m²K</b> by convection (shaft 6.2); radiation (ε 0.7) is added on top.
Every housing face carries its own CFD value in the thermal model.</p>"""
        + table(["Setting", "Value"], [["Domain", "closed box 0.6 × 0.8 × 0.65 m, walls at 40 °C (still room air)"], ["Motor skin", "100 °C (ΔT = 60 K)"],
            ["Flow", "steady, laminar, buoyant air (Ra ≈ 2×10⁷)"], ["Solver", "OpenFOAM 12 fluid, SIMPLE (buoyantCavity settings), 3000 iterations"],
            ["Mesh", "0.81 M tetrahedra"]])
        + table(["Result", "Value", "Check"], [["Mean h, housing", "4.02 W/m²K", "Churchill–Chu: 5.4 on a smooth Ø188 mm cylinder; fins shield each other → 3–6 expected"],
            ["Local h, housing", "0–22 W/m²K", "highest at fin tips and underside, near zero in fin roots"], ["Peak air speed", "0.56 m/s", "buoyancy scale √(gβΔT·L) = 0.57 m/s"],
            ["Median air speed", "0.08 m/s", "air away from the motor nearly still"]])
        + inputs([
            ("Applies to", "all external-airflow pictures, animations and the h map below"),
            ("Domain / walls", "closed box 0.6 × 0.8 × 0.65 m, no-slip walls at 40 °C; motor centred at the origin, shaft along z (horizontal)"),
            ("Motor skin", "isothermal 100 °C on every outer face (housing, fins, end shields, shaft) — ΔT = 60 K"),
            ("Air", "ideal gas, Cp 1007 J/kg·K, μ 1.95e-5 Pa·s, Pr 0.71; gravity −9.81 m/s² in y"),
            ("Physics / solver", "steady, laminar, buoyant (OpenFOAM 12 fluid, SIMPLE, p_rgh 0.7 / U 0.3 / h 0.3 relaxation), no radiation"),
            ("Mesh / run", "0.81 M tetrahedra, 2.5 mm at the skin → 40 mm at the walls; 3000 iterations"),
            ("Animations", "10 s clips, 1400 tracer particles advected (RK2) by the in-plane velocity, real time; colour = full speed |U|")])
        + "<h3>Animated airflow</h3><p>Tracer particles released into the CFD velocity field, shown in real time. Air is drawn in round the "
          "sides and underside, wraps the housing in a thin warm layer and leaves as one plume; two slow eddies turn under the box ceiling.</p>"
        + vid("air_z.mp4", "Animation: air around the motor, radial mid-plane (real time)")
        + vid("air_x.mp4", "Animation: air around the motor, axial mid-plane, rear left / drive end right (real time)")
        + "<h3>Flow paths with the motor parts</h3>"
        + img("flow_ext_z.png", "Streamlines around the motor on the radial mid-plane (z = 5 mm); the motor's parts drawn in grey and copper, labelled")
        + img("flow_ext_x.png", "Streamlines on the axial mid-plane (x = 0): the plume leaves along the whole finned length")
        + "<h3>Field pictures</h3>"
        + img("air_speed_z.png", "Air speed and flow direction, radial mid-plane: one plume rises off the top of the housing")
        + img("air_speed_x.png", "Air speed, axial mid-plane")
        + img("air_temp_z.png", "Air temperature, radial mid-plane (the closed box stratifies to 55–60 °C under its ceiling: slightly conservative)")
        + img("air_h.png", "Convective h on the motor skin (ΔT = 60 K)")
        + """<p class="note">Two earlier set-ups (open box with fixed pressure; pseudo-transient scheme) gave non-physical flow (5–8 m/s) and were discarded
before any thermal run used them. The pipeline now stops itself if the CFD exceeds 0.8 m/s (99th percentile) or mean h leaves 2–12 W/m²K.</p>"""))
    secs.append(("htc", "How each heat-transfer coefficient is obtained", table(
        ["Surface", "Method", "Value"],
        [["Housing, shaft (outside)", "3D natural-convection CFD, per face", "0–22, mean 4.0 W/m²K"],
         ["Housing, shaft (radiation)", "grey body to 40 °C, re-linearised every step", "ε 0.7 → 6–9 W/m²K"],
         ["Air gap (0.5 mm)", "Taylor–Couette (Becker–Kaye)", "k<sub>eff</sub> 0.030–0.070 W/m·K"],
         ["End spaces", "rotor-tip-speed correlation as effective conductivity; checked by internal CFD", "h 47–118 W/m²K"],
         ["Solid contacts", "thin layers (see Materials)", "176–2000 W/m²K"]])
        + """<div class="eq">h<sub>face</sub> = q<sub>wall</sub> / (T<sub>wall</sub> − T<sub>∞</sub>), with T<sub>wall</sub> = 100 °C, T<sub>∞</sub> = 40 °C</div>
<div class="eq">h<sub>rad</sub> = ε σ (T<sub>w</sub>² + T<sub>∞</sub>²)(T<sub>w</sub> + T<sub>∞</sub>)</div>
<div class="eq">Ta = ω² r<sub>m</sub> δ³ / ν² ; Nu = 2 (Ta &lt; 1740), 0.128 Ta<sup>0.367</sup> (&lt; 10⁴), 0.409 Ta<sup>0.241</sup> (≥ 10⁴) ; k<sub>eff</sub> = (Nu/2) k<sub>air</sub></div>
<div class="eq">h<sub>end</sub> = 15 + 6.75 v<sup>0.65</sup> W/m²K, v = rotor tip speed in m/s</div>
<p>OpenFOAM 12's external boundary condition accepts only a uniform h, so the thermal runs use a custom mixed boundary condition that reads the
per-face CFD h and adds the linearised radiation every step. The h map was computed at ΔT = 60 K; natural-convection h scales ~ΔT<sup>0.25</sup>
(≈ +15 % at 30 K, −10 % at 100 K), not corrected.</p>"""))
    secs.append(("internal", "Airflow inside the motor", internal_air()))
    secs.append(("internal-implications", "Internal airflow: implications and complications", """
<p class="lead">The internal CFD shows that the air inside the motor removes far less heat from the end windings than the baseline thermal
model assumed, and that it heats the rotor rather than cooling it. Both make the baseline run times optimistic.</p>
<h3>What the internal flow means for the thermal results</h3>
<table><thead><tr><th>Observation (CFD, 3000 rpm)</th><th>Consequence</th></tr></thead><tbody>
<tr><td>End-winding h ≈ 27 W/m²K, half the 57 W/m²K correlation</td><td>The end turns — already the hot spot — shed less heat than modelled; the hot spot runs hotter.</td></tr>
<tr><td>Winding → air only ~23 W, versus ~127 W through the baseline's conducting air</td><td>The baseline over-cools the winding by roughly 100 W at the continuous point (≈ 40 % of the copper loss): <b>continuous and long-run run times are optimistic</b>. At peak torque the effect is smaller (most heat is stored) but the 3.0 min is also on the high side.</td></tr>
<tr><td>Air between end windings and housing is almost stagnant</td><td>The end-winding-to-housing route through air is weak; heat must go through the bobbin into the teeth instead. Potting the end turns to the housing would replace this weak path with a solid one.</td></tr>
<tr><td>Air (≈ 104 °C) is hotter than the rotor (≈ 98 °C); rotor-end h ≈ 58 W/m²K</td><td>The swirl actively <b>heats the rotor and magnets</b> — consistent with the magnets becoming the long-run limit.</td></tr>
<tr><td>Fast jet (up to 13 m/s) off the rotor end faces, ring swirl ~3 m/s</td><td>Mixing is strong near the rotor and weak near the housing; a single "end-space h" cannot represent both.</td></tr>
</tbody></table>
<h3>Complications and limits of this internal CFD</h3>
<ul>
<li><b>One-way, fixed wall temperatures.</b> Walls are held at the thermal solution's temperatures at 5 h of the continuous run; the CFD does not feed back into the solids. A coupled conjugate run (air and solids together) would settle at different temperatures.</li>
<li><b>One speed only (3000 rpm).</b> Swirl and h grow with speed (roughly with tip speed to the 0.6–0.8 power), so the 6000 and 12000 rpm points need their own runs.</li>
<li><b>Air gap not included.</b> The rotor was grown to the bore in this mesh, so the 0.5 mm gap (and any axial flow through it between the two end spaces) is still the Taylor–Couette correlation.</li>
<li><b>Mesh.</b> Tetrahedra without boundary-layer prisms; wall functions are used, so near-wall resolution (y⁺) is uncertain, and 2 cells have skewness > 4. A prism-layer mesh would firm up the h values by an estimated ±20–30 %.</li>
<li><b>Steady RANS (k-ω SST).</b> The real end-space flow is unsteady (rotating vortices); steady RANS gives the time-averaged picture.</li>
<li><b>Partial volume.</b> The shaft bore and 10 slot-opening slivers (6 % of the internal air) were excluded because they are sealed pockets with no connection to the end spaces.</li>
<li><b>Convergence.</b> The run diverged once at iteration 653 with second-order convection and was continued from iteration 500 with first-order upwind and stronger under-relaxation (more numerical diffusion, slightly smoothed velocity peaks).</li>
</ul>
<h3>How to use it when the new FEMM model and real CAD are integrated</h3>
<ol>
<li>Replace the end-space "conducting air" with the CFD result: either a coupled conjugate run with the air as a fluid region, or per-surface CFD h with a mixed-air temperature.</li>
<li>Run the internal CFD at each load-point speed (2000 / 3000 / 6000 / 12000 rpm) with a prism-layer mesh and include the air gap.</li>
<li>Use time-step-converged settings for the long runs (60 s or smaller with 2–3 coupling iterations; see Limitations).</li>
</ol>"""))
    tr = (inputs([("Load point", "Peak torque — " + lp_line("peak_torque"))] + THERMAL_COMMON + [
            ("Outside cooling", "uniform h 6 W/m²K + radiation ε 0.7 to 40 °C (the housing barely warms in 3 min, so the CFD h map is not needed here)"),
            ("Inside", f"air gap k_eff {LP['peak_torque']['k_gap']:.3f} W/m·K (Taylor–Couette) · end-space air k_eff {LP['peak_torque']['k_inair']:.2f} W/m·K (h {LP['peak_torque']['h_endspace']:.0f} W/m²K)"),
            ("Time stepping", "implicit Euler, Δt = 1 s, 2 coupling iterations per step, 0–250 s")])
          + chart_peak()
          + inputs([(f"{NAMES[lp]}", lp_line(lp) + f" · gap k {LP[lp]['k_gap']:.3f} · end-space k {LP[lp]['k_inair']:.2f} W/m·K") for lp in ORDER if lp != "peak_torque"]
                   + [("Outside cooling", "per-face CFD h (mean 4.0 W/m²K housing, 6.2 shaft) + radiation ε 0.7, re-linearised every step"),
                      ("Time stepping", "implicit Euler; continuous Δt 60 s to 5 h then 120 s; others Δt 120 s; 1 coupling iteration; 0–12 h")]
                   + THERMAL_COMMON)
          + chart_histories()
          + "<h3>Animated temperature rise</h3>"
          + inputs([("Shows", "radial (z = 5 mm) and axial (x = 0) sections heating from 40 °C; one fixed colour scale per clip; live winding and magnet trace"),
                    ("Data", "the saved OpenFOAM solutions of the runs above — peak torque every 50 s (0–250 s), "
                             "continuous every 0.5 h to 5 h then every 1 h to 12 h; frames blend linearly between saved times"),
                    ("Peak torque run", lp_line("peak_torque")), ("Continuous run", lp_line("continuous"))])
          + vid("temp_peak_torque.mp4", "Animation: temperature rise at peak torque, 0–250 s (limit reached at 183 s)")
          + vid("temp_continuous.mp4", "Animation: temperature rise at the continuous point, 0–12 h"))
    secs.append(("transient", "Transient results", tr + """<p>The peak-torque winding rises 0.72 K/s at first, slowing to 0.47 K/s by 250 s as heat soaks into the stator. At the
long-run points the motor is still heating after 12 h (0.07–0.08 K/min): still-air cooling never brings it to a true steady state within a working day.</p>"""))
    secs.append(("distribution", "Temperature distribution", inputs([
        ("Same runs as", "Transient results (inputs listed there)"),
        ("Moment shown", " · ".join(f"{NAMES[lp]} {hrs(T_EVAL[lp])}" for lp in done) + " (limit time; cruise: end of run)"),
        ("Section pictures", "nearest saved solution: peak torque 200 s, continuous 5.0 h, peak power 10.0 h, max speed & cruise 12 h; "
                             "radial plane z = 5 mm, axial plane x = 0; colour scale per picture")]) + chart_components() + """
<p>Radial mid-plane through the stack (z = 5 mm, through the magnets) and axial mid-plane through a tooth (x = 0); each picture has its own colour scale.</p>"""
        + "".join(img(f"sec_{lp}_{ax}.png", f"{NAMES[lp]}, {'radial' if ax == 'z' else 'axial'} section") for lp in
                  ("peak_torque", "continuous", "peak_power", "max_speed", "cruise") for ax in ("z", "x"))
        + """<ul><li><b>Peak torque:</b> slot copper 125–141 °C, end turns to 152 °C, teeth ~70 °C, housing ~50 °C; ~60 K across the bobbin wall.</li>
<li><b>Continuous / peak power / max speed:</b> copper 128–140 °C, teeth 106–113 °C, housing ~100 °C; rotor and magnets soaked to 92–100 °C by
the end-space air and the air gap, hottest at the rotor ends.</li><li><b>Cruise:</b> everything below 90 °C after 12 h.</li></ul>"""))
    heat_anim = ("<h3>Animated heat transfer</h3>"
        + inputs([("Shows", "heat flow between the parts through time (arrow width ∝ watts) and the running balance generated / leaving / stored"),
                  ("Data", "OpenFOAM wallHeatFlux integrated on every region interface at each saved solution (source side); copper loss from the "
                           "winding mean temperature at that moment; frames blend between saved times"),
                  ("Runs", "same as Transient results (peak torque: saved every 50 s; continuous: every 0.5–1 h)")])
        + vid("heat_peak_torque.mp4", "Animation: heat transfer at peak torque, 0–250 s")
        + vid("heat_continuous.mp4", "Animation: heat transfer at the continuous point, 0–12 h"))
    secs.append(("views3d", "3D views of heat transfer inside and outside", inputs([
        ("Shows", "the motor's parts with one quarter cut away (x > 0, y > 0), coloured by temperature; air streamlines coloured by air temperature on the same scale"),
        ("Data", "full 3D OpenFOAM fields: thermal model (continuous at 5 h; peak torque at 50–250 s), external natural-convection CFD, internal air CFD at 3000 rpm"),
        ("Note", "the external CFD skin was held at 100 °C, which matches the continuous point at 5 h (housing ≈ 100 °C); the peak-torque views show the solids only")])
        + img("3d_continuous_cut.png", "Continuous at 5 h: temperature inside the motor (quarter cut away). The end turns are hottest; the heat soaks into teeth, housing and rotor")
        + img("3d_continuous_inside.png", "Continuous at 5 h: the end-space air swirling around the rotor ends, between the hot end turns and the housing")
        + vid("3d_turntable.mp4", "Animation: 360° turn around the cut-away motor with the internal air swirl (continuous, 5 h)")
        + img("3d_continuous_ext.png", "Continuous at 5 h: the warm plume rising from the housing")
        + "<h3>Peak torque: how the motor heats up in 3D</h3>"
        + vid("3d_peak_torque.mp4", "Animation: peak torque 45 N·m @ 2000 rpm, 3D cut-away at 50, 100, 150, 200 and 250 s (cross-faded between saved solutions); fixed scale 40–190 °C")
        + img("3d_peak_200.png", "Peak torque at 200 s: the copper end turns are at 150–180 °C while the rest of the motor is still at 40–70 °C — the burst heats only the winding")))
    secs.append(("heatpaths", "Losses and heat paths", inputs([
        ("Same runs as", "Transient results"),
        ("Generated heat", "copper at the winding's actual mean temperature at that moment; other sources as the load point"),
        ("Heat flows", "OpenFOAM wallHeatFlux integrated over every region interface (source side), at the saved time named in each column"),
        ("Diagram", "continuous point at 5.0 h (18 000 s); arrow width ∝ watts")]) + gen_table() + hp_svg + path_table() + """
<ul><li><b>The end-space air carries as much heat as the bobbin wall</b>; that route depends on the end-space correlation, which the internal CFD checks.</li>
<li><b>The rotor is heated by the air</b> (33–89 W in), which is why the magnets become the long-run limit.</li>
<li><b>The motor is still storing heat</b> after 5–10 h; airflow over the fins would shorten the soak and raise the continuous rating sharply.</li></ul>
<p class="note">Interface flows are reported on the side the heat leaves; with one coupling iteration per 2-minute step the two sides agree within ~5–15 %.</p>""" + heat_anim))
    secs.append(("detailed", "Detailed real-geometry model", ("<p>Results available in results/detailed.</p>" if det else "") + """
<p>A second model replaces the simplifications with the real CAD: 12 swept Ø2.9 mm copper coils with 0.05 mm enamel, 24 PA66-GF30 bobbin halves,
impregnation resin filling every gap (0.105 mm between turns), 3 busbar plates, 6 link straps, 3 terminal bars and 24 welded lead joints, each
conductor heated by its own Joule loss at its own temperature. The scripts are ready (<code>build_mesh_detailed.py</code>);
the run is <b>deferred</b> until the new FEMM loss model and the final real CAD are integrated. Note: the full-detail geometry step needs more than
the ~6 GB this laptop can spare alongside other work (it exceeded memory once), so it should run alone, or with the bobbins simplified to plain
walls of the same thickness and material.</p>"""))
    secs.append(("limits", "Limitations and recommendations", """
<ul><li><b>Isotropic winding k (1.0 W/m·K)</b> in the baseline: conservative for the end-winding hot spot (the detailed model resolves the real wire).</li>
<li><b>No AC copper / PWM loss</b>: high-speed results optimistic.</li><li><b>End-space air as effective conductivity</b> (correlation): checked by the internal CFD.</li>
<li><b>Assumed contacts</b> (bobbin 176, shrink fit 1300, glue 2000 W/m²K) — the bobbin value controls the copper-to-iron path; confirm by test.</li>
<li><b>Time-step sensitivity of the long runs.</b> With one coupling iteration per step, going from 60 s to 120 s steps lowered the heating
rate by ~32 % at the 5 h restart of the continuous run: results computed with 120 s steps (peak power, max speed, cruise, continuous after 5 h)
under-predict temperatures. Peak torque (1 s steps, 2 iterations) is not affected.</li>
<li><b>Internal air as a conducting solid</b> over-cools the end windings (~5× the CFD heat flow) — see "Internal airflow: implications".</li>
<li><b>Natural convection only</b>, motor standing free (no mounting-face conduction, no cable cooling): conservative.</li></ul>
<h3>Recommendations</h3><ol>
<li><b>Peak torque:</b> limit 45 N·m bursts to ~2.5 min from cold (≈ 20 % margin) via a thermal model in the controller; a thinner or thermally
conductive bobbin (1–2 W/m·K) or potting the slots would lengthen the burst most, as the bobbin wall carries a ~60 K drop.</li>
<li><b>Magnet limit:</b> confirm where 100 °C comes from. If it is the adhesive or bearing grease, a 130–150 °C rated choice moves every long-run
limit to the winding (continuous 7.7 h; peak power and cruise unlimited in 12 h).</li>
<li><b>Cooling:</b> still-air cooling is the bottleneck (4 W/m²K). Ram air at vehicle speed (typically 20–40 W/m²K on the fins) or a small fan would
raise the continuous rating sharply; worth a follow-up CFD run.</li>
<li><b>End windings:</b> potting the end turns to the housing would give the 120–130 W now crossing the end-space air a direct metal path.</li>
<li><b>Validate:</b> thermocouples in the rear end winding and on the housing, magnet temperature by IR or telemetry, one peak and one continuous
test; use them to calibrate the bobbin and shrink-fit contacts.</li></ol>"""))
    secs.append(("appendix", "Appendix: files and how to rerun", table(["File", "Does"], [
        ["scripts/build_mesh.py", "CAD → conformal multi-region mesh (--solids-only, --air-only)"], ["scripts/build_mesh_detailed.py", "real coils, bobbins, resin, busbars → mesh"],
        ["scripts/loadpoints.py", "load points → loadpoints.json"], ["scripts/make_case.py", "one transient case per load point"],
        ["scripts/run_case.sh", "generate, decompose, run on 4 cores"], ["scripts/air_case.sh, inair_cfd.sh", "external and internal air CFD"],
        ["scripts/map_h.py", "CFD wall heat flux → h per face"], ["scripts/heatpaths.sh, slices.sh", "heat-path audit, section planes"],
        ["scripts/pipeline.sh", "everything in order, resumable (tmux)"], ["scripts/post.py, make_report.py", "results summary, this report"]])))

    nav = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t, _ in secs)
    body = "".join(f'<section id="{i}"><h2>{esc(t)}</h2>{c}</section>' for i, t, c in secs)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    css = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--line:#e2e2e2;--card:#f6f7f9;--accent:#1f4e8c;--todo:#a15c00}
@media (prefers-color-scheme:dark){:root{--bg:#141517;--fg:#e8e8e8;--muted:#a0a4aa;--line:#2c2f33;--card:#1d1f22;--accent:#7fb0ff;--todo:#ffb74d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{padding:40px 16px 24px;max-width:980px;margin:auto;border-bottom:1px solid var(--line)}h1{margin:0 0 6px;font-size:28px}
.meta{color:var(--muted);font-size:13px}nav{max-width:980px;margin:auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;border-bottom:1px solid var(--line)}
nav a{color:var(--accent);text-decoration:none}main{max-width:980px;margin:auto;padding:0 16px 60px}section{padding-top:22px}
h2{font-size:21px;border-left:4px solid var(--accent);padding-left:10px;margin:18px 0 10px}h3{font-size:16px;margin:18px 0 6px}
.lead{font-size:16px}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--card);font-weight:600}
figure{margin:14px 0}figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figure video{display:block;max-width:100%;max-height:640px;margin:auto;border-radius:6px;background:#000}figure.chart svg{width:100%;height:auto;background:#fff;border-radius:6px}figcaption{color:var(--muted);font-size:12.5px;margin-top:4px}
.diagram{width:100%;height:auto;background:var(--card);border-radius:8px;margin:12px 0}.diagram .node{fill:var(--bg);stroke:#999;stroke-width:1.2}
.diagram .accent{fill:rgba(31,78,140,.10);stroke:var(--accent);stroke-width:2}.diagram .nname{font-weight:600;font-size:13px;fill:var(--fg)}
.diagram .nsub{font-size:11.5px;fill:var(--muted)}.diagram .lbl{font-weight:600;font-size:12px;fill:var(--fg)}
.eq{background:var(--card);border-radius:6px;padding:8px 12px;margin:8px 0;font-family:Cambria,Georgia,serif;font-size:15px;overflow-x:auto}
.inputs{border:1px solid var(--line);border-left:4px solid #8a8f98;border-radius:6px;background:var(--card);padding:6px 10px;margin:14px 0 6px;font-size:12.5px}
.inputs .ih{font-weight:700;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:2px}
.inputs table{display:table;margin:0;font-size:12.5px}.inputs th{background:none;width:150px;color:var(--muted);font-weight:600;border:0;padding:2px 8px 2px 0}
.inputs td{border:0;padding:2px 0}
.card{border:1px solid var(--line);border-radius:8px;padding:4px 14px 8px;margin:14px 0;background:var(--bg)}.card h3{margin:10px 0 4px}.card table{display:table;font-size:13px}.card th{width:170px;background:none;color:var(--muted)}.card ul{margin:0;padding-left:18px}
.note{color:var(--muted);font-size:13px}.todo{color:var(--todo);font-style:italic}code{background:var(--card);padding:1px 4px;border-radius:4px}
@media print{nav{display:none}section{break-inside:avoid-page}}"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Motor_65 Thermal CFD</title><style>{css}</style></head><body>
<header><h1>Motor_65 Thermal Transient CFD Report</h1><div class="meta">12-slot / 10-pole spoke-ferrite PMSM · natural convection, 40 °C ambient ·
OpenFOAM 12 + gmsh · generated {stamp}</div></header><nav>{nav}</nav><main>{body}</main></body></html>"""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "Motor65_Thermal_CFD_Report.html")
    open(path, "w", encoding="utf-8").write(page)
    print(f"wrote {path}  ({os.path.getsize(path)/1e6:.1f} MB)")


build()
