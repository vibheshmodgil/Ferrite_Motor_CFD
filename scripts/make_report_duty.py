"""Design9795_1 vehicle-duty thermal CFD report (slide-3 points duty1..duty5).

    .venv/Scripts/python -I scripts/make_report_duty.py   # -> Report/Design9795_Duty_Thermal_CFD_Report.html

Self-contained HTML (charts as inline SVG, sections as embedded PNG). Every section reads its inputs if they exist
and otherwise prints a 'pending' note, so it can be rerun at any stage. Inputs:
  loadpoints.json                    duty1..5: torque, rpm, Q{winding_100C, stator, rotor, bearings, inair, ...}, k_gap,
                                     k_inair, h_endspace, end_time, dt, write
  results/losses_9795.json           duty1..5 -> {source: {loss: W}} (e.g. femm / mcad); other top-level keys = audit
  results/energy_test.json           optional: {"after": {"Q_W", "t_s", "expected_kJ", "stored_kJ"}, "long_run": {...}}
  results/<lp>/postProcessing        OpenFOAM monitor histories (T_<region>, Tavg_<region>)
  results/<lp>/heatflow_<t>.txt      heatpaths.sh output
  results/<lp>/slices_<t>/*.vtk      slices.sh output
  scripts/make_case.py, loadpoints.py  model constants are read from the source, so the text stays true
  ../OUTPUT/femm_em/eff.json         old v7 loss map, for the before/after loss comparison
  results/femm_duty/                 FEMM duty EM study: femm_duty.json, dq_limits.json, field_stats.json, *.png, *.mp4
  results/anim_duty/, figs_duty/     duty_visuals.sh output (ext air, temp/heat animations, inside air, 3D)
  results/inair_<lp>/                internal-air CFD per point (CFD agent)
  results/detailed/<lp>, results/detailed_vs_baseline.md   detailed-geometry runs (DETAIL agent)
"""
import ast, base64, datetime, glob, html, io, json, math, mimetypes, os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I drops the script dir
from heat_budget import budget, hf_times

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES, OUT = os.path.join(ROOT, "results"), os.path.join(ROOT, "Report")
K, LIM_W, LIM_M = 273.15, 155.0, 100.0


def jload(p):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return None


LPALL = jload(os.path.join(ROOT, "loadpoints.json")) or {}
LOSS = jload(os.path.join(RES, "losses_9795.json")) or {}
ETEST = jload(os.path.join(RES, "energy_test.json")) or {}
HCFD = jload(os.path.join(RES, "h_cfd.json")) or {}
EFF = jload(os.path.join(ROOT, "..", "OUTPUT", "femm_em", "eff.json"))
FD, AD, FG = (os.path.join(RES, d) for d in ("femm_duty", "anim_duty", "figs_duty"))
FDJ = jload(os.path.join(FD, "femm_duty.json")) or {}
DQ = jload(os.path.join(FD, "dq_limits.json")) or {}
FSTAT = jload(os.path.join(FD, "field_stats.json"))
FOCUS = ("duty1", "duty2", "duty3", "duty4", "duty5")  # points with animations and observations
EMF = ("duty1", "duty4")             # points with FEMM field figures
DET = ("duty1", "duty4")             # points with detailed-geometry runs
# internal-air source per point and how it was obtained
INAIR = {"duty1": ("duty1", ""),
         "duty3": ("duty1", "no separate run: the duty1 internal-air field (1782 rpm) is reused; at 3637 rpm the velocities scale with "
                            "speed (×2.04) and the flow pattern is the same"),
         "duty5": ("duty1", "no separate run: the duty1 internal-air field (1782 rpm) is reused; at 1612 rpm the velocities scale with "
                            "speed (×0.90) and the flow pattern is the same"),
         "duty2": ("duty1", "no separate run: the duty1 internal-air field (1782 rpm) is reused; at 2550 rpm the velocities scale with "
                            "speed (×1.43) and the flow pattern is the same"),
         "duty4": ("duty4", "approximate solution: upwind convection, low relaxation, residuals ~1e-3 (did not converge further at "
                            "9339 rpm); use for the flow pattern, not for exact velocities")}
RUN_NOTE = {"duty1": "the run ended at 477 of 480 s when the disk filled; 477 s is treated as the final time "
                     "(the 5 min target was already passed)"}

# slide 3: name, rpm, N.m, target min, U666 test, U666, Spoke (Ferrite) reference [min]
DUTY = {
    "duty1": ("Grade 12.3 % @ 23 km/h", 1782, 37.0, 5, 4 + 20 / 60, 2 + 43 / 60, 4 + 33 / 60),
    "duty2": ("Grade 17.6 % @ 16 km/h", 2550, 26.3, 15, 14 + 48 / 60, 8, 17 + 35 / 60),
    "duty3": ("Grade 25 % @ 11 km/h", 3637, 20.0, 30, 31 + 42 / 60, 16, 38 + 25 / 60),
    "duty4": ("Flat road 60 km/h", 9339, 3.24, 45, 60, 30, 22 + 40 / 60),
    "duty5": ("Grade 7 % @ 30 km/h", 1612, 12.43, 45, None, 80, 180),
}
ORDER = list(DUTY)
COL = dict(zip(ORDER, ("#1f4e8c", "#c2185b", "#2e7d32", "#ef6c00", "#6a1b9a")))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.8})


# ---------------------------------------------------------------- helpers (from make_report.py)
def esc(s):
    return html.escape(str(s))


def todo(msg):
    return f'<p class="todo">Pending: {esc(msg)}</p>'


def inputs(rows, title="Simulation inputs"):
    r = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f'<div class="inputs"><div class="ih">{esc(title)}</div><table>{r}</table></div>'


def svg(fig, caption):
    buf = io.StringIO(); fig.savefig(buf, format="svg", bbox_inches="tight"); plt.close(fig)
    s = buf.getvalue(); s = s[s.index("<svg"):]
    return f'<figure class="chart">{s}<figcaption>{esc(caption)}</figcaption></figure>'


ASSETS = None   # set by --site: media are copied to this folder and linked instead of embedded


def asset(src_path, name, data=None):
    """Copy a file (or write bytes) into ASSETS; return its relative URL."""
    import shutil
    dst = os.path.join(ASSETS, name)
    if data is not None:
        open(dst, "wb").write(data)
    elif not (os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src_path)):
        shutil.copyfile(src_path, dst)
    return "assets/" + name


def png(fig, caption):
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    if ASSETS:
        import hashlib
        d = buf.getvalue()
        return (f'<figure><img loading="lazy" src="{asset(None, "fig_" + hashlib.sha1(d).hexdigest()[:12] + ".png", d)}" '
                f'alt="{esc(caption)}"><figcaption>{esc(caption)}</figcaption></figure>')
    return (f'<figure><img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="{esc(caption)}">'
            f'<figcaption>{esc(caption)}</figcaption></figure>')


def table(head, rows, cap=""):
    """Data table; build() numbers every one ("Table N. cap") in document order."""
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table data-cap="{esc(cap)}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


VID_MAX = 0.5e6     # bytes per embedded video; larger ones are re-encoded once into <dir>/small/ (originals untouched)
IMG_MAX = 3e5       # bytes per embedded still; larger PNGs are embedded as a cached JPEG copy in <dir>/small/


def small_img(p):
    if os.path.getsize(p) <= IMG_MAX or not p.endswith(".png"):
        return p
    out = os.path.join(os.path.dirname(p), "small", os.path.basename(p)[:-4] + ".jpg")
    if not (os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(p)):
        from PIL import Image
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im = Image.open(p)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGB", im.size, "white"); bg.paste(im, mask=im.split()[-1]); im = bg
        im.convert("RGB").save(out, quality=85, optimize=True)
    return out


def small_mp4(p):
    """Cached 720 px H.264 copy of a large mp4 for embedding; steps down quality until it fits VID_MAX."""
    if os.path.getsize(p) <= VID_MAX:
        return p
    out = os.path.join(os.path.dirname(p), "small", os.path.basename(p))
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(p) and os.path.getsize(out) <= VID_MAX:
        return out   # ponytail: a copy that can never reach VID_MAX is re-encoded on every build; add a marker if that happens
    import subprocess, imageio_ffmpeg
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for w, crf in ((720, 30), (640, 34), (540, 38)):
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", p, "-vf", f"scale={w}:-2",
                        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-an", out], check=True)
        if os.path.getsize(out) <= VID_MAX:
            break
    return out


def media(p, caption):
    """Embed an image or mp4 (base64, so the report stays one file), or a pending note if it does not exist yet."""
    if not os.path.exists(p):
        return todo(f"{rel(p)} not available yet.")
    o, p = p, (small_mp4(p) if p.endswith(".mp4") else small_img(p))
    if ASSETS:
        src = asset(p, rel(os.path.dirname(o)).replace("/", "_").replace(".", "") + "_" + os.path.basename(p))
        tag = (f'<video loop muted playsinline controls preload="metadata" data-auto src="{src}"></video>' if p.endswith(".mp4")
               else f'<img loading="lazy" src="{src}" alt="{esc(caption)}">')
        return f'<figure>{tag}<figcaption>{esc(caption)}</figcaption></figure>'
    b = base64.b64encode(open(p, "rb").read()).decode()
    tag = (f'<video autoplay loop muted playsinline controls src="data:video/mp4;base64,{b}"></video>' if p.endswith(".mp4")
           else f'<img src="data:{mimetypes.guess_type(p)[0] or "image/png"};base64,{b}" alt="{esc(caption)}">')
    return f'<figure>{tag}<figcaption>{esc(caption)}</figcaption></figure>'


def flat_rows(obj, pre=""):
    """Nested JSON -> [key path, value] rows."""
    rows = []
    if isinstance(obj, dict):
        for k, x in obj.items():
            rows += flat_rows(x, f"{pre} · {k}" if pre else str(k))
    elif isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        rows += [[esc(pre), esc(" · ".join(f"{k}: {y}" for k, y in x.items()))] for x in obj]
    else:
        rows.append([esc(pre), esc(f"{obj:.4g}" if isinstance(obj, float) else obj)])
    return rows


def md2html(path):
    """Minimal Markdown (#, | tables |, - lists, ![](img), **b**, `code`) -> HTML; images embedded.
    ponytail: covers what the agents' .md files use; add a real parser if they grow nested lists or links."""
    d, out, tab, lst = os.path.dirname(path), [], [], False
    inl = lambda s: re.sub(r"`(.+?)`", r"<code>\1</code>", re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s)))
    for s in [l.strip() for l in open(path, encoding="utf-8").read().splitlines()] + [""]:
        if s.startswith("|"):
            if not set(s) <= set("|-: "):
                tab.append([inl(c.strip()) for c in s.strip("|").split("|")])
            continue
        if tab:
            out.append(table(tab[0], tab[1:])); tab = []
        if lst and not s.startswith("- "):
            out.append("</ul>"); lst = False
        if m := re.match(r"!\[(.*?)\]\((.+?)\)", s):
            out.append(media(os.path.join(d, m[2]), m[1]))
        elif m := re.match(r"#{1,6}\s+(.*)", s):
            out.append(f"<h4>{inl(m[1])}</h4>")
        elif s.startswith("- "):
            out.append(("" if lst else "<ul>") + f"<li>{inl(s[2:])}</li>"); lst = True
        elif s:
            out.append(f"<p>{inl(s)}</p>")
    return "".join(out)


def mmss(m):
    if m is None:
        return "—"
    if m >= 120:
        return f"{m/60:.1f} h" if m >= 600 else f"{m:.0f} min"
    s = round(m * 60)
    return f"{s // 60} min {s % 60:02d} s"


def hist(lp, region, kind="T", fn=None):
    if fn is None and region == "winding" and lp.startswith("detailed/"):   # detailed runs monitor the coil in the copper region
        region, fn = "copper", f"{kind}_coil"
    base = os.path.join(RES, lp, "postProcessing", region, fn or f"{kind}_{region}")
    if not os.path.isdir(base):
        return None
    try:
        segs = [np.atleast_2d(np.loadtxt(os.path.join(base, t, "volFieldValue.dat"), comments="#", ndmin=2))
                for t in sorted(os.listdir(base), key=float)]
        segs = [s for s in segs if s.size]  # ponytail: skip empty/truncated restart segments (disk-full, mid-copy)
        if not segs:
            return None
        a = np.vstack(segs)
    except (OSError, ValueError):
        return None
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    return a[:, 0], a[:, 1] - K


def at(lp, region, t0, kind="T"):
    h = hist(lp, region, kind)
    return None if h is None else float(np.interp(t0, *h))


def cross(t, T, lim):
    i = int(np.argmax(T >= lim))
    if T[i] < lim:
        return None
    return t[i] if i == 0 else t[i - 1] + (lim - T[i - 1]) * (t[i] - t[i - 1]) / (T[i] - T[i - 1])


def heatflow(lp, t):
    try:
        return {(r, p): float(q) for r, p, q in (l.split() for l in open(os.path.join(RES, lp, f"heatflow_{t}.txt")) if l.strip())}
    except (OSError, ValueError):
        return None


def saved_times(lp, pattern):
    return sorted(int(f.split("_")[-1].split(".")[0]) for f in glob.glob(os.path.join(RES, lp, pattern))
                  if f.split("_")[-1].split(".")[0].isdigit())


def consts(path):
    """Top-level constant assignments of a script, evaluated without running it (load-point refs -> 'per point')."""
    class Stub(dict):
        def get(self, k, d=None): return d
        def __missing__(self, k): return "per load point"
    ns = {"math": math, "os": os, "LP": Stub(), "lp": "duty", "frozenset": frozenset, "round": round, "float": float}
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except OSError:
        return {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            names = [t] if isinstance(t, ast.Name) else list(getattr(t, "elts", []))
            if not names or not all(isinstance(n, ast.Name) for n in names):
                continue
            try:
                v = eval(compile(ast.Expression(node.value), path, "eval"), ns)
                ns.update({names[0].id: v} if isinstance(t, ast.Name) else dict(zip((n.id for n in names), v)))
            except Exception:
                continue
    return ns


MC = consts(os.path.join(ROOT, "scripts", "make_case.py"))
LPS = consts(os.path.join(ROOT, "scripts", "loadpoints.py"))


def c(ns, k, fmt="{}"):
    return fmt.format(ns[k]) if k in ns else "?"


# ---------------------------------------------------------------- results per point
def result(lp):
    w, m = hist(lp, "winding"), hist(lp, "magnets")
    if w is None or m is None:
        return None
    tw, tm = cross(*w, LIM_W), cross(*m, LIM_M)
    lims = [(v, k) for v, k in ((tw, "winding"), (tm, "magnets")) if v is not None]
    tl, by = min(lims) if lims else (None, None)
    done = os.path.exists(os.path.join(RES, lp, "done")) or lp in RUN_NOTE   # RUN_NOTE points ended early but are final
    return dict(tw=tw, tm=tm, t_lim=tl, by=by, t_end=float(w[0][-1]), Tw_end=float(w[1][-1]), Tm_end=float(m[1][-1]), done=done)


# user rule: where a detailed (real-coil) run exists it is THE result; the baseline stays only as the validation reference
SRC = {lp: (f"detailed/{lp}" if lp in DET and os.path.isdir(os.path.join(RES, "detailed", lp, "postProcessing")) else lp) for lp in ORDER}
IS_DET = lambda lp: SRC[lp] != lp
MODEL = lambda lp: "detailed model (real coils, resin, bobbins, busbars)" if IS_DET(lp) else "baseline (simplified winding) model"
DET_NOTE = {"duty1": "detailed model: saved fields (section planes, heat flows) exist only up to 420 s",
            "duty4": "detailed model: section planes only at 900 / 1800 / 2700 s and one heat flow before the cut (900 s); its run energy "
                     "balance is −1.7 to −2.1 %, outside the 1 % goal (heat slightly lost, temperatures slightly low)"}
R = {lp: result(SRC[lp]) for lp in ORDER}
HAVE = [lp for lp in ORDER if R[lp]]


def verdict(lp):
    r, tgt = R[lp], DUTY[lp][3]
    if not r:
        return "<i>pending</i>"
    if r["t_lim"] is None:
        ok = r["t_end"] / 60 >= tgt
        tag = "" if r["done"] else " (run in progress)"
        return (f'<b class="ok">meets</b> — no limit in {mmss(r["t_end"]/60)}{tag}' if ok
                else f'<i>open</i> — no limit yet at {mmss(r["t_end"]/60)}{tag}')
    m = r["t_lim"] / 60
    return (f'<b class="ok">meets</b> (+{(m/tgt-1)*100:.0f} %)' if m >= tgt
            else f'<b class="bad">short</b> ({(m/tgt-1)*100:.0f} %)')


# ---------------------------------------------------------------- losses
def Q(lp):
    return (LPALL.get(lp) or {}).get("Q")


def groups(q):
    cu = q.get("winding_100C", 0) + q.get("coil", 0) + q.get("winding_ac", 0)
    fe = q.get("stator", 0) + q.get("rotor", 0)
    mech = q.get("bearings", 0) + q.get("inair", 0)
    rest = sum(v for k, v in q.items() if isinstance(v, (int, float))) - cu - fe - mech   # magnets etc.
    return cu, fe, mech, rest


def v7(lp):
    """Old v7 FEMM map (DC copper at 100 C, scaled no-load iron) at the duty point, bilinear like loadpoints.py."""
    if not EFF:
        return None
    _, n, T = DUTY[lp][:3]
    ts, ns = EFF["torques"], EFF["speeds"]
    i = min(max(np.searchsorted(ts, T) - 1, 0), len(ts) - 2); j = min(max(np.searchsorted(ns, n) - 1, 0), len(ns) - 2)
    u, v = (T - ts[i]) / (ts[i + 1] - ts[i]), (n - ns[j]) / (ns[j + 1] - ns[j])
    out = {}
    for key in ("pcu", "pfe", "pmech"):
        a = np.array(EFF[key], dtype=float)
        out[key] = sum(wk * a[i + di, j + dj] for (di, dj), wk in
                       (((0, 0), (1 - u) * (1 - v)), ((1, 0), u * (1 - v)), ((0, 1), (1 - u) * v), ((1, 1), u * v)) if wk > 1e-12)
    return out


def chart_losses():
    pts = [lp for lp in ORDER if Q(lp)]
    if not pts:
        return todo("Design9795_1 losses for duty1..duty5 are not in loadpoints.json yet (LOSS agent).")
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    parts = [("Copper (AC, ref. temp.)", 0, "#3a78c2"), ("Iron, stator + rotor", 1, "#e07b39"),
             ("Bearings + windage", 2, "#3fae7a"), ("Other (magnets, ...)", 3, "#9e9e9e")]
    left = np.zeros(len(pts))
    for name, k, col in parts:
        v = np.array([groups(Q(lp))[k] for lp in pts])
        if v.any():
            ax.barh(range(len(pts)), v, left=left, color=col, label=name); left += v
    for i in range(len(pts)):
        ax.text(left[i] + 6, i, f"{left[i]:.0f} W", va="center")
    ax.set_yticks(range(len(pts)), [f"{lp[-1]}. {DUTY[lp][0]} — {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]}" for lp in pts])
    ax.invert_yaxis(); ax.set_xlabel("heat generated [W]"); ax.grid(axis="y", visible=False)
    ax.legend(ncol=2, loc="lower right", frameon=False, fontsize=9); ax.set_xlim(0, left.max() * 1.18)
    top = pts[int(np.argmax(left))]
    ax.set_title(f"{DUTY[top][0]} dissipates the most heat ({left.max():.0f} W)", loc="left", fontweight="bold")
    return svg(fig, "Heat sources per duty point as applied in the CFD (loadpoints.json, Design9795_1 FEMM model).")


def loss_table():
    rows = []
    for lp in ORDER:
        q, old, src = Q(lp), v7(lp), LOSS.get(lp) or {}
        if isinstance(src, dict) and src and all(isinstance(v, (int, float)) for v in src.values()):
            src = {"femm": src}
        def total(d):
            if not isinstance(d, dict): return None
            for k in d:
                if k.lower().startswith("total") and isinstance(d[k], (int, float)): return d[k]
            vals = [v for v in d.values() if isinstance(v, (int, float))]
            return sum(vals) if vals else None
        mc = next((total(v) for k, v in src.items() if "mcad" in k.lower() or "motor" in k.lower()), None)
        rows.append([f"{lp[-1]}. {DUTY[lp][0]}", f"{DUTY[lp][2]:g} N·m @ {DUTY[lp][1]}",
                     " · ".join(f"{a} {b:.0f}" for a, b in zip(("Cu", "Fe", "mech", "other"), groups(q)) if b > 0.5) + f" = <b>{sum(groups(q)):.0f}</b>" if q else "<i>pending</i>",
                     f"{mc:.0f}" if mc is not None else "<i>pending</i>",
                     f"Cu {old['pcu']:.0f} · Fe {old['pfe']:.0f} · mech {old['pmech']:.0f} = <b>{sum(old.values()):.0f}</b>"
                     if old and not any(math.isnan(x) for x in old.values()) else ("outside v7 map" if old else "eff.json not found")])
    out = table(["Point", "Operating point", "Design9795_1 FEMM, as applied in CFD (W)", "Motor-CAD map total (W)",
                 "Old v7 map (W, DC Cu @ 100 °C)"], rows)
    # every source / loss the LOSS agent wrote, as-is
    detail = []
    for lp in ORDER:
        src = LOSS.get(lp)
        if isinstance(src, dict) and src:
            if all(isinstance(v, (int, float)) for v in src.values()):
                src = {"femm": src}
            for s, d in src.items():
                if isinstance(d, dict):
                    detail.append([lp, esc(s), " · ".join(f"{esc(k)} {v:.1f}" if isinstance(v, (int, float)) else f"{esc(k)} {esc(v)}"
                                                           for k, v in d.items())])
    out += (table(["Point", "Source", "Values (results/losses_9795.json)"], detail) if detail
            else todo("results/losses_9795.json (FEMM Design9795_1 vs Motor-CAD per loss component) not written yet."))
    return out


def audit_table():
    items = {k: v for k, v in LOSS.items() if not k.startswith("duty")}
    if not items:
        return todo("materials / factors audit (non-duty keys of results/losses_9795.json) not written yet.")
    return table(["Item", "Value / source"], flat_rows(items))


# ---------------------------------------------------------------- transient charts
T_STOP = 180.0   # user rule: every temperature-vs-time chart / animation ends when the winding maximum reaches this


def wmon(src, kind="T"):
    """(region, file) of the winding monitor: the detailed runs record the coil inside the merged copper region."""
    return ("copper", f"{kind}_coil") if src.startswith("detailed/") else ("winding", None)


def t_stop(src, region=None, fn=None):
    """Time the winding (or given region) maximum first reaches T_STOP, else the end of the history."""
    region, fn = (region, fn) if region else wmon(src)
    h = hist(src, region, fn=fn)
    return None if h is None else (cross(*h, T_STOP) or float(h[0][-1]))


def upto(h, tend):
    """History cut at tend (the value at tend is interpolated so the curve ends exactly there)."""
    if h is None or tend is None:
        return h
    t, T = h
    m = t <= tend
    if m.any() and t[m][-1] < tend <= t[-1]:
        return np.append(t[m], tend), np.append(T[m], np.interp(tend, t, T))
    return t[m], T[m]


def events(lp):
    """(t_stop, [(label, t or None, {winding max/mean, magnet max/mean at t})], histories) for the 100 °C magnet and 155 °C
    winding events; lp may be a baseline point or detailed/<point>."""
    te = t_stop(lp)
    (wr, wf), (ar, af) = wmon(lp, "T"), wmon(lp, "Tavg")
    H = {"wmax": upto(hist(lp, wr, fn=wf), te), "wmean": upto(hist(lp, ar, "Tavg", fn=af), te),
         "mmax": upto(hist(lp, "magnets"), te), "mmean": upto(hist(lp, "magnets", "Tavg"), te)}
    out = []
    for lab, key, lim in (("Magnets reach 100 °C", "mmax", LIM_M), ("Winding reaches 155 °C", "wmax", LIM_W)):
        t = cross(*H[key], lim) if H[key] is not None and len(H[key][0]) else None
        out.append((lab, t, {k: (float(np.interp(t, *h)) if (t is not None and h is not None) else None) for k, h in H.items()}))
    return te, out, H


def chart_transient(pts=None):
    pts = [lp for lp in (pts or HAVE) if R[lp]]
    if not pts:
        return todo("no OpenFOAM histories for this point yet.")
    fig, axs = plt.subplots(len(pts), 1, figsize=(8.6, 3.0 * len(pts) + (0.4 if len(pts) == 1 else 0)), squeeze=False)
    for ax, lp in zip(axs[:, 0], pts):
        name, _, _, tgt, u_test, u666, spoke = DUTY[lp]
        te, ev, H = events(SRC[lp])
        for key, col, ls, lw, lab in (("wmax", COL[lp], "-", 2.0, "winding max"), ("wmean", COL[lp], "--", 1.2, "winding mean"),
                                      ("mmax", "#2e7d32", "-", 1.8, "magnet max"), ("mmean", "#2e7d32", ":", 1.6, "magnet mean")):
            if H[key] is not None:
                ax.plot(H[key][0] / 60, H[key][1], color=col, ls=ls, lw=lw, label=lab)
        hh = upto(hist(SRC[lp], "housing"), te)
        if hh is not None:
            ax.plot(hh[0] / 60, hh[1], color="#999", lw=1.0, label="housing max")
        ax.axhline(LIM_W, color="#c62828", ls="--", lw=1); ax.axhline(LIM_M, color="#c62828", ls=":", lw=1)
        for t, lab, y in ((tgt, f" target {tgt} min", 42), (u_test, f" U666 test {mmss(u_test)}", 52)):
            if t and t * 60 <= te:
                ax.axvline(t, color="#555" if y == 42 else "#8d6e63", ls="-.", lw=1, alpha=.7); ax.text(t, y, lab, fontsize=8, color="#555")
        for k, (lab, t, v) in enumerate(ev):
            if t is None:
                continue
            y = LIM_M if "Magnets" in lab else LIM_W
            ax.plot(t / 60, y, "o", color="#c62828", zorder=5)
            txt = (f"magnets 100 °C @ {mmss(t/60)}\nwinding {v['wmax']:.0f} max / {v['wmean']:.0f} mean" if "Magnets" in lab
                   else f"winding 155 °C @ {mmss(t/60)}\nmagnet {v['mmax']:.0f} max / {v['mmean']:.0f} mean" if v["mmean"] is not None
                   else f"winding 155 °C @ {mmss(t/60)}\nmagnet {v['mmax']:.0f} max")
            ax.annotate(txt, (t / 60, y), xytext=(-150, 14) if "Winding" in lab else (8, -34), textcoords="offset points",
                        fontsize=8, color="#c62828", fontweight="bold", arrowprops=dict(arrowstyle="-", color="#c62828", lw=0.7))
        cut = "winding max reaches 180 °C" if cross(*hist(SRC[lp], "winding"), T_STOP) else "end of run"
        ax.set_xlim(0, te / 60 * 1.02); ax.set_ylim(35, 190)
        ax.set_title(f"{lp[-1]}. {name}, {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]} rpm, {'detailed' if IS_DET(lp) else 'baseline'} model — shown to {mmss(te/60)} ({cut})"
                     + (f"; target {tgt} min is beyond" if tgt * 60 > te else ""), loc="left", fontweight="bold", fontsize=9.5)
        ax.set_ylabel("°C")
    axs[0, 0].legend(frameon=False, fontsize=8, ncol=5, loc="upper left", bbox_to_anchor=(0, 1.36))
    axs[-1, 0].set_xlabel("time from 40 °C cold start [min]")
    fig.tight_layout()
    return svg(fig, "OpenFOAM monitor histories, each cut where the winding maximum reaches 180 °C (or at the end of the run). Point colour: winding "
                    "max (solid) and mean (dashed); green: magnet max (solid) and mean (dotted); grey: housing. Red lines: 155 °C winding, "
                    "100 °C magnet limits; red dots: the two events (values in the table below).")


def event_table(pts=None, head=True):
    rows = []
    for lp in [lp for lp in (pts or HAVE) if R[lp]]:
        te, ev, _ = events(SRC[lp])
        for lab, t, v in ev:
            f = lambda x: f"{x:.1f}" if x is not None else "—"
            rows.append([f"{lp[-1]}. {DUTY[lp][0]} ({'detailed' if IS_DET(lp) else 'baseline'})", lab,
                         f"<b>{mmss(t/60)}</b> ({t:.0f} s)" if t is not None else f"not reached by {te:.0f} s",
                         f(v["wmax"]), f(v["wmean"]), f(v["mmax"]), f(v["mmean"])])
    return (("<h3>Limit events</h3>" if head else "") + table(["Point", "Event", "Time", "Winding max (°C)", "Winding mean (°C)",
            "Magnet max (°C)", "Magnet mean (°C)"], rows, "Limit events: time and temperatures when the magnets reach 100 °C and the "
            "winding 155 °C (\"not reached\" = not within the plotted window)")) if rows else ""


def transient_table():
    rows = []
    for lp in ORDER:
        r = R[lp]
        if not r:
            rows.append([f"{lp[-1]}. {DUTY[lp][0]}", "<i>pending</i>", "", "", "", ""]); continue
        rows.append([f"{lp[-1]}. {DUTY[lp][0]}", mmss(r["tw"] / 60) if r["tw"] else f"not reached ({r['Tw_end']:.0f} °C)",
                     mmss(r["tm"] / 60) if r["tm"] else f"not reached ({r['Tm_end']:.0f} °C)",
                     mmss(r["t_end"] / 60) + ("" if r["done"] else " (running)"),
                     f"{at(lp, 'winding', DUTY[lp][3]*60):.0f} / {at(lp, 'magnets', DUTY[lp][3]*60):.0f}"
                     if r["t_end"] >= DUTY[lp][3] * 60 else "—", verdict(lp)])
    return table(["Point", "Winding 155 °C at", "Magnets 100 °C at", "Simulated to", "Winding / magnet max at target (°C)", "Verdict"], rows)


def run_notes():
    return "".join(f'<p class="note">{lp}: {esc(n)}.</p>' for lp, n in RUN_NOTE.items() if R[lp])


OBS_INTRO = ("<p>For each computed point, from the actual results: where the hot spot is, which loss drives it, which heat path "
             "carries it and which part of that path limits it, and what each design lever would change. Effects are first-order "
             "estimates from this run (a temperature margin divided by the hot-spot heating rate for the short point, steady-state "
             "scaling for the long point); each needs a confirming CFD re-run.</p>")


# ---------------------------------------------------------------- sections (slices)
def read_vtk(path):            # from animate_temp.py
    tok = open(path).read().split()
    i = tok.index("POINTS"); n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3)
    i = tok.index("POLYGONS"); m = int(tok[i + 1]); j = i + 3; tris = []
    for _ in range(m):
        k = int(tok[j]); ids = [int(t) for t in tok[j + 1:j + 1 + k]]; j += 1 + k
        tris += [(ids[0], ids[q], ids[q + 1]) for q in range(1, k - 1)]
    i = tok.index("FIELD"); nf = int(tok[i + 2]); j = i + 3; T = None
    for _ in range(nf):
        name, nc, nn = tok[j], int(tok[j + 1]), int(tok[j + 2]); j += 4
        if name == "T":
            T = np.array(tok[j:j + nc * nn], float)
        j += nc * nn
    return pts, np.array(tris), T - K


def slice_times(lp):
    """Saved times with standard section planes (slices_<t>; the slices_<t>_z<pos> variants are skipped)."""
    names = (os.path.basename(d) for d in glob.glob(os.path.join(RES, lp, "slices_*")) if glob.glob(os.path.join(d, "*.vtk")))
    return sorted(int(n[7:]) for n in names if n[7:].isdigit())


def nearest(ts, t):
    return min(ts, key=lambda x: abs(x - t)) if ts else None


def section_times(lp):
    """(t, label) for the stills: saved time nearest the first limit, and the last saved time before the 180 °C cut-off."""
    k, lp = lp, SRC[lp]
    ts = slice_times(lp)
    if not ts:
        return []
    te = t_stop(lp) or ts[-1]
    hit = cross(*hist(lp, "winding"), T_STOP) is not None
    tf = max([t for t in ts if t <= te + 1e-6] or ts[:1])
    out = {tf: f"last saved field before the winding reaches {T_STOP:.0f} °C" if hit else "last saved full field"}
    if R[k] and R[k]["t_lim"]:
        t = nearest(ts, R[k]["t_lim"])
        out[t] = out.get(t, "") + ("; " if t in out else "") + f"saved time nearest the {R[k]['by']} limit ({mmss(R[k]['t_lim']/60)})"
    return sorted(out.items())


def slice_stats(lp, t):
    """Per-region hottest point on the section planes {reg: (T, xyz)}, stator axial extent, per-region plane-mean T."""
    best, zs, means = {}, [], {}
    for f in glob.glob(os.path.join(RES, lp, f"slices_{t}", "*.vtk")):
        try:
            pts, _, T = read_vtk(f)
        except (OSError, ValueError, IndexError):
            continue
        reg = os.path.basename(f).rsplit("_", 1)[0]
        means.setdefault(reg, []).append(T.mean())
        if reg == "stator":
            zs += [pts[:, 2].min(), pts[:, 2].max()]
        i = int(np.argmax(T))
        if reg not in best or T[i] > best[reg][0]:
            best[reg] = (float(T[i]), pts[i])
    return best, (min(zs), max(zs)) if zs else None, {k: float(np.mean(v)) for k, v in means.items()}


def _plane(a, d, ax):
    """Draw every region's section plane of one axis from slice folder d on axes a -> (artists, Tmin, Tmax)."""
    arts, lo, hi = [], 1e9, -1e9
    for f in sorted(glob.glob(os.path.join(d, f"*_{ax}.vtk"))):
        try:
            pts, tris, T = read_vtk(f)
        except (ValueError, IndexError):
            continue
        X, Y = (pts[:, 0], pts[:, 1]) if ax == "z" else (-pts[:, 2], pts[:, 1])
        arts.append(a.tripcolor(X * 1000, Y * 1000, tris, T, shading="gouraud", cmap="turbo"))
        lo, hi = min(lo, T.min()), max(hi, T.max())
    a.set_aspect("equal"); a.axis("off")
    return arts, lo, hi


def section(lp, t, label):
    d = os.path.join(RES, lp, f"slices_{t}")
    k = os.path.basename(lp)   # duty key, also for detailed/<lp>
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    arts, lo, hi = [], 1e9, -1e9
    for a, ax in zip(axs, ("z", "x")):
        ar, l, h = _plane(a, d, ax); arts += ar; lo, hi = min(lo, l), max(hi, h)
        a.set_title("radial section z = 5 mm" if ax == "z" else "axial section x = 0 (rear left, drive end right)", fontsize=10)
    if not arts:
        plt.close(fig); return todo(f"{lp}: slice files in {d} unreadable.")
    for ar in arts:
        ar.set_clim(lo, hi)
    fig.colorbar(arts[0], ax=axs, shrink=0.8, label="temperature [°C]")
    fig.suptitle(f"{k[-1]}. {DUTY[k][0]} at {mmss(t/60)}: {lo:.0f}–{hi:.0f} °C", x=0.02, ha="left", fontweight="bold")
    return png(fig, f"{DUTY[k][0]}, {DUTY[k][2]:g} N·m @ {DUTY[k][1]} rpm — temperature at {mmss(t/60)} ({label}).")


def section_pair(lp, t):
    """Baseline (top) and detailed (bottom) section planes at the same saved time on one shared colour scale."""
    fig, axs = plt.subplots(2, 2, figsize=(11, 8.4), gridspec_kw={"width_ratios": [1, 1.25]})
    arts, lo, hi = [], 1e9, -1e9
    for row, (src, lab) in enumerate(((lp, "baseline (homogenised winding)"), (f"detailed/{lp}", "detailed geometry (real coils)"))):
        for a, ax in zip(axs[row], ("z", "x")):
            ar, l, h = _plane(a, os.path.join(RES, src, f"slices_{t}"), ax); arts += ar; lo, hi = min(lo, l), max(hi, h)
            a.set_title(f"{lab}: " + ("radial z = 5 mm" if ax == "z" else "axial x = 0 (rear left)"), fontsize=9.5)
    if not arts:
        plt.close(fig); return todo(f"{lp}: slices at {t} s unreadable.")
    for ar in arts:
        ar.set_clim(lo, hi)
    fig.colorbar(arts[0], ax=axs, shrink=0.6, label="temperature [°C] (shared scale)")
    fig.suptitle(f"{lp[-1]}. {DUTY[lp][0]} at {mmss(t/60)}: baseline vs detailed, {lo:.0f}–{hi:.0f} °C", x=0.02, ha="left", fontweight="bold")
    return png(fig, f"{DUTY[lp][0]} — baseline (top) and detailed geometry (bottom) at the same time {mmss(t/60)}, one colour scale.")


# ---------------------------------------------------------------- heat paths (from make_report.py, Q generalised)
def flows(lp, t):
    """Heat balance at saved time t: copper at the winding mean T, other sources, generated, to ambient, edges [(a, b, W)]."""
    key = os.path.basename(lp)
    hf, q = heatflow(lp, t), Q(key)
    if not hf or not q:
        return None
    g = lambda k: hf.get(k, 0.0)
    if lp.startswith("detailed/"):
        b = budget(lp, key, t)
        cu = b["copper"]["own"]
        other = sum(v for k, v in q.items() if k not in ("winding_100C", "winding_ac") and isinstance(v, (int, float)))
        out = -g(("housing", "defaultFaces")) - g(("shaft", "defaultFaces"))
        E = [("w", "st", -g(("bobbin", "bobbin_to_stator")) - g(("resin", "resin_to_stator"))),
             ("w", "air", -g(("copper", "copper_to_inair")) - g(("resin", "resin_to_inair")) - g(("bobbin", "bobbin_to_inair"))),
             ("air", "st", -g(("inair", "inair_to_stator"))), ("air", "rot", -g(("inair", "inair_to_rotor"))),
             ("air", "hous", -g(("inair", "inair_to_housing"))), ("st", "hous", g(("housing", "housing_to_stator"))),
             ("hous", "amb", out)]
        return cu, other, cu + other, out, E
    Tw = at(lp, "winding", t, "Tavg") or 100.0
    # DC copper scales with T, AC copper (winding_ac) is a constant source in the same winding (make_case.py)
    cu = q.get("winding_100C", 0) * (1 + MC.get("JOULE_TC", 0.00393) * (Tw - 100)) + q.get("winding_ac", 0)
    other = sum(v for k, v in q.items() if k not in ("winding_100C", "winding_ac") and isinstance(v, (int, float)))
    out = -g(("housing", "defaultFaces")) - g(("shaft", "defaultFaces"))
    E = [("w", "st", -g(("winding", "winding_to_stator"))), ("w", "air", -g(("winding", "winding_to_inair"))),
         ("air", "st", -g(("inair", "inair_to_stator"))), ("air", "rot", -g(("inair", "inair_to_rotor"))),
         ("air", "hous", -g(("inair", "inair_to_housing"))), ("st", "hous", g(("housing", "housing_to_stator"))),
         ("hous", "amb", out)]
    return cu, other, cu + other, out, E


def heatpath_svg(src, t):
    f = flows(src, t)
    if not f:
        return None
    cu, other, gen, out, E = f
    lp = src.replace("/", "_")
    q = Q(os.path.basename(src))
    N = {"w": (95, 215, "Winding" if lp == src else "Coil + resin + bobbin", f"makes {cu:.0f} W (copper)"), "st": (300, 130, "Stator", f"makes {q.get('stator', 0):.0f} W (iron)"),
         "air": (300, 300, "Internal air", "end spaces"),
         "rot": (505, 380, "Rotor, magnets", f"makes {other - q.get('stator', 0):.0f} W"),
         "hous": (505, 180, "Housing", "fins, end shields"), "amb": (675, 180, "Ambient air", "convection + radiation")}
    BW, BH, sc = 140, 50, 30.0 / max(max(w for *_, w in E), 1)
    s = [f'<svg viewBox="0 0 760 460" class="diagram" role="img" aria-label="heat paths {lp}">',
         f'<defs><marker id="ar{lp}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0L10 5L0 10z" fill="#c2185b"/></marker></defs>']
    for a, b, w in E:
        x1, y1, *_ = N[a]; x2, y2, *_ = N[b]; sw = 1.5 + max(w, 0) * sc
        if x1 == x2:
            dpath = f"M{x1} {y1 - BH/2}L{x2} {y2 + BH/2 + 4}"; lx, ly, anc = x1 + 14, (y1 + y2) / 2 + 4, "start"
        else:
            sx, ex = x1 + BW / 2, x2 - BW / 2 - 4; mx = (sx + ex) / 2
            dpath = f"M{sx} {y1}C{mx} {y1} {mx} {y2} {ex} {y2}"; lx, ly, anc = mx, (y1 + y2) / 2 - sw / 2 - 6, "middle"
            if (a, b) == ("hous", "amb"): ly = y1 - 34
            if (a, b) == ("air", "rot"): lx, ly = mx - 34, (y1 + y2) / 2 + 22
            if (a, b) == ("st", "hous"): ly -= 10
        s.append(f'<path d="{dpath}" fill="none" stroke="#c2185b" stroke-opacity="0.45" stroke-width="{sw:.1f}" marker-end="url(#ar{lp})"/>')
        s.append(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="{anc}" class="lbl">{w:.0f} W</text>')
    for x, y, name, sub in N.values():
        s.append(f'<rect x="{x-BW/2}" y="{y-BH/2}" width="{BW}" height="{BH}" rx="8" class="node"/>')
        s.append(f'<text x="{x}" y="{y-4}" text-anchor="middle" class="nname">{name}</text><text x="{x}" y="{y+13}" text-anchor="middle" class="nsub">{sub}</text>')
    s.append(f'<text x="24" y="445" class="nsub">Generated {gen:.0f} W − leaving to ambient {out:.0f} W = {gen-out:.0f} W stored in the motor mass ({(gen-out)/gen*100:.0f} %)</text></svg>')
    return "".join(s), gen, out


def heat_section():
    out, rows = "", []
    for lp in ORDER:
        ts = saved_times(lp, "heatflow_*.txt")
        bal = [(t, heatpath_svg(lp, t)) for t in ts]
        bal = [(t, b) for t, b in bal if b]
        if not bal:
            out += f"<h3>{lp[-1]}. {DUTY[lp][0]}</h3>" + todo(f"results/{lp}/heatflow_<t>.txt (heatpaths.sh) not available yet.")
            continue
        for t, (_, gen, o) in bal:
            rows.append([f"{lp[-1]}. {DUTY[lp][0]}", mmss(t / 60), f"{gen:.0f}", f"{o:.0f}", f"{gen-o:.0f}", f"{(gen-o)/gen*100:.0f} %"])
        t, (d, *_) = bal[-1]
        out += f"<h3>{lp[-1]}. {DUTY[lp][0]}, {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]} rpm, at {mmss(t/60)}</h3>" + d
    if rows:
        out = table(["Point", "Time", "Generated (W)", "To ambient (W)", "Stored (W)", "Stored share"], rows) + out
    return out


# ---------------------------------------------------------------- energy verification
def energy_section():
    b = ("<p>Before the fix, an adiabatic test (outer skin insulated, fixed losses, copper loss not temperature-dependent) "
         "with <b>299.76 W for 300 s</b> must store exactly <b>89.93 kJ</b>; the model stored only <b>46 kJ</b> (−49 %). "
         "In the old 12 h continuous run ~336 W was generated, ~205 W left to ambient and only ~9 W was being stored, "
         "so ~120 W simply vanished — every old run time was too long by roughly a factor of two.</p>")
    rows = [["Before fix (earlier report)", "299.76", "300", "89.93", "46", "−49 %"]]
    a = ETEST.get("after")
    for key, lab in (("after", "After fix"), ("production", "Production settings (used for every run in this report)")):
        e = ETEST.get(key)
        if e:
            st, ex = e.get("stored_kJ"), e.get("expected_kJ")
            rows.append([lab + (f"<br><span class=\"note\">{esc(e['setting'])}</span>" if e.get("setting") else ""),
                         f"{e.get('Q_W', '')}", f"{e.get('t_s', '')}", f"{ex}", f"{st}", f"{(st/ex-1)*100:+.1f} %" if st and ex else ""])
    tab = table(["Adiabatic energy test", "Heat (W)", "Duration (s)", "Exact stored (kJ)", "Model stored (kJ)", "Error"], rows)
    lr = ETEST.get("long_run")
    extra = ("<p>Long-run check after the fix: " + esc(" · ".join(f"{k} {v}" for k, v in lr.items())) + "</p>") if lr else ""
    note = "" if a else todo("post-fix energy test (results/energy_test.json, key 'after') from the CFD agent.")
    eb = [(lp, d) for lp in ORDER if (d := jload(os.path.join(RES, lp, "energy_balance.json")))]
    run = ("<p>The same check on the real, non-adiabatic duty runs (copper loss rising with temperature, convection and radiation "
           "to ambient): heat generated − heat out = heat stored in the motor mass, integrated over the run.</p>"
           + table(["Run", "Integrated to", "Generated (kJ)", "Out to ambient (kJ)", "Stored (kJ)", "Error", "At the end: generated / out (W)"],
                   [[f"{lp[-1]}. {DUTY[lp][0]}", mmss(d["t_end_s"] / 60), f"{d['generation_kJ']:.1f}", f"{d['outflow_kJ']:.1f}",
                     f"{d['storage_kJ']:.1f}", f"{d['error_pct']:+.2f} %", f"{d['gen_end_W']:.0f} / {d['outflow_end_W']:.0f}"] for lp, d in eb])
           ) if eb else ""
    over = [f"{lp} {d['error_pct']:+.2f} %" for lp, d in eb if abs(d["error_pct"]) > 1]
    if over:
        run += (f'<p class="note">Goal: within ±1 %. {", ".join(over)} is slightly outside it: with 60 s steps the coupling iterations '
                "converge only to the 1e-3 residual, so a little energy is lost each step and it accumulates over a long run. "
                "That is ~1 % of the heat. It does not change any limit time or conclusion in this report.</p>")
    return b + tab + extra + note + run


# ---------------------------------------------------------------- electromagnetic load points (FEMM agent)
def em_section():
    out = ("<p class=\"lead\">Where the heat comes from at each duty point and why, from the FEMM model of Design9795_1 "
           "(losses tuned to Motor-CAD). duty1 (low speed, high torque) and duty4 (top speed, field weakening) are the two extremes "
           "and are shown in detail.</p>")
    if FDJ:
        rows = []
        for lp in ORDER:
            d = FDJ.get(lp)
            if not d:
                continue
            o, L = d.get("operating", {}), d.get("losses_W", {})
            rows.append([lp, d["rpm"], f"{d['torque_Nm']:g}", f"{d['f_el_Hz']:.0f}", f"{o.get('I_line', 0):.0f}",
                         f"{o.get('id_phase_pk', 0):.0f} / {o.get('iq_phase_pk', 0):.0f}", f"{o.get('V_ph_pk', 0):.1f}"]
                        + [f"{L.get(k, 0):.0f}" for k in ("cu_dc", "cu_ac", "stator", "rotor", "bearings", "windage")]
                        + [f"<b>{d['total_W']:.0f}</b>", f"{d.get('mcad_total_W', 0):.0f}", esc(d.get("dominant_term", ""))])
        out += table(["Point", "rpm", "N·m", "f el (Hz)", "I line (A rms)", "id / iq (A pk)", "V ph pk (max 49.4)", "Cu DC", "Cu AC",
                      "Stator Fe", "Rotor Fe", "Bearings", "Windage", "Total (W)", "Motor-CAD (W)", "Largest term"], rows)
    else:
        out += todo("results/femm_duty/femm_duty.json (FEMM agent).")
    out += media(os.path.join(FD, "loss_segregation.png"), "Loss segregation per duty point (FEMM, Design9795_1).")
    out += media(os.path.join(FD, "dq_limits.png"), "d-q current plane with the voltage ellipse at each speed and the current limit: "
                 "duty1 is current/torque driven, duty4 sits on the voltage ellipse.")
    used = {"loss_segregation.png", "dq_limits.png"}
    for lp in EMF:
        d, q = FDJ.get(lp), DQ.get(lp)
        out += f"<h3>{lp[-1]}. {DUTY[lp][0]}, {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]} rpm</h3>"
        if d:
            out += (f"<p><b>Cause.</b> {esc(d['reason'])}</p><p><b>CFD consequence.</b> {esc(d['cfd_consequence'])}</p>"
                    f"<p><b>EM levers.</b> {esc(d['em_levers'])}</p>")
        if q:
            out += (f"<p class=\"note\">Voltage {q['V_op']:.1f} of {q['V_max']:g} V pk (with id = 0 it would need {q['V_same_iq_id0']:.0f} V); "
                    f"current angle {q['gamma_deg']:.0f}°, d-axis flux reduced {q['psi_d_reduction_pct']:.0f} %, power factor {q['pf']:.2f}.</p>")
        mp4 = os.path.join(FD, f"flux_{lp}.mp4"); used.add(os.path.basename(mp4))
        still = sorted(glob.glob(os.path.join(FD, f"flux_{lp}*frame0*.png")))
        used.update(os.path.basename(s) for s in still)
        cap = f"|B| (0–2 T) and flux lines over one electrical period, {lp}, rotor turning, phase-current marker."
        out += media(mp4, "Animation: " + cap) if os.path.exists(mp4) or not still else media(still[0], "First frame: " + cap)
    out += "<h3>duty1 vs duty4: where the iron and AC copper loss sit</h3>"
    for f, cap in (("iron_density_duty1_vs_duty4.png", "Iron-loss density (W/kg) per element from the full-cycle B waveforms (Motor-CAD Steinmetz)."),
                   ("waveforms_spectrum_duty1_vs_duty4.png", "Tooth, tip, yoke and rotor B waveforms and their harmonic spectra."),
                   ("slot_leakage_duty1_vs_duty4.mp4", "Animation: slot leakage B at the wires over the cycle (AC copper loss ~ f² B²).")):
        used.add(f); out += media(os.path.join(FD, f), cap)
    used.add("slot_leakage_frame0.png")   # first frame of the mp4 above
    if FSTAT:
        pts = [lp for lp in ORDER if isinstance(FSTAT.get(lp), dict)]
        cols = {lp: dict((k, v) for k, v in flat_rows(FSTAT[lp])) for lp in pts}
        keys = list(dict.fromkeys(k for lp in pts for k in cols[lp]))
        out += ("<h4>Field statistics (FEMM, unskewed centre slice)</h4>"
                + table(["Quantity"] + pts, [[k] + [cols[lp].get(k, "—") for lp in pts] for k in keys]))
        pr = FSTAT.get("probes") or {}
        names = list(dict.fromkeys(n for lp in pts for n in (pr.get(lp) or {})))
        if names:   # harmonics are in the waveform/spectrum figure; the table keeps the peak only
            bp = lambda lp, n: ((pr.get(lp) or {}).get(n) or {}).get("B_peak")
            out += table(["Probe: peak B (T)"] + pts, [[esc(n)] + [f"{bp(lp, n):.2f}" if bp(lp, n) is not None else "—" for lp in pts]
                                                       for n in names])
    else:
        out += todo("results/femm_duty/field_stats.json not available yet.")
    extra = [p for p in sorted(glob.glob(os.path.join(FD, "*.png")) + glob.glob(os.path.join(FD, "*.mp4")))
             if os.path.basename(p) not in used]
    out += "".join(media(p, os.path.basename(p)) for p in extra)
    return out


# ---------------------------------------------------------------- animations and cross-sections
def anim_section():
    out = ("<h3>External air (natural convection, shared by all duty points)</h3><p class=\"note\">One CFD of the still air around "
           "the motor (results/air, housing at ΔT 60 K): no fan or vehicle air speed, so the same flow applies to every duty point. "
           "Its per-face h is the outer boundary condition of every run.</p>")
    for ax, lab in (("z", "radial mid-plane z = 5 mm"), ("x", "axial mid-plane, rear left / drive end right")):
        out += (media(os.path.join(AD, f"ext_air_{ax}.mp4"), f"Animation: air around the motor, {lab} (real time).")
                + media(os.path.join(FG, f"ext_air_{ax}.png"), f"Air speed and streamlines around the motor, {lab}."))
    for lp in ORDER:
        st = section_times(lp)
        if lp not in FOCUS and not st:
            continue
        name = f"{lp[-1]}. {DUTY[lp][0]}, {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]} rpm"
        out += f"<h3>{name}</h3>" + (f'<p class="note">Note: {esc(RUN_NOTE[lp])}.</p>' if lp in RUN_NOTE else "")
        out += "".join(section(lp, t, l) for t, l in st) or todo(f"results/{lp}/slices_<t>/ section planes (CFD agent).")
        if lp not in FOCUS:
            continue
        out += (media(os.path.join(AD, f"temp_{lp}.mp4"), f"Animation: temperature rise from the 40 °C start, {name}; fixed colour scale.")
                + media(os.path.join(AD, f"heat_{lp}.mp4"), f"Animation: heat flow between the parts, {name}."))
        out += "<h4>Air inside the motor</h4>"
        src, why = INAIR.get(lp, (lp, ""))
        rpm = DUTY[src][1]
        if not os.path.isdir(os.path.join(RES, f"inair_{src}")):
            out += todo(f"results/inair_{src} (internal-air CFD at {rpm} rpm, CFD agent).")
        elif src != lp:   # reused field: shown once under its own point, referenced here
            out += f'<p class="note">{esc(why[0].upper() + why[1:])}: see the {src} internal-air animations and stills above.</p>'
        else:
            out += f'<p class="note">{esc(why[0].upper() + why[1:])}.</p>' if why else ""
            for ax, lab in (("z", "drive-end space z = −40 mm"), ("x", "axial mid-plane")):
                out += (media(os.path.join(AD, f"inair_{ax}_{src}.mp4"), f"Animation: inside air at {rpm} rpm, {lab} (slow motion).")
                        + media(os.path.join(FG, f"inair_{ax}_{src}.png"), f"Inside air at {rpm} rpm, {lab}."))
        t3 = max((int(d.rsplit("_", 1)[1]) for d in glob.glob(os.path.join(RES, "vtk3d", f"{lp}_*")) if d.rsplit("_", 1)[1].isdigit()), default=None)
        when = f"at {mmss(t3/60)} (last saved full field)" if t3 else "at the last saved full field"
        tb = budget_time(lp)
        out += ("<h4>Who heats whom</h4>" + media(os.path.join(AD, f"budget_{lp}.mp4"), f"Animation: heat budget per part over time, {name}.")
                + (f"<p>At {mmss(tb/60)} (last saved heat flow before the 180 °C cut-off):</p>" + budget_lines(lp, lp, tb) if tb else ""))
        out += ("<h4>3D cut-away</h4>" + media(os.path.join(FG, f"3d_{lp}.png"), f"3D cut-away coloured by temperature {when}, {name}.")
                + media(os.path.join(AD, f"3d_{lp}.mp4"), f"Animation: 360° turn around the cut-away, {name}."))
    return out


# ---------------------------------------------------------------- observations: causes and improvements
def observe(lp):
    """Quantitative findings and improvement estimates for one point from the actual CFD/FEMM outputs.
    ponytail: improvement effects are first-order (ΔT / dT/dt for margins, stored-power scaling for losses); a re-run confirms."""
    name, rpm, tq, tgt, ut, u6, sp = DUTY[lp]
    r, fd = R[lp], FDJ.get(lp) or {}
    L = fd.get("losses_W") or {}
    key, lp, det = lp, SRC[lp], IS_DET(lp)          # data from the detailed run where it exists
    head = f"<h3>{lp[-1]}. {name}, {tq:g} N·m @ {rpm} rpm</h3>"
    loss_txt = (f"{esc(fd['dominant'])}; total {fd['total_W']:.0f} W (Motor-CAD {fd['mcad_total_W']:.0f} W): "
                + " · ".join(f"{k} {v:.0f}" for k, v in L.items())) if fd else "<i>pending (results/femm_duty/femm_duty.json)</i>"
    if not r:
        return head + inputs([("Dominant loss", loss_txt)], "Findings") + todo(f"results/{lp} CFD histories, slices and heat flows (CFD agent).")
    tl, t_ev = r["t_lim"], r["t_lim"] or r["t_end"]
    rows = []
    # time to limit vs target and benchmarks
    tt = (f"<b>{mmss(tl/60)}</b> to the {r['by']} limit vs target {tgt} min ({(tl/60/tgt-1)*100:+.0f} %)" if tl
          else f"no limit within {mmss(r['t_end']/60)} (target {tgt} min); winding {r['Tw_end']:.0f} °C, magnets {r['Tm_end']:.0f} °C at the end")
    bm = "; ".join(f"{lab} {mmss(v)}" + (f" (CFD / ref. {tl/60/v:.2f})" if tl else "")
                   for lab, v in (("U666 test", ut), ("Spoke (Ferrite) column from slide 3, a different motor's data, benchmark only", sp)) if v)
    rows.append(("Model", MODEL(key) + (f"; {DET_NOTE[key]}" if det and key in DET_NOTE else "")))
    rows.append(("Time to limit", tt + (f". Benchmarks: {bm}" if bm else "") + (f". Note: {esc(RUN_NOTE[lp])}" if lp in RUN_NOTE else "")))
    # hot spot
    Tmx = at(lp, "winding", t_ev)
    hs = f"winding maximum {Tmx:.0f} °C" + (f", magnet maximum {at(lp, 'magnets', t_ev):.0f} °C (limiting)" if r["by"] == "magnets" else "") \
        + f" at {mmss(t_ev/60)} (monitors, whole region)"
    ts = nearest(slice_times(lp), t_ev)
    if ts is not None:
        best, zr, _ = slice_stats(lp, ts)
        reg = r["by"] or "winding"
        reg = "copper" if det and reg == "winding" else reg
        if reg in best:
            T, p = best[reg]
            end = "rear (non-drive)" if p[2] > 0 else "drive-end"      # +z is the rear, as in the axial plots
            part = "end winding" if reg in ("winding", "copper") else f"end of the {reg}"
            where = ("" if not zr else f" → {end} {part}, outside the stack" if not zr[0] <= p[2] <= zr[1]
                     else " → inside the stack" + (" (slot)" if reg in ("winding", "copper") else ""))
            hs += (f"; hottest point on the section planes at {mmss(ts/60)}: {T:.0f} °C in the {reg}, r {math.hypot(p[0], p[1])*1e3:.0f} mm, "
                   f"z {p[2]*1e3:.0f} mm{where}" + (f" (stack z {zr[0]*1e3:.0f} … {zr[1]*1e3:.0f} mm)" if zr else ""))
    if "end winding" in hs and os.path.exists(ENDW):
        hs += ("; front and rear end windings are within 1 °C in this real-wire model, so the hot spot is not specific to one end "
               "(see the end-winding subsection)" if det else
               "; a one-end hot spot is mostly a smeared-winding artefact: the detailed real-wire runs keep both ends within 1 °C "
               "(sections 3.1, 3.4), so read it as the whole winding running hot")
    rows.append(("Hot spot", hs))
    rows.append(("Dominant loss", loss_txt))
    # heat path and bottleneck at the heat-flow time nearest the evaluation time
    th = nearest(saved_times(lp, "heatflow_*.txt"), t_ev)
    f = flows(lp, th) if th is not None else None
    chain, imp = [], []
    if not f:
        rows.append(("Heat path", f"<i>no saved heat flow in results/{lp}</i>"))
    else:
        cu, other, gen, out, E = f
        Ed = {(a, b): w for a, b, w in E}
        stored = gen - out
        Tw, Th, Tm = at(lp, "winding", th, "Tavg"), at(lp, "housing", th, "Tavg"), at(lp, "winding", th)
        sm = slice_stats(lp, th)[2] if th in slice_times(lp) else {}
        Tst, Tair = sm.get("stator"), sm.get("inair")
        if Tm is not None and Tw is not None:
            chain.append(("Winding interior (hot spot − winding mean)", cu, Tm - Tw))
        if Tw is not None and Th is not None:
            if Tst is not None:
                chain += [("Winding → stator (bobbin + resin)" if det else "Winding → stator (bobbin / slot liner)", Ed[("w", "st")], Tw - Tst)]
                if Tair is not None:
                    chain.append(("Winding → end-space air (end turns)", Ed[("w", "air")], Tw - Tair))
                chain += [
                          ("Stator → housing (yoke + shrink fit)", Ed[("st", "hous")], Tst - Th)]
            else:
                chain.append(("Winding → housing (liner + iron + shrink fit)", Ed[("st", "hous")], Tw - Th))
            chain.append(("Housing → ambient (fins: convection + radiation)", out, Th - 40.0))
        neck = max(chain, key=lambda c: c[2]) if chain else None
        rows.append(("Heat path", f"at {mmss(th/60)}: {gen:.0f} W generated, <b>{stored/gen*100:.0f} % stored</b> in the motor mass, {out:.0f} W to ambient. "
                     f"From the winding{' package (coil + resin + bobbin)' if det else ''}: {Ed[('w', 'st')]:.0f} W into the stator "
                     f"({Ed[('w', 'st')]/max(Ed[('w', 'st')] + Ed[('w', 'air')], 1e-9)*100:.0f} %), {Ed[('w', 'air')]:.0f} W into the end-space air; "
                     f"stator → housing {Ed[('st', 'hous')]:.0f} W."
                     + (f" Bottleneck: <b>{neck[0].lower()}</b>, {neck[2]:.0f} K." if neck else "")))
        # improvements
        h = hist(lp, "winding")
        t0 = max(0.9 * t_ev, t_ev - 60)
        rate = (np.interp(t_ev, *h) - np.interp(t0, *h)) / (t_ev - t0) if t_ev > t0 else 0
        transient = stored / gen > 0.5
        lim_w = r["by"] == "winding"   # winding-side levers convert to limit time only when the winding sets the limit
        def gK(dK):
            if tl and transient and lim_w and rate > 0:
                return f"≈ +{dK/rate:.0f} s to the limit ({dK:.0f} K margin at {rate*60:.1f} K/min)"
            return f"≈ −{dK:.0f} K on the winding hot spot"
        def gQ(dQ):
            if transient and tl and lim_w:
                return f"≈ +{(stored/(stored-dQ)-1)*100:.0f} % time to the limit"
            if transient:
                return f"≈ {dQ/stored*100:.0f} % slower motor-wide temperature rise"
            return f"≈ −{dQ*((Tm or 40)-40)/gen:.0f} K on the hot spot (steady-state scaling)"
        # winding exits are parallel: doubling one conductance Gi lowers the winding-to-sink ΔT from Q/G to Q/(G + Gi)
        par = {lab: Qc / dT for lab, Qc, dT in chain if lab.startswith("Winding →") and dT > 0.5 and Qc > 0}
        Qp, G = sum(c[1] for c in chain if c[0] in par), sum(par.values())
        dpar = lambda lab: Qp / G - Qp / (G + par[lab]) if lab in par else 0.0
        for lab, Qc, dT in chain:
            if lab.startswith("Winding interior"):
                imp.append(("Impregnation / potting k", f"interior ΔT {dT:.0f} K across " + ("coil and resin" if det else "the homogenised winding (k 1.0 W/m·K)"),
                            "vacuum impregnation or filled resin, k 1 → 2 W/m·K halves it: " + gK(dT / 2)))
            elif "bobbin" in lab or "liner" in lab:
                imp.append(("Slot liner / bobbin", f"{dT:.0f} K for {Qc:.0f} W (R {dT/max(Qc, 1e-9):.3f} K/W)",
                            "thinner or higher-k liner, no air gaps to the tooth (×2 conductance): " + gK(dpar(lab))))
            elif "end-space" in lab:
                imp.append(("End-space airflow / end-turn potting", f"{dT:.0f} K for {Qc:.0f} W ({Qc/max(cu, 1e-9)*100:.0f} % of the copper loss)",
                            "rotor end vanes or fan, or potting the end turns to the end shield (×2 conductance): " + gK(dpar(lab))))
            elif lab.startswith("Stator → housing"):
                imp.append(("Stator–housing interface", f"{dT:.0f} K for {Qc:.0f} W", "tighter shrink fit / interface compound (×2): " + gK(dT / 2)))
            elif lab.startswith("Housing → ambient"):
                imp.append(("Fins / external air", f"{dT:.0f} K for {Qc:.0f} W (R {dT/max(Qc, 1e-9):.3f} K/W)",
                            ("longer fins or forced air (×2 h·A): " + (gQ(out) + " (upper bound: the extra heat leaves the housing, not the winding)"
                                                                       if transient else gK(dT / 2)))))
        if L.get("cu_dc"):
            imp.append(("DC copper", f"Cu DC {L['cu_dc']:.0f} W", "fill factor / shorter end turns, −10 % resistance: " + gQ(0.1 * L["cu_dc"])))
        if L.get("cu_ac", 0) > 0.1 * gen:
            imp.append(("AC copper (strand choice)", f"Cu AC {L['cu_ac']:.0f} W, wire/skin depth {fd.get('wire_over_skin', 0):.2f}",
                        "parallel strands of half the diameter (eddy ~ d²: −75 %): " + gQ(0.75 * L["cu_ac"])))
        if L.get("stator", 0) > 0.15 * gen:
            hy = ((FSTAT or {}).get(key) or {}).get("hysteresis_share_pct")
            eddy = L["stator"] * (1 - hy / 100) if hy is not None else L["stator"]
            imp.append(("Iron grade", f"stator iron {L['stator']:.0f} W at {fd.get('f_el_Hz', 0):.0f} Hz"
                        + (f", {100-hy:.0f} % eddy (field_stats.json)" if hy is not None else ""),
                        "0.20 mm instead of 0.35 mm laminations (eddy ×0.33)" + ("" if hy is not None else ", upper bound if all were eddy")
                        + ": " + gQ(0.67 * eddy)))
        if r["by"] == "magnets" and L:
            rs = L.get("rotor", 0) + L.get("bearings", 0) + L.get("windage", 0)
            dq = 0.3 * L.get("bearings", 0)
            imp.append(("Rotor-side heat (magnet limit)", f"rotor iron {L.get('rotor', 0):.0f} + bearings {L.get('bearings', 0):.0f} + windage "
                        f"{L.get('windage', 0):.0f} = {rs:.0f} W heat the rotor, whose only exits are the air gap, end-space air and shaft",
                        f"low-friction / lower-preload bearings (−30 %, {dq:.0f} W): ≈ +{dq/max(rs-dq, 1e-9)*100:.0f} % time to the magnet limit "
                        "(rotor-local scaling, time ∝ 1 / rotor-side heat); rotor end vanes also help the rotor → end-space air exit"))
        q = DQ.get(key)
        if q and q["V_op"] / q["V_max"] > 0.95:
            volt = next((s.strip() for s in fd.get("em_levers", "").split(";") if "voltage" in s.lower()), "")
            imp.append(("Voltage margin", f"{q['V_op']:.1f} of {q['V_max']:g} V pk, {q['fw_fraction_id_over_I']*100:.0f} % of the current is field weakening",
                        esc(volt) or "a higher DC link or less battery sag cuts the d-axis current"))
        if r["t_end"] >= tgt * 60:
            tw, tm = at(lp, "winding", tgt * 60), at(lp, "magnets", tgt * 60)
            hw, hm = hist(lp, "winding"), hist(lp, "magnets")
            dr = lambda h: (np.interp(tgt * 60, *h) - np.interp(tgt * 60 - 300, *h)) / 5   # K/min over the last 5 min
            rows.append(("At the target time", f"{tgt} min: winding {tw:.0f} °C, magnets {tm:.0f} °C, still rising "
                                               f"{dr(hw):.1f} / {dr(hm):.1f} K/min (limits {LIM_W:.0f} / {LIM_M:.0f} °C)"))
        if tl and transient and lim_w and tl / 60 < tgt:
            rows.append(("To meet the target", f"the stored power must fall by ≈ {stored*(1-tl/60/tgt):.0f} W "
                                               f"({(1-tl/60/tgt)*100:.0f} %), or the margins below combined"))
    out = head + inputs(rows, "Findings")
    if chain:
        out += table(["Path", "Heat (W)", "ΔT (K)", "R (K/W)"],
                     [[esc(a), f"{b:.0f}", f"{c:.1f}", f"{c/b:.3f}" if b > 1e-9 else "—"] for a, b, c in chain])
        out += ('<p class="note">Stator and end-space air temperatures: means over the section planes (proxy for the volume means, '
                'which are not monitored). The two winding exits (stator, end-space air) are parallel paths; a lever on one of them is '
                'credited with the drop of the combined winding-to-sink ΔT.</p>') if any("stator" in c[0].lower() for c in chain) else ""
    if imp:
        out += "<h4>Improvements and expected effect</h4>" + table(["Lever", "Why, from this run", "Change and expected effect"], imp)
    return out


def detailed_section():
    md, js = os.path.join(RES, "detailed_vs_baseline.md"), jload(os.path.join(RES, "detailed_vs_baseline.json")) or {}
    have = [lp for lp in DET if os.path.isdir(os.path.join(RES, "detailed", lp))]
    if not have:
        return todo("results/detailed/&lt;lp&gt; and results/detailed_vs_baseline.md (detailed-geometry runs, DETAIL agent).")
    et = jload(os.path.join(RES, "energy_test_detailed.json")) or {}
    out = inputs([
        ("Purpose", "check the homogenised winding block of the baseline model against the real conductor geometry"),
        ("Geometry", "real coils re-swept from the CAD centreline as bare 2.9 mm copper, with resin, a simplified bobbin "
                     "(4457 vs 4773 mm³ in the CAD), busbars, straps and t-bars; everything else as the baseline"),
        ("Mesh", "4.65 M tetrahedra (Delaunay); checkMesh passes except 2 cells with aspect ratio 1225; 4 screw-hole voids of 4 mm³ "
                 "left as adiabatic holes"),
        ("Copper region", "coil, straps, busbars and t-bars merged into one region with one Joule source per part: as separate "
                          "regions the copper-to-copper coupling stalled and the energy test failed (−1.3 %)"),
    ], "Detailed geometry: method")
    rows = [[esc(lab), f"{e['t_s']}", f"{e['expected_kJ']}", f"{e['stored_kJ']}", f"{e['error_pct']:+.1f} %"]
            for key, lab in (("split_copper_regions", "Separate copper regions (rejected)"), ("merged_copper", "Merged copper (used)"))
            if (e := et.get(key))]
    if rows:
        out += table(["Adiabatic energy test, detailed mesh", "Duration (s)", "Exact stored (kJ)", "Model stored (kJ)", "Error"], rows)
    eb = []   # whole-run energy balances, detailed vs baseline (goal |error| <= 1 %)
    for lp in have:
        d, b = jload(os.path.join(RES, "detailed", lp, "energy_balance.json")), jload(os.path.join(RES, lp, "energy_balance.json"))
        if d and d.get("error_pct_range"):
            lo, hi = sorted(d["error_pct_range"]); bad = max(abs(lo), abs(hi)) > 1
            eb.append(f"{lp}: detailed run {lo:+.1f} to {hi:+.1f} %" + (" (outside the 1 % goal)" if bad else "")
                      + (f", baseline {b['error_pct']:+.2f} %" if b and "error_pct" in b else ""))
    if eb:
        out += ("<p><b>Run energy balance</b> (stored + lost vs generated over the run; the range spans the copper-loss temperature "
                "dependence): " + "; ".join(eb) + ". The detailed duty4 run loses about 2 % of the heat, so its temperatures are "
                "slightly low; this does not change the verdict below, where the baseline reaches every limit first.</p>")
    # time histories: baseline winding block vs detailed coil
    fig, axs = plt.subplots(1, len(have), figsize=(5.2 * len(have), 3.3), squeeze=False)
    for ax, lp in zip(axs[0], have):
        d = f"detailed/{lp}"
        tb, td = t_stop(lp), t_stop(d)   # each model cut where its own winding max reaches 180 °C
        for h, col, ls, lab in ((upto(hist(lp, "winding"), tb), COL[lp], "-", "baseline winding max"),
                                (upto(hist(lp, "winding", "Tavg"), tb), COL[lp], ":", "baseline winding mean"),
                                (upto(hist(d, "copper", fn="T_coil"), td), "#ef6c00", "-", "detailed coil max"),
                                (upto(hist(d, "copper", fn="Tavg_coil"), td), "#ef6c00", ":", "detailed coil mean"),
                                (upto(hist(lp, "magnets"), tb), "#2e7d32", "-", "baseline magnet max"),
                                (upto(hist(d, "magnets"), td), "#7cb342", "--", "detailed magnet max")):
            if h is not None:
                ax.plot(h[0] / 60, h[1], color=col, ls=ls, lw=1.6, label=lab)
        ax.axhline(LIM_W, color="#c62828", ls="--", lw=1); ax.axhline(LIM_M, color="#c62828", ls=":", lw=1)
        ax.set_title(f"{lp[-1]}. {DUTY[lp][0]}", loc="left", fontweight="bold", fontsize=10); ax.set_xlabel("min"); ax.set_ylabel("°C")
    axs[0, 0].legend(frameon=False, fontsize=8)
    out += svg(fig, "Baseline homogenised winding vs detailed coil geometry: maximum (solid) and mean (dotted); magnets in green. "
                    f"Each curve ends where that model's winding maximum reaches {T_STOP:.0f} °C (or at the end of the run).")
    # limit events, both models side by side
    rows = []
    for lp in have:
        for src, model in ((lp, "baseline"), (f"detailed/{lp}", "detailed")):
            te, ev, _ = events(src)
            for lab, t, v in ev:
                f = lambda x: f"{x:.1f}" if x is not None else "—"
                rows.append([lp, lab, model, f"<b>{mmss(t/60)}</b> ({t:.0f} s)" if t is not None else f"not reached by {te:.0f} s",
                             f(v["wmax"]), f(v["wmean"]), f(v["mmax"]), f(v["mmean"])])
    out += "<h3>Limit events, both models</h3>" + table(["Point", "Event", "Model", "Time", "Winding max (°C)", "Winding mean (°C)",
                                                         "Magnet max (°C)", "Magnet mean (°C)"], rows)
    end = []
    for lp in have:
        b, dt = (js.get(lp) or {}).get("baseline") or {}, (js.get(lp) or {}).get("detailed") or {}
        if b.get("winding") and dt.get("coil"):
            end += [[lp, f"Busbar / strap / t-bar max at {dt.get('t_end_s', 0):.0f} s (°C)", "not modelled",
                     " / ".join(f"{(dt.get(k) or {}).get('T_max_C', float('nan')):.0f}" for k in ("busbar", "strap", "tbar"))],
                    [lp, f"Bobbin / resin max at {dt.get('t_end_s', 0):.0f} s (°C)", "inside the winding block",
                     " / ".join(f"{(dt.get(k) or {}).get('T_max_C', float('nan')):.0f}" for k in ("bobbin", "resin"))]]
    if end:
        out += table(["Point", "Parts only in the detailed model", "Baseline", "Detailed"], end)
    for lp in have:   # side-by-side stills at the last common saved time before either model reaches 180 °C
        te = min(x for x in (t_stop(lp), t_stop(f"detailed/{lp}")) if x is not None)
        ts = [t for t in slice_times(f"detailed/{lp}") if t in slice_times(lp) and t <= te + 1e-6]
        if ts:
            out += section_pair(lp, ts[-1])
    out += "<h3>Who heats whom: component heat budget, both models</h3>" + BUDGET_NOTE
    for lp in have:
        out += budget_compare(lp)
    out += ("<p><b>Interpretation.</b> The homogenised baseline is conservative for the hot spot: in the real coil, heat spreads along the "
            "continuous copper wire from the end turns into the slot, so the detailed end-turn peak is lower and 155 °C is reached later. "
            "The baseline slightly under-predicts the winding mean, because the detailed model resolves the resin / bobbin barrier between "
            "copper and iron. The global energy balance of the detailed runs stays within −0.8 … +0.3 %.</p>")
    if len(have) == len(DET):
        dev = []
        for lp in have:
            b, dt = js[lp]["baseline"], js[lp]["detailed"]
            d = [(dt[k] / b[k] - 1) * 100 for k in ("t_winding_155C_s", "t_magnet_100C_s")
                 if isinstance(b.get(k), (int, float)) and isinstance(dt.get(k), (int, float))]
            if d:
                dev.append(f"{lp}: limit times {', '.join(f'{x:+.0f} %' for x in d)} in the detailed model")
        out += ('<p class="lead"><b>Verdict.</b> ' + "; ".join(dev) + ". In every case the baseline reaches the limit first, so it is "
                "conservative: close agreement at duty4, and a larger but safe-side margin at duty1, where the end-turn hot spot "
                "dominates. The baseline modelling is validated as a slightly conservative model, so duty2, duty3 and duty5, which have no detailed run, use the "
                "baseline mesh, while duty1 and duty4 report the detailed results. No detailed runs were made for duty2, duty3 and duty5: the detailed model will be redone later on "
                "the latest CAD.</p>")
    out += "".join(todo(f"detailed geometry at {lp}: results/detailed/{lp} (run in progress, DETAIL agent).") for lp in DET if lp not in have)
    return out


# ---------------------------------------------------------------- who heats whom (heat_budget.py)
BNAME = {"winding": "Winding", "copper": "Copper (coil, busbars, straps, t-bars)", "resin": "Resin", "bobbin": "Bobbin",
         "stator": "Stator", "housing": "Housing", "rotor": "Rotor iron", "magnets": "Magnets", "shaft": "Shaft",
         "bearings": "Bearings", "inair": "Internal air"}
BOWN = {"winding": "copper DC + AC", "copper": "copper DC + AC + busbar Joule", "stator": "iron", "rotor": "iron",
        "bearings": "friction", "inair": "windage"}
BORDER = list(BNAME)
WIND_CAVEAT = ('<div class="caveat"><b>Caveat: winding heat path.</b> The baseline winding is a homogenised isotropic block, '
               "k = 1 W/m·K (an anisotropic 0.77 / 200 W/m·K attempt diverged on the tet mesh), so heat cannot run along the copper from the "
               "end windings into the slot. The baseline therefore splits the winding heat about 50/50 between the stator and the end-space "
               "air (duty1 at 420 s: 277 W to each). At the same time the detailed model with real copper sends 69 % to the stator "
               "(398 W: bobbin path 228 W + resin path 170 W) and 31 % to the air (180 W: 126 W from the resin and 53 W directly from "
               "the copper). The baseline is therefore pessimistic for the "
               "winding hot spot (190 vs 171 °C) and slightly pessimistic for the magnets (extra heat reaches the rotor through the "
               "end-space air): its pass/fail verdicts are on the safe side, but its heat split is not physical; trust the detailed split. "
               "Recommendation: use the detailed coil or an anisotropic winding on the real CAD.</div>")
BUDGET_NOTE = ('<p class="note">Per part at a saved time, from the OpenFOAM interface heat flows: own loss (what the part makes), '
               "net heat received from its neighbours (+ = heated by others, − = passes heat on), heat to the surroundings, and "
               "stored = own + received + to surroundings (what warms the part). The interface flows cancel in total to within a few W. "
               "Stator and rotor have no flux monitor of their own; they take the mirror of their neighbours' flows.</p>")


def budget_time(src):
    """Last saved heat-flow time before the winding reaches 180 °C."""
    te = t_stop(src)
    ts = [t for t in hf_times(src) if te is None or t <= te + 1e-6]
    return ts[-1] if ts else None


def budget_lines(src, lp, t):
    b = budget(src, lp, t)
    if not b:
        return ""
    li = []
    for r in [r for r in BORDER if r in b]:
        v = b[r]
        own = f"{v['own']:.0f} W own ({BOWN[r]})" if v["own"] > 0.5 else "no own loss"
        rec = (f"<b>receives {v['received']:.0f} W</b> from neighbours" if v["received"] > 0.5
               else f"<b>gives {-v['received']:.0f} W</b> to neighbours" if v["received"] < -0.5 else "exchanges ~0 W")
        amb = f", {-v['ambient']:.0f} W to the surroundings" if v["ambient"] < -0.5 else ""
        li.append(f"<li><b>{BNAME[r]}</b>: {own}, {rec}{amb}; stores {v['stored']:.0f} W</li>")
    return "<ul>" + "".join(li) + "</ul>"


def budget_chart(panels, title):
    """panels: [(label, budget dict)] -> horizontal bars (own orange, received blue / passed-on purple), shared x scale."""
    regs = [r for r in BORDER if any(r in b for _, b in panels)]
    lim = max(max(abs(v["own"]), abs(v["received"])) for _, b in panels for v in b.values()) * 1.1
    fig, axs = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 0.42 * len(regs) + 1.4), squeeze=False, sharey=True)
    y = np.arange(len(regs))
    for ax, (lab, b) in zip(axs[0], panels):
        own = [b[r]["own"] if r in b else 0 for r in regs]
        rec = [b[r]["received"] if r in b else 0 for r in regs]
        ax.barh(y - 0.2, own, height=0.36, color="#ef8a3c", label="own loss")
        ax.barh(y + 0.2, rec, height=0.36, color=["#3a78c2" if x >= 0 else "#8e44ad" for x in rec], label="received (+) / passed on (−)")
        ax.scatter([b[r]["stored"] if r in b else np.nan for r in regs], y, marker="|", s=300, color="k", zorder=5, label="stored")
        ax.axvline(0, color="#444", lw=0.8); ax.set_xlim(-lim, lim); ax.set_title(lab, fontsize=10, loc="left"); ax.set_xlabel("W")
        ax.grid(axis="y", visible=False)
    axs[0, 0].set_yticks(y, [BNAME[r].split(" (")[0] for r in regs]); axs[0, 0].invert_yaxis()
    axs[0, 0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle(title, x=0.02, ha="left", fontweight="bold", fontsize=10.5)
    fig.tight_layout()
    return svg(fig, "Orange: own loss. Blue: net heat received from neighbouring parts; purple: net heat passed on. Black tick: stored.")


def budget_compare(lp):
    """Baseline and detailed budgets at the same saved time before either model reaches 180 °C."""
    d = f"detailed/{lp}"
    te = min(x for x in (t_stop(lp), t_stop(d)) if x is not None)
    ts = [t for t in hf_times(d) if t in hf_times(lp) and t <= te + 1e-6]
    if not ts:
        return todo(f"{lp}: no common heat-flow time for both models before the 180 °C cut-off.")
    t = ts[-1]
    pb, pd = budget(lp, lp, t), budget(d, lp, t)
    return (budget_chart([("baseline", pb), ("detailed geometry", pd)], f"{lp[-1]}. {DUTY[lp][0]} at {mmss(t/60)}")
            + f"<p><b>Baseline at {mmss(t/60)}</b></p>" + budget_lines(lp, lp, t)
            + f"<p><b>Detailed geometry at {mmss(t/60)}</b></p>" + budget_lines(d, lp, t))


# ---------------------------------------------------------------- content
def results_table():
    rows = []
    for lp in ORDER:
        name, n, T, tgt, ut, u6, sp = DUTY[lp]
        r = R[lp]
        cfd = ("<i>pending</i>" if not r else f"<b>{mmss(r['t_lim']/60)}</b> ({r['by']})" if r["t_lim"]
               else f"&gt; {mmss(r['t_end']/60)}")
        q = Q(lp)
        rows.append([lp[-1], name, n, f"{T:g}", f"{sum(groups(q)):.0f}" if q else "<i>pending</i>", f"{tgt} min",
                     mmss(ut), mmss(u6), mmss(sp), cfd, verdict(lp)])
    return table(["S.No", "Condition", "rpm", "N·m", "Heat (W)", "Target", "U666 test", "U666", "Spoke (Ferrite) ref.",
                  "<b>CFD Design9795_1</b> to first limit", "Verdict vs target"], rows)


def lp_rows():
    rows = []
    for lp in ORDER:
        d = LPALL.get(lp) or {}
        rows.append([lp, DUTY[lp][0], DUTY[lp][1], f"{DUTY[lp][2]:g}", f"{DUTY[lp][2]*DUTY[lp][1]*math.pi/30/1e3:.2f}",
                     f"{d['I_line']:.0f}" if "I_line" in d else "—", f"{DUTY[lp][3]} min",
                     f"{d['end_time']/60:.0f} min, Δt {d['dt']} s" if "end_time" in d else "<i>pending</i>"])
    return table(["Name", "Condition", "rpm", "N·m", "Shaft kW", "Line A rms", "Target", "CFD run length / step"], rows)


def method_section():
    M = MC.get("MAT", {})
    def k(r):
        if r not in M: return "?"
        v = M[r][2]
        return f"{v[0]:g} in-plane / {v[2]:g} axial" if isinstance(v, tuple) else (f"{v:g}" if isinstance(v, (int, float)) else esc(v))
    mat_rows = [[r, f"{M[r][0]:.0f}", f"{(M[r][1] if M[r][1] is not None else MC.get('cp_w', 0)):.0f}", k(r)]
                for r in ("housing", "stator", "rotor", "winding", "magnets", "shaft", "bearings", "inair") if r in M]
    L = MC.get("LAYERS", {})
    lay_rows = []
    for pair, why in ((("winding", "stator"), "bobbin wall + resin gap"), (("stator", "housing"), "shrink fit"),
                      (("magnets", "rotor"), "glue"), (("rotor", "stator"), "air gap (Taylor–Couette k per point)")):
        v = L.get(frozenset(pair))
        if v:
            t, kk = v
            lay_rows.append([" → ".join(pair), why, f"{t*1e3:g}", esc(kk) if isinstance(kk, str) else f"{kk:g}",
                             f"{kk/t:.0f}" if isinstance(kk, (int, float)) else "60–140"])
    h = HCFD.get("housing", {}).get("defaultFaces"); hs = HCFD.get("shaft", {}).get("defaultFaces")
    hrow = (f"per-face CFD h, housing mean {np.mean(h):.1f} (range {np.min(h):.1f}–{np.max(h):.1f}) W/m²K over {len(h):,} faces"
            + (f"; shaft mean {np.mean(hs):.1f}" if hs else "")) if h else "results/h_cfd.json missing"
    duty_k = [[lp, f"{d['k_gap']:.3f}", f"{d.get('taylor', 0):.0f}", f"{d['h_endspace']:.0f}", f"{d['k_inair']:.2f}"]
              for lp in ORDER if (d := LPALL.get(lp)) and "k_gap" in d]
    rows = [
        ("Geometry / mesh", "<b>the CFD mesh is the earlier v7 motor_65 geometry</b>, 8 conformal solid regions, 2.39 M tetrahedra (gmsh). "
         "Against Design9795_1: stack 65 vs 64 mm and shaft 30 vs 25 mm; outer diameter, bore and rotor match, same 12-slot/10-pole "
         "spoke-ferrite layout. Losses are the Design9795_1 values applied to the v7 volumes, so heat density and heat capacity are off by "
         "~1–2 % (about 1–2 % on run time). The detailed-geometry runs ([[detailed]]) check the winding model itself."),
        ("Start / ambient", f"uniform {MC.get('T_AMB', 313.15)-K:.0f} °C at t = 0; surroundings {MC.get('T_AMB', 313.15)-K:.0f} °C (slide 3)"),
        ("Outer convection", hrow + f" — from the 3D natural-convection CFD at ΔT 60 K (h ~ ΔT^0.25, not re-scaled); fallback uniform {c(MC, 'H_NAT', '{:g}')} W/m²K"),
        ("Radiation", f"grey body ε = {c(MC, 'EMISSIVITY', '{:g}')} to {MC.get('T_AMB', 313.15)-K:.0f} °C, re-linearised every step "
                      "(h_rad = εσ(Tw²+Ta²)(Tw+Ta)); fins see each other, so effective ε below 0.9 paint value"),
        ("Air gap", f"{c(LPS, 'GAP', '{:g}')} m gap at r = {c(LPS, 'R_ROT', '{:g}')} m: Ta = ω²r_mδ³/ν², Nu = 2 / 0.128Ta^0.367 / 0.409Ta^0.241, "
                    f"k_eff = (Nu/2)·{c(LPS, 'K_AIR', '{:g}')} W/m·K (Becker–Kaye, as in lumped motor-thermal tools)"),
        ("End spaces", f"h = 15 + 6.75 v^0.65 (v = rotor tip speed), applied as conducting air k = h·{c(LPS, 'L_END', '{:g}')} m; ρ×10 "
                       "for stable coupling (air heat capacity ~12 J/K vs ~7 kJ/K motor). The internal CFD of the earlier report found the "
                       "end-winding h about half this correlation, so this is optimistic for the end-turn hot spot."),
        ("Copper loss", f"from the Design9795_1 FEMM model, spread uniformly over the winding: the DC part at 100 °C scaled per cell every step "
                        f"as q(1 + {c(MC, 'JOULE_TC', '{:g}')}(T − 100 °C)) (the hot winding makes more heat), plus the AC part (skin / "
                        "proximity) as a constant source (it actually falls slightly with T, so holding it constant is slightly conservative)"),
        ("Iron / mechanical", "stator and rotor iron from the full-cycle FEMM iron-loss calculation with the Motor-CAD Steinmetz "
                              "coefficients and build factor 1.6, uniform in each region; bearing friction into the bearings, windage into the internal air"),
        ("Time step", "implicit Euler, fixed Δt per point (table in Scope); 2 coupling iterations for runs under 1 h, "
                      "1 for longer runs (make_case.py: SHORT = END_TIME &lt; 3600)"),
        ("Limits", f"winding hot spot (region maximum) {LIM_W:.0f} °C, magnet maximum {LIM_M:.0f} °C; time to limit = first crossing, linear between steps"),
        ("Energy check", "adiabatic 300 s test against the exact stored energy ([[changes]]) and generated − out = stored per run ([[heatpaths]])"),
    ]
    return (inputs(rows, "Model, assumptions and justification")
            + "<h3>Materials</h3>" + (table(["Region", "ρ (kg/m³)", "c (J/kg·K)", "k (W/m·K)"], mat_rows) if mat_rows else todo("make_case.py MAT not parsed"))
            + "<p>AlSi10Mg housing; M235-35A laminations conduct well in-plane and poorly across the stack; the winding is a homogenised "
              "copper (fill 0.51) + resin block, k 1.0 W/m·K isotropic (cross-turn ~0.77 plus a little along the wire); ferrite 4 W/m·K.</p>"
            + "<h3>Contact layers</h3>" + (table(["Interface", "Layer", "t (mm)", "k (W/m·K)", "Conductance (W/m²K)"], lay_rows) if lay_rows else todo("make_case.py LAYERS not parsed"))
            + "<h3>Speed-dependent internal coefficients per duty point</h3>"
            + (table(["Point", "Air-gap k_eff (W/m·K)", "Taylor number", "End-space h (W/m²K)", "End-space k (W/m·K)"], duty_k) if duty_k
               else todo("duty1..5 entries in loadpoints.json")))


# ---------------------------------------------------------------- document structure
STRESS = os.path.join(ROOT, "..", "OUTPUT", "rotor", "stress_2d", "report.html")
ALIAS = {"changes": "verif", "method": "bc", "heatpaths": "results", "detailed": "valid", "observe": "results"}


def fold(summary, html_):
    """Heavy media behind a click."""
    return f"<details><summary>{esc(summary)}</summary>{html_}</details>" if html_ else ""


def demote(h):
    """Reused blocks keep their own headings one level below the subsection heading."""
    return h.replace("<h4>", "<h5>").replace("</h4>", "</h5>").replace("<h3>", "<h4>").replace("</h3>", "</h4>")


def name_of(lp):
    return f"duty{lp[-1]}: {DUTY[lp][0]}, {DUTY[lp][2]:g} N·m @ {DUTY[lp][1]} rpm"


def first_limit(lp):
    r = R[lp]
    if not r:
        return None, None
    te = t_stop(SRC[lp])
    _, ev, _ = events(SRC[lp])
    hits = [(t, lab) for lab, t, _ in ev if t is not None]
    return min(hits) if hits else (None, f"none by {te:.0f} s")


EPS_CAVEAT = ('<div class="caveat"><b>Caveat: emissivity.</b> Every duty1–5 run used emissivity 0.7 on all outer faces, but the '
              "housing is bare machined aluminium (ε ≈ 0.1). Radiation carried about 60–70 % of the external heat loss in these runs, "
              "so <b>all times to limit are optimistic</b>, most for the long points (duty4, duty5) where the housing-to-ambient path "
              "sets the rise. duty4 was re-run at ε 0.1 on the baseline geometry (correction note under duty4 and on the fin page); duty1, 2, 3 and 5 stay at ε 0.7 (user decision) and are flagged.</div>")


def summary_table():
    rows = []
    for lp in ORDER:
        name, n, T, tgt, ut, u6, sp = DUTY[lp]
        t, lab = first_limit(lp)
        if not R[lp]:
            res, pf, mg = "<i>pending</i>", "<i>pending</i>", "—"
        elif t is None:
            res, pf, mg = f"no limit ({lab})", '<b class="ok">PASS</b>' if R[lp]["t_end"] >= tgt * 60 else "open", f"≥ {(R[lp]['t_end'] / 60 / tgt - 1) * 100:+.0f} % (run end)"
        else:
            m = t / 60 / tgt - 1
            res = f"<b>{mmss(t/60)}</b> — {lab[0].lower() + lab[1:]}"
            pf, mg = ('<b class="ok">PASS</b>', f"+{m*100:.0f} %") if m >= 0 else ('<b class="bad">FAIL</b>', f"{m*100:.0f} %")
        rows.append([f"duty{lp[-1]}", name, f"{T:g} N·m @ {n} rpm", f"{tgt} min", res, pf, mg,
                     ("detailed" if IS_DET(lp) else "baseline (simplified winding)") if R[lp] else "—", "0.7 ⚠" if R[lp] else "—", mmss(ut), mmss(sp)])
    return table(["Point", "Condition", "Operating point", "Target", "First limit event (CFD)", "Result", "Margin vs target",
                  "Thermal model", "Emissivity used", "U666 test", "Spoke (Ferrite) column"], rows,
                 "Results per duty point: time from a 40 °C cold start to the first limit (winding 155 °C or magnets 100 °C). "
                 "The U666 test and the Spoke (Ferrite) column of slide 3 are benchmarks from other motors.")


def key_findings():
    f = []
    for lp in HAVE:
        t, lab = first_limit(lp)
        d = FDJ.get(lp) or {}
        L = d.get("losses_W") or {}
        tgt = DUTY[lp][3]
        if t is None:
            continue
        verdict_ = "meets" if t / 60 >= tgt else "misses"
        cause = ""
        if L:
            cu = L.get("cu_dc", 0) + L.get("cu_ac", 0)
            rs = L.get("rotor", 0) + L.get("bearings", 0) + L.get("windage", 0)
            cause = (f"; copper makes {cu:.0f} of {d['total_W']:.0f} W" if "Winding" in lab
                     else f"; the rotor side receives {rs:.0f} W (rotor iron, bearings, windage) and has poor cooling paths, "
                          f"and AC copper is {L.get('cu_ac', 0):.0f} W at {d.get('f_el_Hz', 0):.0f} Hz")
        f.append(f"<b>duty{lp[-1]} {verdict_} its {tgt} min target</b>: {lab[0].lower() + lab[1:]} at {mmss(t/60)} "
                 f"({(t/60/tgt-1)*100:+.0f} %){cause}.")
    js = jload(os.path.join(RES, "detailed_vs_baseline.json")) or {}
    dv = []
    for lp in DET:
        b, dt = (js.get(lp) or {}).get("baseline") or {}, (js.get(lp) or {}).get("detailed") or {}
        k = "t_winding_155C_s"
        if isinstance(b.get(k), (int, float)) and isinstance(dt.get(k), (int, float)):
            dv.append(f"{lp} {(dt[k]/b[k]-1)*100:+.0f} %")
    if dv:
        f.append("<b>Model</b>: duty1 and duty4 use the detailed real-coil model; duty2, 3 and 5 use the baseline (simplified winding) "
                 "model, which the detailed runs show is conservative (time to 155 °C " + ", ".join(dv) + " in the detailed model). "
                 "In the detailed model the front and rear end windings stay within 1 °C; the baseline's rear hot spot is mostly "
                 "a smeared-winding artefact, but the rear remains the weaker cooled end (sections 3.1 and 3.4).")
    eb = []
    for lp in ORDER:
        d = jload(os.path.join(RES, SRC[lp], "energy_balance.json"))
        if d and "error_pct_range" in d:
            lo, hi = sorted(d["error_pct_range"]); eb.append(f"{lp} {lo:+.1f} to {hi:+.1f} %" + (" (outside 1 %)" if max(-lo, hi) > 1 else ""))
        elif d:
            eb.append(f"{lp} {d['error_pct']:+.2f} %" + (" (outside 1 %)" if abs(d["error_pct"]) > 1 else ""))
    pr = ETEST.get("production")
    if pr or eb:
        f.append("<b>Energy is conserved</b>: " + (f"adiabatic test {pr['error_pct']:+.1f} % with the production settings; " if pr else "")
                 + ("run balances " + ", ".join(eb) if eb else "") + " (the earlier report's model lost 49 %).")
    pend = [f"duty{lp[-1]}" for lp in ORDER if not R[lp]]
    if pend:
        f.append(f"<b>Pending</b>: {', '.join(pend)} are still to run on the validated baseline model.")
    return "<ol class=\"findings\">" + "".join(f"<li>{x}</li>" for x in f[:5]) + "</ol>"


def op_table(lp):
    name, n, T, tgt, ut, u6, sp = DUTY[lp]
    d, lpd = FDJ.get(lp) or {}, LPALL.get(lp) or {}
    o = d.get("operating", {})
    rows = [["Condition (slide 3)", name], ["Speed / torque / shaft power", f"{n} rpm / {T:g} N·m / {T*n*math.pi/30/1e3:.2f} kW"],
            ["Target duration", f"{tgt} min"],
            ["Outer-surface emissivity", "0.7 on all outer faces; the housing is bare Al (ε ≈ 0.1), so the times below are optimistic"], ["Benchmarks", f"U666 test {mmss(ut)}; Spoke (Ferrite) column {mmss(sp)} (other motors)"]]
    if d:
        rows += [["Line current / phase voltage", f"{o.get('I_line', 0):.0f} A rms / {o.get('V_ph_pk', 0):.1f} V pk (limit 49.4)"],
                 ["Total loss (FEMM) / Motor-CAD", f"{d['total_W']:.0f} W / {d.get('mcad_total_W', 0):.0f} W; largest term {esc(d.get('dominant_term', ''))}"]]
    if "end_time" in lpd:
        rows.append(["CFD run length / time step", f"{lpd['end_time']/60:.0f} min / {lpd['dt']} s"])
    rows.append(["Thermal model", MODEL(lp) + (f"; {DET_NOTE[lp]}" if IS_DET(lp) and lp in DET_NOTE else "")])
    out = table(["Item", "Value"], rows, f"duty{lp[-1]}: operating point and target")
    return out + (f'<p class="note">Note: {esc(RUN_NOTE[lp])}.</p>' if lp in RUN_NOTE and not IS_DET(lp) else "")


def anim_point(lp):
    nm = name_of(lp)
    st = "".join(section(SRC[lp], t, l) for t, l in section_times(lp))
    if IS_DET(lp):        # detailed model: its own temperature animation and the 3D viewer stills
        return (st or todo(f"results/{SRC[lp]}/slices_<t>/ section planes.")) + fold(
            "Animation and 3D views (detailed model)",
            media(os.path.join(AD, f"temp_det_{lp}.mp4"), f"Animation: temperature rise from the 40 °C start, {nm}, detailed model; fixed colour scale.")
            + "".join(media(os.path.join(FG, f"3d_det_{lp}_{v}.png"), f"{c}, {nm}, detailed model, last saved full field before the cut.")
                      for v, c in (("cut", "3D cut-away, all parts"), ("exploded", "Exploded half section (3D viewer)"),
                                   ("rotor", "Rotor group: rotor, magnets, shaft, bearings (3D viewer)"))
                      if os.path.exists(os.path.join(FG, f"3d_det_{lp}_{v}.png"))))
    t3 = max((int(d.rsplit("_", 1)[1]) for d in glob.glob(os.path.join(RES, "vtk3d", f"{lp}_*")) if d.rsplit("_", 1)[1].isdigit()), default=None)
    when = f"at {mmss(t3/60)} (last saved full field)" if t3 else "at the last saved full field"
    return (st or todo(f"results/{lp}/slices_<t>/ section planes.")) + fold(
        "Animations and 3D view",
        media(os.path.join(AD, f"temp_{lp}.mp4"), f"Animation: temperature rise from the 40 °C start, {nm}; fixed colour scale.")
        + media(os.path.join(AD, f"heat_{lp}.mp4"), f"Animation: heat flow between the parts, {nm}.")
        + media(os.path.join(FG, f"3d_{lp}.png"), f"3D cut-away coloured by temperature {when}, {nm}.")
        + media(os.path.join(AD, f"3d_{lp}.mp4"), f"Animation: 360° turn around the cut-away, {nm}."))


def budget_point(lp):
    key, lp = lp, SRC[lp]
    tb = budget_time(lp)
    if not tb:
        return todo(f"results/{lp}/heatflow_<t>.txt (heatpaths.sh).")
    hp = heatpath_svg(lp, tb)
    rows = []
    for t in saved_times(lp, "heatflow_*.txt"):
        f = flows(lp, t)
        if f and t <= tb:
            _, _, gen, o, _ = f
            rows.append([mmss(t / 60), f"{gen:.0f}", f"{o:.0f}", f"{gen-o:.0f}", f"{(gen-o)/gen*100:.0f} %"])
    return ((hp[0] if hp else "") + table(["Time", "Generated (W)", "To ambient (W)", "Stored (W)", "Stored share"], rows,
                                         f"duty{lp[-1]}: generated, lost and stored heat at the saved times")
            + BUDGET_NOTE + ("" if lp != key else WIND_CAVEAT)
            + f"<p>Per part at {mmss(tb/60)} (last saved heat flow before the 180 °C cut-off):</p>" + budget_lines(lp, key, tb)
            + (fold("Heat-budget animation", media(os.path.join(AD, f"budget_{key}.mp4"), f"Animation: heat budget per part over time, {name_of(key)}."))
               if lp == key else '<p class="note">Only one saved heat flow before the cut in the detailed run, so no budget animation.</p>'))


ENDW = os.path.join(RES, "endwinding_asym.md")
Z_END = 0.0325     # end turns: coil outside the stack, |z| > 32.5 mm (endwinding_asym.md)


def endwinding_fig(src, t):
    """Axial section of the detailed run with the front (drive end, z < 0) and rear end turns marked by their plane maxima."""
    d = os.path.join(RES, src, f"slices_{t}")
    f = os.path.join(d, "copper_x.vtk")
    if not os.path.exists(f):
        return ""
    pts, _, T = read_vtk(f)
    z = pts[:, 2]
    fr, re_ = T[z < -Z_END], T[z > Z_END]
    if not len(fr) or not len(re_):
        return ""
    fig, ax = plt.subplots(figsize=(10, 4.6))
    arts, lo, hi = _plane(ax, d, "x")
    for a in arts:
        a.set_clim(lo, hi)
    fig.colorbar(arts[0], ax=ax, shrink=0.8, label="temperature [°C]")
    for sel, Tm, lab in ((z < -Z_END, fr.max(), "front (drive end)"), (z > Z_END, re_.max(), "rear (non-drive end)")):
        P = pts[sel]
        x0, x1 = (-P[:, 2]).min() * 1000, (-P[:, 2]).max() * 1000
        y0, y1 = P[:, 1].min() * 1000, P[:, 1].max() * 1000
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="k", lw=1.2, ls="--"))
        ax.text((x0 + x1) / 2, y1 + 4, f"{lab}\nmax {Tm:.1f} °C", ha="center", va="bottom", fontsize=9, fontweight="bold")
    k = os.path.basename(src)
    ax.set_title(f"{k[-1]}. {DUTY[k][0]}, detailed model at {mmss(t/60)}: axial section x = 0 (rear left, drive end right)",
                 fontsize=10, loc="left")
    return png(fig, f"Front and rear end windings (coil outside the stack, |z| > 32.5 mm) on the axial section of the detailed model at "
                    f"{mmss(t/60)}: section-plane maxima front {fr.max():.1f} °C, rear {re_.max():.1f} °C (plane values, not volume maxima).")


def endwinding_part(lp):
    """Front vs rear end-winding temperature (detailed data), from results/endwinding_asym.md."""
    if not (IS_DET(lp) and os.path.exists(ENDW)):
        return ""
    rows = [[c.strip().replace("**", "") for c in l.strip().strip("|").split("|")] for l in open(ENDW, encoding="utf-8")
            if l.startswith(("| baseline " + lp, "| detailed " + lp))]
    ts = [t for t in slice_times(SRC[lp]) if t <= (t_stop(SRC[lp]) or 0) + 1e-6]
    fig = endwinding_fig(SRC[lp], ts[-1]) if ts else ""
    return ("<h4>Front vs rear end-winding temperature</h4>"
            "<p>In the detailed (real-wire) model the front and rear end windings stay within 1 °C of each other: each coil is one "
            "continuous copper conductor, so heat runs along the wire between the ends. The baseline's rear hot spot (+21 °C at duty1, "
            "+10 °C at duty4) is mostly an artefact of its smeared winding. The rear is still the weaker end: 6× further from a cold "
            "wall (33 vs 5 mm, 5× the end-space air), a bare barrel and a thin bolted cover outside it, and all the busbar / strap / "
            "terminal-bar Joule loss inside it; in the real motor this raises the whole winding rather than one end.</p>"
            + (table(["Model and time", "Front end turns max / mean (°C)", "Rear end turns max / mean (°C)", "Rear − front (max)"],
                     rows, f"duty{lp[-1]}: end-turn temperatures per end (results/endwinding_asym.md; baseline shown for reference)")
               if rows else "")
            + fig
            + "<p><b>Levers for the rear end:</b> fins over the bare rear barrel (the selected ring fins add 3 rings there); a gap pad or "
              "potting from the busbars / terminal bars to the rear housing wall; potting or a conductive fill across the 33 mm rear "
              "end space; a thicker cover (5 mm) with paste on the spigot.</p>"
            + fold("Full end-winding write-up (DETAIL agent)", md2html(ENDW)))


def duty_part(lp):
    head = (f'<p class="lead">{esc(DUTY[lp][0])} — {DUTY[lp][2]:g} N·m at {DUTY[lp][1]} rpm, target {DUTY[lp][3]} min. '
            f'Results from the <b>{MODEL(lp)}</b>.</p>')
    if not R[lp]:
        return head + op_table(lp) + todo(f"duty{lp[-1]} CFD run (pending): limit events, temperature charts, cross-sections, heat "
                                           "budget, observations and levers follow the same structure as the points above.")
    obs = re.sub(r"^<h3>.*?</h3>", "", observe(lp), count=1)
    parts = [("Operating point and target", op_table(lp)),
             ("Limit events", event_table([lp], head=False) + (eps01_note() if lp == "duty4" else "")),
             (f"Temperature history (to {T_STOP:.0f} °C winding)", chart_transient([lp])), ("Cross-sections", anim_point(lp)),
             ("Heat budget: who heats whom", budget_point(lp)), ("Observations and improvement levers", demote(obs) + endwinding_part(lp))]
    return head + "".join(f"<h4>{t}</h4>{h}" for t, h in parts)


def em_parts():
    """Split of the electromagnetic content: model, segregation, fields, causes."""
    model = ("<p>FEMM-Lab model of Design9795_1 (lab_model v3, 3 skew slices), copper winding of 2.95 mm wire, delta, 52 V, "
             "modulation index 0.95, winding and magnets at 100 °C, tuned to Motor-CAD. Iron loss over a full electrical cycle at the "
             "loaded operating point with the Motor-CAD Steinmetz coefficients (M235-35A, build factor 1.6), rotor iron in the rotor "
             "frame; AC copper from the slot leakage field (skin / proximity).</p>"
             + table(["", "Earlier report (v7 map)", "This report (Design9795_1)"], [
                 ["Copper", "DC only, R at 100 °C", "AC copper (skin / proximity) from FEMM"],
                 ["Iron", "single no-load snapshot scaled by |ψ|²/ψm², KH 0.0177, KE 6.2e-5, build 1.5",
                  "full electrical cycle at the loaded operating point, Motor-CAD Steinmetz coefficients, build factor 1.6"],
                 ["Rotor iron", "10 % of stator", "computed in the rotor frame"],
                 ["Design", "motor_65 v7", "Design9795_1 (copper), 64 mm stack, tuned to Motor-CAD"]], "Loss model: earlier report vs this report")
             + "<h4>Materials and factors audit</h4>" + audit_table())
    seg = ""
    if FDJ:
        rows = []
        for lp in ORDER:
            d = FDJ.get(lp)
            if d:
                o, L = d.get("operating", {}), d.get("losses_W", {})
                rows.append([lp, d["rpm"], f"{d['torque_Nm']:g}", f"{d['f_el_Hz']:.0f}", f"{o.get('I_line', 0):.0f}",
                             f"{o.get('id_phase_pk', 0):.0f} / {o.get('iq_phase_pk', 0):.0f}", f"{o.get('V_ph_pk', 0):.1f}"]
                            + [f"{L.get(k, 0):.0f}" for k in ("cu_dc", "cu_ac", "stator", "rotor", "bearings", "windage")]
                            + [f"<b>{d['total_W']:.0f}</b>", f"{d.get('mcad_total_W', 0):.0f}", esc(d.get("dominant_term", ""))])
        seg = table(["Point", "rpm", "N·m", "f el (Hz)", "I line (A rms)", "id / iq (A pk)", "V ph pk (max 49.4)", "Cu DC", "Cu AC",
                     "Stator Fe", "Rotor Fe", "Bearings", "Windage", "Total (W)", "Motor-CAD (W)", "Largest term"], rows,
                    "Loss segregation per duty point (FEMM, W)")
    seg += (media(os.path.join(FD, "loss_segregation.png"), "Loss segregation per duty point (FEMM, Design9795_1).")
            + chart_losses() + loss_table()
            + media(os.path.join(FD, "dq_limits.png"), "d-q current plane with the voltage ellipse at each speed and the current limit: "
                    "duty1 is current/torque driven, duty4 sits on the voltage ellipse."))
    fields = ""
    for lp in EMF:
        mp4 = os.path.join(FD, f"flux_{lp}.mp4")
        fields += media(mp4, f"Animation: |B| (0–2 T) and flux lines over one electrical period, {lp}, rotor turning, phase-current marker.")
    for f_, cap in (("iron_density_duty1_vs_duty4.png", "Iron-loss density (W/kg) per element from the full-cycle B waveforms (Motor-CAD Steinmetz)."),
                    ("waveforms_spectrum_duty1_vs_duty4.png", "Tooth, tip, yoke and rotor B waveforms and their harmonic spectra."),
                    ("slot_leakage_duty1_vs_duty4.mp4", "Animation: slot leakage B at the wires over the cycle (AC copper loss ~ f² B²).")):
        fields += media(os.path.join(FD, f_), cap)
    stats = ""
    if FSTAT:
        pts = [lp for lp in ORDER if isinstance(FSTAT.get(lp), dict)]
        cols = {lp: dict((k, v) for k, v in flat_rows(FSTAT[lp])) for lp in pts}
        keys = list(dict.fromkeys(k for lp in pts for k in cols[lp]))
        stats = table(["Quantity"] + pts, [[k] + [cols[lp].get(k, "—") for lp in pts] for k in keys], "Field statistics (FEMM, unskewed centre slice)")
    fields = fold("Flux, iron-loss density and slot-leakage animations", fields) + fold("Field statistics table", stats)
    why = ""
    for lp in ORDER:
        d, q = FDJ.get(lp), DQ.get(lp)
        if not d:
            continue
        why += (f"<h4>{name_of(lp)}</h4><p><b>Cause.</b> {esc(d['reason'])}</p><p><b>Thermal consequence.</b> {esc(d['cfd_consequence'])}</p>"
                f"<p><b>Electromagnetic levers.</b> {esc(d['em_levers'])}</p>")
        if q:
            why += (f"<p class=\"note\">Voltage {q['V_op']:.1f} of {q['V_max']:g} V pk (with id = 0 it would need {q['V_same_iq_id0']:.0f} V); "
                    f"current angle {q['gamma_deg']:.0f}°, d-axis flux reduced {q['psi_d_reduction_pct']:.0f} %, power factor {q['pf']:.2f}.</p>")
    return model, seg, fields, why or todo("results/femm_duty/femm_duty.json")


def air_parts():
    ext = ("<p>One CFD of the still air around the motor (results/air, housing at ΔT 60 K): no fan or vehicle air speed, so the same flow "
           "applies to every duty point. Its per-face heat-transfer coefficient is the outer boundary condition of every thermal run.</p>")
    ext += fold("External air: animations and stills", "".join(
        media(os.path.join(AD, f"ext_air_{ax}.mp4"), f"Animation: air around the motor, {lab} (real time).")
        + media(os.path.join(FG, f"ext_air_{ax}.png"), f"Air speed and streamlines around the motor, {lab}.")
        for ax, lab in (("z", "radial mid-plane z = 5 mm"), ("x", "axial mid-plane, rear left / drive end right"))))
    inn = ("<p>Internal air (end spaces and air gap) per speed. In the thermal runs the end-space air is a conducting solid with a "
           "speed-dependent coefficient (2.2); these CFD fields show the flow pattern behind it.</p>")
    for src in ("duty1", "duty4"):
        rpm = DUTY[src][1]
        users = [f"duty{lp[-1]}" for lp, (s_, _) in INAIR.items() if s_ == src]
        why = INAIR.get(src, (src, ""))[1]
        inn += f"<h4>{rpm} rpm (used for {', '.join(users)})</h4>"
        if not os.path.isdir(os.path.join(RES, f"inair_{src}")):
            inn += todo(f"results/inair_{src}")
            continue
        inn += (f'<p class="note">{esc(why[0].upper() + why[1:])}.</p>' if why else "")
        inn += "".join(media(os.path.join(FG, f"inair_{ax}_{src}.png"), f"Inside air at {rpm} rpm, {lab}.")
                       for ax, lab in (("z", "drive-end space z = −40 mm"), ("x", "axial mid-plane")))
        inn += fold(f"Animations at {rpm} rpm", "".join(
            media(os.path.join(AD, f"inair_{ax}_{src}.mp4"), f"Animation: inside air at {rpm} rpm, {lab} (slow motion).")
            for ax, lab in (("z", "drive-end space z = −40 mm"), ("x", "axial mid-plane"))))
    for lp in ("duty2", "duty3", "duty5"):
        inn += f'<p class="note">{lp} ({DUTY[lp][1]} rpm): {esc(INAIR[lp][1])}.</p>'
    return ext, inn


def valid_parts():
    """Detailed-geometry section split into method / comparison / verdict.
    ponytail: splits detailed_section()'s HTML at its first chart and at the verdict paragraph; refactor if that layout changes."""
    h = detailed_section()
    a = h.find('<figure class="chart">'); b = h.find('<p class="lead"><b>Verdict.')
    e = h.find("Adiabatic energy test, detailed mesh"); e = h.rfind("<table", 0, e) if e > 0 else -1
    if a < 0:
        return h, "", "", ""
    e = e if 0 < e < a else a
    st = "".join(media(os.path.join(FG, f"3d_det_{lp}_{v}.png"), f"Detailed model, {name_of(lp)}: {cap} at the last saved field before the "
                       f"{T_STOP:.0f} °C cut (from the 3D viewer).")
                 for lp in DET for v, cap in (("exploded", "exploded half section, all parts"), ("rotor", "rotor group (rotor, magnets, shaft, bearings)"))
                 if os.path.exists(os.path.join(FG, f"3d_det_{lp}_{v}.png")))
    return h[:e], h[e:a], (h[a:b] if b > 0 else h[a:]) + st, (h[b:] if b > 0 else "")


PEND = [lp for lp in ORDER if not R[lp]]


def verdict_line():
    out = []
    for lp in ORDER:
        t, lab = first_limit(lp) if R[lp] else (None, None)
        if not R[lp]:
            out.append(f"{lp} pending")
        elif t is None:
            out.append(f"{lp} passes (no limit reached)")
        else:
            out.append(f"{lp} {'passes' if t/60 >= DUTY[lp][3] else 'fails'} ({lab[0].lower() + lab[1:]} at {mmss(t/60)}, target {DUTY[lp][3]} min)")
    return "; ".join(out) + ". The magnet-limited failures need combined measures on the rotor-side heat, AC copper and external cooling."


def conclusions():
    rows = []
    L4 = (FDJ.get("duty4") or {}).get("losses_W") or {}
    hy = ((FSTAT or {}).get("duty4") or {}).get("hysteresis_share_pct")
    if R.get("duty4") and L4:
        rows += [["1", "duty4 (fails)", "AC copper: parallel strands of half the wire diameter",
                  f"Cu AC {L4.get('cu_ac', 0):.0f} W → ≈ {0.25*L4.get('cu_ac', 0):.0f} W (eddy ~ d²); the largest single cut at top speed"],
                 ["2", "duty4 (fails)", "Rotor-side heat: low-friction / lower-preload bearings, rotor end vanes",
                  f"bearings {L4.get('bearings', 0):.0f} W + windage {L4.get('windage', 0):.0f} W + rotor iron {L4.get('rotor', 0):.0f} W "
                  "heat the rotor and magnets, which set the limit; −30 % bearing loss ≈ +21 % time to the magnet limit"],
                 ["3", "duty4 (fails)", "External cooling: longer fins or forced air",
                  "housing → ambient is the bottleneck (section 3.4 levers); see the fin optimisation for the bare-aluminium housing"],
                 ["4", "duty4 (fails)", "Iron: 0.20 mm laminations instead of 0.35 mm",
                  f"stator iron {L4.get('stator', 0):.0f} W" + (f", {100-hy:.0f} % of it eddy loss" if hy is not None else "") + " → eddy ×0.33"],
                 ["5", "duty4", "Voltage margin: higher DC link, less battery sag",
                  "the point sits on the voltage limit (98 % field-weakening current); 48 V adds 38 W, 44 V adds 81 W"]]
    for lp in HAVE:
        t, lab = first_limit(lp)
        L = (FDJ.get(lp) or {}).get("losses_W") or {}
        if lp == "duty4" or t is None or t / 60 >= DUTY[lp][3] or "Magnet" not in lab or not L:
            continue
        rows.append(["", f"{lp} (fails)", "Rotor-side heat and magnet cooling: low-friction bearings, rotor end vanes, iron grade",
                     f"magnets reach 100 °C at {mmss(t/60)}, so it needs {(DUTY[lp][3]*60/t-1)*100:.0f} % longer to reach {DUTY[lp][3]} min; rotor iron "
                     f"{L.get('rotor', 0):.0f} W + bearings {L.get('bearings', 0):.0f} W + windage {L.get('windage', 0):.0f} W heat the rotor "
                     f"directly and stator iron {L.get('stator', 0):.0f} W raises the air gap side; the duty4 levers 2–4 apply with smaller gains"])
    ok = [lp for lp in HAVE if first_limit(lp)[0] is None or first_limit(lp)[0] / 60 >= DUTY[lp][3]]
    bad = [lp for lp in HAVE if lp not in ok]
    rows += [["", ", ".join(ok) + " (pass)", "Winding exits: end-turn potting / end-space airflow, thinner or higher-k slot liner, impregnation",
              "expected effects per point in the section 3 levers; keeps the margin under battery sag"],
             ["", "all", "Rear end cooling: fins over the bare rear barrel, busbar-to-housing gap pad, potting across the rear end space, thicker cover",
              "the rear end space is 6× longer to a cold wall and holds all the busbar loss (end-winding subsections in 3.1 and 3.4)"],
             ["", "all", "Calibrate contacts (bobbin, shrink fit) and end-space h against the U666 test at duty1", "removes the main model uncertainty"],
             *([["", ", ".join(PEND), "Run on the validated baseline model", "completes the duty table"]] if PEND else [])]
    for i, r in enumerate(rows, 1):
        r[0] = str(i)
    return (f"<p>{', '.join(ok) or 'No point'} meet{'s' if len(ok) == 1 else ''} the target; {', '.join(bad) or 'none'} "
            f"{'does' if len(bad) == 1 else 'do'} not. "
            + ("duty4 needs several of the levers below together: each one alone falls short of the ≈ 70 % longer time it needs. " if "duty4" in bad else "")
            + "</p>"
            + table(["Rank", "Point", "Lever", "Why / expected effect (first-order, from this report)"], rows,
                    "Ranked improvement levers; effects are first-order estimates to be confirmed by a re-run"))


def limitations():
    return """<ul><li><b>Emissivity 0.7 on all outer faces</b> while the housing is bare machined aluminium (ε ≈ 0.1): radiation was about 60–70 % of the external heat loss, so every time to limit is optimistic, most at duty4 and duty5 (duty4 re-run at ε 0.1: correction note under duty4).</li>
<li><b>Mesh is the old v7 motor_65 geometry</b>, not the Design9795_1 CAD: stack 65 vs 64 mm, shaft 30 vs 25 mm; outer diameter, bore and rotor match. Losses come from Design9795_1. Effect about 1–2 % on temperatures and run times.</li>
<li><b>Homogenised isotropic winding</b> (k 1.0 W/m·K, uniform copper loss per volume) in the baseline; the anisotropic 0.77 / 200 W/m·K version diverged on the tet mesh. Heat cannot run along the copper from the end windings into the slot, so the baseline splits the winding heat about 50/50 between stator and end-space air, where the detailed model gives 69 / 31 % (duty1, 420 s). The baseline is pessimistic for the winding hot spot (190 vs 171 °C) and slightly for the magnets: verdicts are safe-side, but the heat split is not physical. Use the detailed coil or an anisotropic winding on the real CAD.</li>
<li><b>End-space air as a conducting solid</b> from a correlation; the earlier internal CFD found h about half the correlation, so the end-turn hot spot is optimistic.</li>
<li><b>Assumed contacts</b> (bobbin, shrink fit, glue); the bobbin layer controls the copper-to-iron path.</li>
<li><b>Still-air external h</b> from one CFD at ΔT 60 K; no mounting conduction, no vehicle air speed. A dyno or vehicle mounting plate is a heat sink the model does not have (conservative).</li>
<li><b>Constant torque and speed</b> per point; no drive cycle, nominal 52 V losses (battery sag raises copper loss, most at duty4).</li>
<li><b>Limit definition</b>: the CFD limit is the hottest cell; a test thermistor in the end winding reads later.</li>
<li><b>Benchmarks</b>: the Spoke (Ferrite) column is a different motor (multi-strand distributed winding, no busbar): a benchmark, not a prediction for this design.</li>
<li><b>Internal air at duty4</b> is an approximate solution (residuals ~1e-3); duty2 reuses the duty1 field scaled by speed.</li></ul>"""


def structural():
    ptr = (f'<p>A separate 2D centrifugal stress study of a 10-pole spoke-ferrite rotor lamination (106 mm OD, 25 mm bore, 12 000 rpm × 1.2 '
           f'overspeed, glue intact / cracked cases) exists in <code>{esc(rel(STRESS))}</code>. Whether its geometry is exactly '
           "Design9795_1 was not checked in this work.</p>") if os.path.exists(STRESS) else ""
    return ("<p><b>No structural analysis was done in this work.</b> Rotor bridge stress, magnet retention, shaft and bearing loads, "
            "and thermal stresses from the temperatures above are outside its scope.</p>" + ptr)


def parts():
    """Every section's content, in document order: [(part id, title, summary, [(sub id, title, html)])]."""
    em_model, em_seg, em_fields, em_why = em_parts()
    ext, inn = air_parts()
    v_method, v_verif, v_cmp, v_verdict = valid_parts()
    f_cons, f_scr, f_why, f_res = fin_parts()
    PARTS = [
        ("summary", "Executive summary", None, [
            ("results-table", "Results per duty point", EPS_CAVEAT + summary_table()),
            ("findings", "Key findings", key_findings())]),
        ("em", "Electromagnetic analysis (FEMM)",
         "Where the heat comes from. Losses per duty point from the FEMM model of Design9795_1, tuned to Motor-CAD: copper dominates "
         "at low speed (duty1 610 of 709 W); at top speed (duty4) the loss spreads over AC copper, stator iron and bearings, because "
         "the point sits on the voltage limit and needs heavy field-weakening current.", [
            ("em-model", "Model and materials", em_model),
            ("em-seg", "Loss segregation per point", em_seg),
            ("em-fields", "Flux, iron-loss density and slot-leakage fields", em_fields),
            ("em-why", "Why the losses are high at each point", em_why)]),
        ("cfd", "Thermal CFD method",
         "Transient 3D conduction model in OpenFOAM 12: 8 solid regions, still air at 40 °C (natural convection + radiation), "
         "uniform 40 °C start, Design9795_1 losses with temperature-dependent DC copper. Energy conservation is verified to "
         + (f"{ETEST['production']['error_pct']:+.1f} % " if ETEST.get("production") else "")
         + "with the production settings; the earlier report's model lost 49 % of the heat.", [
            ("geom", "Geometry and mesh", "<p>Transient 3D conduction model of Design9795_1 (12-slot / 10-pole spoke-ferrite PMSM, copper, "
             "52 V, delta). Each duty point is held at constant torque and speed until a limit is reached or the run length (≥ the target "
             "duration) ends.</p>" + lp_rows()),
            ("bc", "Boundary conditions, materials and losses applied", EPS_CAVEAT + method_section()),
            ("solver", "Solver settings", "<p>OpenFOAM 12 foamMultiRun, solid module per region, implicit Euler, fixed time step per point "
             "(table above); region coupling iterated to " + esc((ETEST.get("production") or {}).get("setting", "the production residual control"))
             + ". Runs on 4 MPI ranks.</p>"),
            ("verif", "Verification: energy tests and balances", energy_section())]),
        ("results", "Thermal results per load point",
         "One subsection per duty point with the same structure. Charts and animations end when the winding maximum reaches "
         f"{T_STOP:.0f} °C (or at the end of the run). " + "; ".join(
             f"duty{lp[-1]}: " + (("first limit " + mmss(first_limit(lp)[0] / 60)) if R[lp] and first_limit(lp)[0] else "pending")
             for lp in ORDER) + ".",
         [(f"res-{lp}", name_of(lp), duty_part(lp)) for lp in ORDER]),
        ("air", "Airflow",
         "Natural convection around the motor sets the outer cooling for every point; the internal air flow (driven by the rotor) "
         "carries heat from the end turns to the housing and grows with speed.", [
            ("air-ext", "External natural convection", ext), ("air-int", "Internal air per speed", inn)]),
        ("valid", "Detailed geometry validation",
         "The baseline model treats the winding as a homogenised copper-resin block. A second model with the real coils, resin, bobbins, "
         "busbars, straps and t-bars was run at duty1 and duty4 to check it. The baseline reaches every limit first, so it is "
         "conservative; it is used for all points.", [
            ("valid-method", "Method, mesh and verification", v_method + v_verif),
            ("valid-cmp", "Baseline vs detailed comparison", v_cmp),
            ("valid-verdict", "Verdict", v_verdict or todo("detailed runs at both points"))]),
        ("fins", "Fin optimisation (duty4)",
         "duty4 is limited by the housing-to-ambient path. Larger housing fins within the 205 mm envelope were screened analytically "
         "at the real bare-aluminium emissivity (ε 0.1), and one variant goes to CFD.", [
            ("fins-cons", "Constraints", f_cons), ("fins-screen", "Analytical screen", f_scr),
            ("fins-choice", "Selected variant", f_why), ("fins-cfd", "CFD result", f_res)]),
        ("struct", "Structural", "Not part of this work.", [("struct-note", "Status", structural())]),
        ("concl", "Conclusions and recommendations",
         verdict_line(), [("levers", "Ranked improvement levers", conclusions())]),
        ("limits", "Limitations and assumptions", "What the model does not include and how each simplification biases the result.",
         [("limits-list", "Limitations", limitations())]),
        ("appendix", "Appendix: files, scripts and settings", None, [("files", "Files and how to rerun", table(["File", "Does"], [
            ["scripts/loadpoints.py → loadpoints.json", "duty1..5 heat sources and speed-dependent coefficients"],
            ["results/losses_9795.json / .md", "Design9795_1 FEMM vs Motor-CAD losses and the materials/factors audit"],
            ["scripts/make_case.py, run_case.sh, duty_runs.sh", "one OpenFOAM case per point (4 ranks)"],
            ["scripts/energy_test.sh, energy_check.sh, energy_balance.py", "energy tests → results/energy_test.json, per-run balances"],
            ["scripts/slices.sh, heatpaths.sh", "results/&lt;lp&gt;/slices_&lt;t&gt;/, heatflow_&lt;t&gt;.txt"],
            ["scripts/heat_budget.py, animate_budget.py", "per-part heat budget (who heats whom) and its animation"],
            ["scripts/femm_duty_*.py → results/femm_duty/", "FEMM duty study: loss segregation, d-q limits, flux / leakage animations"],
            ["scripts/duty_visuals.sh, animate_temp.py, animate_heat.py, render3d.py", "animations and stills → results/anim_duty/, figs_duty/"],
            ["scripts/det_run.sh, compare_detailed.py", "detailed-geometry runs and comparison"],
            ["scripts/make_report_duty.py", "this report: <code>.venv/Scripts/python -I scripts/make_report_duty.py</code>"]],
            "Files and scripts"))]),
    ]
    return PARTS, (v_method, v_verif, v_cmp, v_verdict)


def numbers(PARTS):
    """Parts 1..n (summary and appendix unnumbered), subsections n.m."""
    num, n = {}, 0
    for pid, _, _, subs in PARTS:
        if pid not in ("summary", "appendix"):
            n += 1; num[pid] = str(n)
            for m, (sid, _, _) in enumerate(subs, 1):
                num[sid] = f"{n}.{m}"
    return num


def captions(body, k):
    """Number figures and tables in order; k = [figures, tables] carried across pages."""
    def fig(m):
        k[0] += 1
        return f"<figcaption><b>Figure {k[0]}.</b> "
    def tab(m):
        k[1] += 1
        return f'<table><caption><b>Table {k[1]}.</b> {m[1]}</caption>'
    return re.sub(r'<table data-cap="(.*?)">', tab, re.sub(r"<figcaption>", fig, body))


def titleblock(stamp):
    return f"""<table class="titleblock"><tr><th>Motor</th><td>12-slot / 10-pole spoke-ferrite PMSM, copper winding, 52 V delta</td></tr>
<tr><th>Design</th><td>Design9795_1</td></tr><tr><th>Scope</th><td>Electromagnetic losses (FEMM) and transient thermal CFD (OpenFOAM 12) at the five slide-3 vehicle duty points; 40 °C ambient, natural convection</td></tr>
<tr><th>Date</th><td>{stamp:%Y-%m-%d}</td></tr><tr><th>Revision</th><td>auto-generated {stamp:%Y-%m-%d %H:%M} from the results in this repository</td></tr></table>"""


FINS = os.path.join(RES, "fins")


EPS01 = next((c for c in ("duty4_eps01", "fins/baseline_eps0.1") if os.path.isdir(os.path.join(RES, c, "postProcessing"))), None)


def eps01_note():
    """duty4 re-run with the bare-aluminium emissivity 0.1 (baseline geometry): correction note against the ε 0.7 runs."""
    if not EPS01:
        return todo("duty4 re-run at ε 0.1 (results/duty4_eps01).")
    _, e01, _ = events(EPS01)
    _, e07, _ = events("duty4")
    eb = jload(os.path.join(RES, EPS01, "energy_balance.json")) or {}
    rows, fac = [], {}
    for (lab, t1, _), (_, t7, _) in zip(e01, e07):
        if t1 and t7:
            fac[lab] = t1 / t7
        rows.append([lab, f"{mmss(t7/60)} ({t7:.0f} s)" if t7 else "—", f"{mmss(t1/60)} ({t1:.0f} s)" if t1 else "—",
                     f"{(t1/t7-1)*100:+.0f} %" if t1 and t7 else "—"])
    _, ed, _ = events(SRC["duty4"])
    est = "; ".join(f"{lab[0].lower() + lab[1:]} ≈ {mmss(td*fac[lab]/60)}" for lab, td, _ in ed if td and lab in fac)
    return ("<p><b>Bare-aluminium correction (ε 0.1).</b> duty4 was re-run with the real emissivity of the bare machined housing, on "
            f"the baseline geometry (results/{EPS01}). Against the same geometry at ε 0.7:</p>"
            + table(["Event", "Baseline geometry, ε 0.7", "Baseline geometry, ε 0.1", "Change"], rows,
                    "duty4: effect of the housing emissivity on the limit times (baseline geometry)")
            + (f"<p>Run energy balance {eb['error_pct']:+.2f} %. " if "error_pct" in eb else "<p>")
            + (f"Applying the same ratios to the detailed-model result gives a first-order bare-aluminium estimate: {est}. " if est else "")
            + "The fins below act on this bare-aluminium case.</p>")


def fin_parts():
    cons = table(["Constraint", "Value"], [
        ["Fin profile", "tapered, 4 mm at the root to 2.5 mm at the tip"],
        ["Envelope", "outer diameter ≤ 205 mm (fin tips ≤ r 102 mm); the cable glands may protrude"],
        ["Surface", "bare machined aluminium, ε ≈ 0.1 (no paint or anodising)"],
        ["Cooling", "natural convection only (no fan, no vehicle air speed)"],
        ["Span", "barrel z −44 to +67.5 mm; fins cut back to r 18 mm round the 4 cable-gland axes"],
        ["Existing housing", "10 annular fins, 2.5 mm uniform, 8 mm proud, pitch 8 mm"]], "Fin optimisation constraints (duty4)")
    md = os.path.join(FINS, "screen.md")
    scr = (("<p>Analytical screen without CFD: UA at a 100 °C wall and 40 °C ambient. Convection from parallel-plate correlations "
            "(rings: channel height = fin OD; axial fins: buoyancy reduced for the channel orientation round a horizontal cylinder) and "
            "Churchill–Chu for the bare barrel, both calibrated on the external-air CFD of the existing housing; radiation at ε 0.1 from the "
            "fin-array envelope. Script: scripts/fin_screen.py.</p>" + md2html(md)) if os.path.exists(md) else todo("results/fins/screen.md"))
    sj = jload(os.path.join(FINS, "screen.json")) or {}
    al = {v["name"]: v for v in sj.get("all", [])}
    ch, ax, b0 = al.get("ring H16 p11.5"), max((v for v in al.values() if v.get("kind") == "axial tapered"), key=lambda v: v["UA_WK"], default=None), \
        al.get("baseline (CAD fins, 2.5 mm uniform)")
    why = ("<p>Selected variant: <b>tapered rings, H 16 mm, pitch 11.5 mm, full span with gland cut-outs</b>"
           + (f": UA {ch['UA_WK']:.2f} W/K vs {b0['UA_WK']:.2f} W/K for the existing fins (×{ch['UA_WK']/b0['UA_WK']:.1f}), "
              f"+{ch['d_mass_kg']:.2f} kg aluminium." if ch and b0 else ".") + "</p>"
           + (f"<p class=\"note\">The screen rates the best axial variant ({esc(ax['name'])}) higher, at {ax['UA_WK']:.2f} W/K "
              f"(+{ax['d_mass_kg']:.2f} kg).</p>" if ax else "")
           + "<p><b>Why rings.</b> The axial-fin screen value rests on the least certain correlation. On a horizontal cylinder in natural "
             "convection the buoyant flow rises round the circumference: ring fins leave vertical channels open for it, whereas "
             "longitudinal (axial) fins block that circumferential flow, so real axial performance is usually far below the screen value. "
             "Rings are the robust choice and also suit the 4 → 2.5 mm taper. Axial fins will be tested with CFD on the real motor CAD.</p>")
    cfd, cj = os.path.join(FINS, "summary.md"), jload(os.path.join(FINS, "summary.json"))
    res = eps01_note() + (md2html(cfd) if os.path.exists(cfd) else
                          table(["Quantity", "Value"], flat_rows(cj), "Fin CFD summary (results/fins/summary.json)") if cj else
                          todo("duty4 CFD with the selected fins at ε 0.1 (DETAIL agent, results/fins/summary.*)."))
    note = '<p class="note">Further fin variants will be done on the real motor CAD.</p>'
    return cons + note, scr, why, res + note


def build():
    stamp = datetime.datetime.now()
    PARTS, _ = parts()
    num = numbers(PARTS)
    lab = lambda i, t: f"{num[i]} {t}" if i in num else t
    toc = "".join(f'<li><a href="#{pid}">{esc(lab(pid, t))}</a><ol>'
                  + "".join(f'<li><a href="#{sid}">{esc(lab(sid, st))}</a></li>' for sid, st, _ in subs) + "</ol></li>"
                  for pid, t, _, subs in PARTS)
    back = '<p class="back"><a href="#toc">↑ Back to contents</a></p>'
    body = ""
    for pid, t, summ, subs in PARTS:
        body += f'<section id="{pid}"><h2>{esc(lab(pid, t))}</h2>' + (f'<p class="summary">{summ}</p>' if summ else "")
        for sid, st, h in subs:
            body += f'<section id="{sid}"><h3>{esc(lab(sid, st))}</h3>{demote(h) if pid != "results" else h}{back}</section>'
        body += "</section>"
    body = re.sub(r"\[\[(\w+)\]\]", lambda m: f"section {num.get(ALIAS.get(m[1], m[1]), '?')}", body)
    k = [0, 0]
    body = captions(body, k)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Design9795 Duty Thermal</title><style>{CSS}</style></head><body>
<header><h1>Design9795_1 Vehicle-Duty Thermal Report</h1>{titleblock(stamp)}</header>
<div class="layout"><aside class="side"><div class="sidehead">Contents</div><ol>{toc}</ol></aside>
<main><nav id="toc"><h2>Contents</h2><ol class="toc">{toc}</ol></nav>{body}</main></div></body></html>"""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "Design9795_Duty_Thermal_CFD_Report.html")
    open(path, "w", encoding="utf-8").write(page)
    print(f"wrote {path}  ({os.path.getsize(path)/1e6:.2f} MB); figures {k[0]}, tables {k[1]}; CFD results for: {HAVE or 'none'}")


CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--line:#e2e2e2;--card:#f6f7f9;--accent:#1f4e8c;--todo:#a15c00;--ok:#2e7d32;--bad:#c62828}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141517;--fg:#e8e8e8;--muted:#a0a4aa;--line:#2c2f33;--card:#1d1f22;--accent:#7fb0ff;--todo:#ffb74d;--ok:#81c784;--bad:#ef9a9a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{padding:40px 16px 24px;max-width:980px;margin:auto;border-bottom:1px solid var(--line)}h1{margin:0 0 6px;font-size:28px}
.meta{color:var(--muted);font-size:13px}nav{max-width:980px;margin:auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;border-bottom:1px solid var(--line)}
nav a{color:var(--accent);text-decoration:none}main{max-width:980px;margin:auto;padding:0 16px 60px}section{padding-top:22px}
h2{font-size:21px;border-left:4px solid var(--accent);padding-left:10px;margin:18px 0 10px}h3{font-size:16px;margin:18px 0 6px}
.lead{font-size:16px}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--card);font-weight:600}
figure{margin:14px 0}figure video{display:block;max-width:100%;max-height:640px;margin:auto;border-radius:6px;background:#000}h4{font-size:14.5px;margin:14px 0 4px}figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figure.chart svg{width:100%;height:auto;background:#fff;border-radius:6px}figcaption{color:var(--muted);font-size:12.5px;margin-top:4px}
.diagram{width:100%;height:auto;background:var(--card);border-radius:8px;margin:12px 0}.diagram .node{fill:var(--bg);stroke:#999;stroke-width:1.2}
.diagram .nname{font-weight:600;font-size:13px;fill:var(--fg)}.diagram .nsub{font-size:11.5px;fill:var(--muted)}.diagram .lbl{font-weight:600;font-size:12px;fill:var(--fg)}
.inputs{border:1px solid var(--line);border-left:4px solid #8a8f98;border-radius:6px;background:var(--card);padding:6px 10px;margin:14px 0 6px;font-size:12.5px}
.inputs .ih{font-weight:700;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:2px}
.inputs table{display:table;margin:0;font-size:12.5px}.inputs th{background:none;width:150px;color:var(--muted);font-weight:600;border:0;padding:2px 8px 2px 0}
.inputs td{border:0;padding:2px 0}.ok{color:var(--ok)}.bad{color:var(--bad)}
.caveat{border:1px solid #e0a800;border-left:5px solid #e0a800;background:rgba(224,168,0,.12);border-radius:6px;padding:10px 14px;margin:12px 0}
.note{color:var(--muted);font-size:13px}.todo{color:var(--todo);font-style:italic}code{background:var(--card);padding:1px 4px;border-radius:4px}
.titleblock{display:table;width:auto;font-size:13px}.titleblock th{background:none;color:var(--muted);width:110px}
caption{caption-side:top;text-align:left;font-size:12.5px;color:var(--muted);padding:4px 0}
.summary{background:var(--card);border-left:4px solid var(--accent);padding:10px 14px;border-radius:6px}
.toc,.toc ol,.side ol{list-style:none;padding-left:0}.toc ol{padding-left:22px;font-size:14px}.toc>li{margin:6px 0;font-weight:600}
.toc ol li{font-weight:400}.toc a,.side a{color:var(--accent);text-decoration:none}.back{font-size:12.5px;text-align:right}
.back a{color:var(--muted)}details{border:1px solid var(--line);border-radius:6px;padding:6px 10px;margin:10px 0}
summary{cursor:pointer;font-weight:600;color:var(--accent)}h5{font-size:13.5px;margin:12px 0 4px}
h3{border-bottom:1px solid var(--line);padding-bottom:4px}.findings li{margin:6px 0}
.layout{max-width:1320px;margin:auto;display:block}.side{display:none}
@media (min-width:1200px){.layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:24px}
.side{display:block;position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;padding:16px 8px 16px 16px;font-size:12.5px;border-right:1px solid var(--line)}
.side ol ol{padding-left:12px}.side li{margin:3px 0}.sidehead{font-weight:700;margin-bottom:6px}main{margin:0}}
@media print{.side{display:none}details{border:0}section{break-inside:avoid-page}}"""

SITE_JS = """document.documentElement.classList.add('js');
function show(){var h=decodeURIComponent(location.hash.slice(1)),el=h&&document.getElementById(h),tabs=document.querySelectorAll('.tab');
 if(!tabs.length)return;var t=el&&el.closest('.tab')||tabs[0];
 tabs.forEach(function(x){x.classList.toggle('on',x===t)});
 document.querySelectorAll('.tabs a').forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+t.id)});
 if(el&&el!==t)el.scrollIntoView();else window.scrollTo(0,0);}
addEventListener('hashchange',show);addEventListener('DOMContentLoaded',function(){show();
 var io=new IntersectionObserver(function(es){es.forEach(function(e){e.isIntersecting?e.target.play().catch(function(){}):e.target.pause()})});
 document.querySelectorAll('video[data-auto]').forEach(function(v){io.observe(v)});});"""

SITE_CSS = """.topnav{position:sticky;top:0;z-index:9;background:var(--bg);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:2px;padding:6px 12px}
.topnav a{padding:6px 10px;border-radius:6px;text-decoration:none;color:var(--fg);font-size:14px}.topnav a.on{background:var(--accent);color:#fff}
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:2px solid var(--line);margin:16px 0}.tabs a{padding:7px 14px;text-decoration:none;
color:var(--muted);border:1px solid var(--line);border-bottom:0;border-radius:6px 6px 0 0;font-size:14px}.tabs a.on{background:var(--accent);color:#fff}
.js .tab{display:none}.js .tab.on{display:block}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin:18px 0}
.card{display:block;border:1px solid var(--line);border-radius:10px;padding:16px;background:var(--card);text-decoration:none;color:var(--fg)}
.card b{display:block;font-size:17px;color:var(--accent);margin-bottom:6px}.card span{font-size:13.5px;color:var(--muted)}
.pager{display:flex;justify-content:space-between;border-top:1px solid var(--line);margin-top:30px;padding:14px 0;font-size:14px}
.pager a{color:var(--accent);text-decoration:none}main.site{max-width:1200px;margin:auto;padding:0 16px}
.v3d-ctl{display:flex;flex-direction:column;gap:8px;font-size:13.5px;margin:10px 0}.v3d-ctl label{margin-right:12px;white-space:nowrap}
.v-parts{display:flex;flex-wrap:wrap;gap:4px 10px}.v-parts label.off{opacity:.4}.v-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px}
#v-time{flex:1;min-width:200px}.v3d-ctl button{padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}
.v3d-main{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:14px}@media (max-width:800px){.v3d-main{grid-template-columns:1fr}}
.v3d-canvas{position:relative;border:1px solid var(--line);border-radius:8px;overflow:hidden}.v3d-canvas canvas{display:block}
#v-bar{position:absolute;right:6px;top:6px;background:rgba(255,255,255,.85);border-radius:6px}
#v-probe{position:absolute;display:none;pointer-events:none;background:rgba(0,0,0,.78);color:#fff;font-size:12.5px;padding:3px 7px;border-radius:5px;z-index:2}
#v-read{font-size:12.5px}"""
VIEWER_BODY = ('<div id="v3d"><p class="note">Loading the 3D viewer…</p></div>'
               '<p class="note">Surfaces are the region boundaries of the CFD mesh, decimated to about 100–150 k vertices per model; colours are '
               'the adjacent-cell temperature. Drag to rotate, scroll to zoom, right-drag to pan. Data: scripts/export_viewer.py.</p>'
               '<script src="assets/vendor/three.min.js"></script><script src="assets/vendor/OrbitControls.js"></script>'
               '<script src="assets/viewer/manifest.js"></script><script src="assets/viewer/viewer.js"></script>')


def build_site():
    """Multi-page site in Report/Design9795_site/: the same section builders, media as files in assets/ (works offline)."""
    global ASSETS
    site = os.path.join(OUT, "Design9795_site")
    ASSETS = os.path.join(site, "assets"); os.makedirs(ASSETS, exist_ok=True)
    import shutil   # viewer code + vendored three.js r147 (last release with the non-module build, so file:// works)
    for d in ("viewer", "vendor"):
        os.makedirs(os.path.join(ASSETS, d), exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "scripts", "viewer3d.js"), os.path.join(ASSETS, "viewer", "viewer.js"))
    for f in ("three.min.js", "OrbitControls.js"):
        shutil.copyfile(os.path.join(ROOT, "scripts", "vendor_three", f), os.path.join(ASSETS, "vendor", f))
    stamp = datetime.datetime.now()
    PARTS, (v_method, v_verif, v_cmp, v_verdict) = parts()
    C = {sid: h for _, _, _, subs in PARTS for sid, _, h in subs}
    S = {pid: summ for pid, _, summ, _ in PARTS}
    num = numbers(PARTS)
    compare = (chart_transient() + event_table() + C["results-table"])
    P = [("index.html", "Overview", None, None),
         ("em.html", "Electromagnetic (FEMM)", S["em"], [("model", "Model & materials", C["em-model"]), ("losses", "Loss segregation", C["em-seg"]),
            ("fields", "Field animations", C["em-fields"]), ("why", "Why losses are high", C["em-why"])]),
         ("cfd_method.html", "CFD method", S["cfd"], [("geometry", "Geometry & mesh", C["geom"]), ("bc", "Boundary conditions & losses", C["bc"]),
            ("solver", "Solver", C["solver"]), ("verification", "Verification", C["verif"])]),
         ("results.html", "Thermal results", S["results"], [(lp, f"Duty {lp[-1]}", C[f"res-{lp}"]) for lp in ORDER]
            + [("compare", "Compare all", compare)]),
         ("viewer3d.html", "3D viewer", "Interactive 3D temperature field per load point (baseline and, where run, detailed model): "
            "parts on/off, time slider to the 180 °C cut, cut-away, explode, hover probe and per-part max/mean.", VIEWER_BODY),
         ("airflow.html", "Airflow", S["air"], [("external", "External", C["air-ext"]), ("internal", "Internal (per speed)", C["air-int"])]),
         ("detailed.html", "Detailed geometry", S["valid"], [("method", "Method & mesh", v_method), ("verification", "Verification", v_verif),
            ("compare", "Baseline vs detailed", v_cmp), ("verdict", "Verdict", v_verdict or todo("detailed runs at both points"))]),
         ("fins.html", "Fin optimisation", S["fins"], [("constraints", "Constraints", C["fins-cons"]), ("screen", "Analytical screen", C["fins-screen"]),
            ("choice", "Selected variant", C["fins-choice"]), ("cfd", "CFD result", C["fins-cfd"])]),
         ("structural.html", "Structural", None, [("status", "Status", C["struct-note"])]),
         ("conclusions.html", "Conclusions", S["concl"], [("recommendations", "Recommendations", C["levers"]),
            ("limitations", "Limitations", C["limits-list"]), ("appendix", "Appendix", C["files"])])]
    cards = "".join(f'<a class="card" href="{f}"><b>{esc(t)}</b><span>{re.sub(r"<[^>]+>", "", s_ or "") or "Placeholder: no structural analysis in this work."}</span></a>'
                    for f, t, s_, _ in P[1:])
    k = [0, 0]
    size = 0
    for i, (f, t, summ, tabs) in enumerate(P):
        nav = "".join(f'<a href="{f2}"' + (' class="on"' if f2 == f else "") + f'>{esc(t2)}</a>' for f2, t2, _, _ in P)
        if tabs is None:
            body = (f"<h1>Design9795_1 Vehicle-Duty Thermal Report</h1>{titleblock(stamp)}<h2>Results per duty point</h2>{C['results-table']}"
                    f"<h2>Key findings</h2>{C['findings']}<h2>Report pages</h2><div class=\"cards\">{cards}</div>")
        elif isinstance(tabs, str):
            body = f"<h1>{esc(t)}</h1>" + (f'<p class="summary">{summ}</p>' if summ else "") + tabs
        else:
            body = (f"<h1>{esc(t)}</h1>" + (f'<p class="summary">{summ}</p>' if summ else "")
                    + '<nav class="tabs">' + "".join(f'<a href="#{tid}">{esc(tl)}</a>' for tid, tl, _ in tabs) + "</nav>"
                    + "".join(f'<section class="tab" id="{tid}"><h2>{esc(tl)}</h2>{h}</section>' for tid, tl, h in tabs))
        body = re.sub(r"\[\[(\w+)\]\]", lambda m: f"section {num.get(ALIAS.get(m[1], m[1]), '?')}", captions(body, k))
        prev = f'<a href="{P[i-1][0]}">← {esc(P[i-1][1])}</a>' if i else "<span></span>"
        nxt = f'<a href="{P[i+1][0]}">{esc(P[i+1][1])} →</a>' if i + 1 < len(P) else "<span></span>"
        page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Design9795 {esc(t)}</title><style>{CSS}{SITE_CSS}</style><script>{SITE_JS}</script></head><body>
<nav class="topnav">{nav}</nav><main class="site">{body}<footer class="pager">{prev}{nxt}</footer></main></body></html>"""
        out = os.path.join(site, f)
        open(out, "w", encoding="utf-8").write(page)
        size += os.path.getsize(out)
    asz = sum(os.path.getsize(os.path.join(ASSETS, x)) for x in os.listdir(ASSETS))
    ASSETS = None
    print(f"wrote {site}: {len(P)} pages {size/1e6:.2f} MB + assets {asz/1e6:.2f} MB; figures {k[0]}, tables {k[1]}")


if __name__ == "__main__":
    build_site() if "--site" in sys.argv else build()
