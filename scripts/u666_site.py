"""U666 multi-page report site -> Report/U666_site/index.html (+ assets/). Local files only.

    .venv\\Scripts\\python -I scripts\\u666_site.py [--no-render]

Every page reads its inputs if they exist and prints a 'pending' note otherwise, so it can be rerun at any stage.
Single thread, BelowNormal priority (the OpenFOAM runs use all 4 cores). --no-render: skip the WSL geometry render step
(scripts/u666_report_render.sh geo, cached) and the mp4 animations (none yet: see handoff/u666_report_handoff.md).
Duty data is read straight from \\\\wsl.localhost\\Ubuntu-24.04\\home\\cfd\\cfd\\<case>\\postProcessing/<region>/<fo>/<t>/*.dat.
Case per duty: results/u666/report/sources.json {duty: "u666_duty1"} else u666_<duty>.
"""
import csv, ctypes, datetime, glob, html, json, os, re, shutil, subprocess, sys
from pathlib import Path

if sys.platform == "win32":     # CPU rule: BelowNormal
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import u666_method_report as M
import u666_figs as FG

R = M.R
RES, REP = R / "results/u666", R / "results/u666/report"
SITE = R / "Report/U666_site"
AS = SITE / "assets"
WSL = Path(r"\\wsl.localhost\Ubuntu-24.04\home\cfd\cfd")
e, inline, md = html.escape, M.inline, M.md
K = 273.15
LIM = {"winding": 155, "endw": 155, "slot": 155, "magnets": 100}


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


LP = {k: v for k, v in (J(R / "loadpoints_u666.json") or {}).items() if k.startswith("duty")}
SEC = M.parse()
DONE = {}   # page -> list of figures copied


def pend(msg):
    return f'<p class="todo">Pending: {e(msg)}</p>'


def fig(src, cap, w=None):
    src = Path(src)
    if not src.exists():
        return pend(f"figure {src.name}")
    AS.mkdir(parents=True, exist_ok=True)
    dst = AS / src.name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        shutil.copyfile(src, dst)
    return f'<figure><img loading="lazy" src="assets/{src.name}" alt="{e(cap)}"><figcaption>{inline(cap)}</figcaption></figure>'


def vid(src, cap):
    src = Path(src)
    if not src.exists():
        return pend(f"animation {src.name}")
    AS.mkdir(parents=True, exist_ok=True)
    if not (AS / src.name).exists() or (AS / src.name).stat().st_mtime < src.stat().st_mtime:
        shutil.copyfile(src, AS / src.name)
    return f'<figure><video controls loop muted preload="none" src="assets/{src.name}"></video><figcaption>{inline(cap)}</figcaption></figure>'


def tbl(head, rows):
    return ('<table><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")


def steps(*nums, title=True):
    """steps_log sections S<n> rendered (all lettered variants)."""
    out = ""
    for s in SEC:
        if int(s["id"][1:]) in nums:
            out += (f'<details open><summary>{s["id"]} {inline(s["title"])}</summary>{md(s["lines"])}</details>')
    return out or pend("steps_log section " + str(nums))


# ---------------------------------------------------------------- CSS / page frame
CSS = """:root{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--line:#e2e2e2;--card:#f6f7f9;--accent:#1f4e8c;--todo:#a15c00;--ok:#2e7d32;--bad:#c62828;--ink:#1d1d1f}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141517;--fg:#e8e8e8;--muted:#a0a4aa;--line:#2c2f33;--card:#1d1f22;--accent:#7fb0ff;--todo:#ffb74d;--ok:#81c784;--bad:#ef9a9a;--ink:#e8e8e8}}
:root[data-theme=dark]{--bg:#141517;--fg:#e8e8e8;--muted:#a0a4aa;--line:#2c2f33;--card:#1d1f22;--accent:#7fb0ff;--todo:#ffb74d;--ok:#81c784;--bad:#ef9a9a;--ink:#e8e8e8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
main{max-width:1000px;margin:auto;padding:0 16px 60px}h1{font-size:28px;margin:22px 0 6px}h2{font-size:21px;border-left:4px solid var(--accent);padding-left:10px;margin:26px 0 10px}h3{font-size:16px;margin:18px 0 6px}
.topnav{position:sticky;top:0;z-index:9;background:var(--bg);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:2px;padding:6px 12px;align-items:center}
.topnav a{padding:6px 9px;border-radius:6px;text-decoration:none;color:var(--fg);font-size:13.5px}.topnav a.on{background:var(--accent);color:#fff}.topnav button{margin-left:auto;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:4px 8px;cursor:pointer}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px;display:block;overflow-x:auto}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--card)}
figure{margin:14px 0}figure img,figure video{max-width:100%;height:auto;display:block;margin:auto;border:1px solid var(--line);border-radius:6px;background:#fff}figcaption{color:var(--muted);font-size:12.5px;margin-top:4px}
.todo{color:var(--todo);font-style:italic}.summary{background:var(--card);border-left:4px solid var(--accent);padding:10px 14px;border-radius:6px}.mut,.note{color:var(--muted);font-size:13px}
code{background:var(--card);padding:1px 4px;border-radius:4px}mark{background:rgba(224,168,0,.25);color:inherit;padding:0 3px;border-radius:3px}details{border:1px solid var(--line);border-radius:6px;padding:6px 10px;margin:10px 0}summary{cursor:pointer;font-weight:600;color:var(--accent)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin:16px 0}.card{display:block;border:1px solid var(--line);border-radius:10px;padding:12px;background:var(--card);text-decoration:none;color:var(--fg)}.card b{display:block;color:var(--accent)}.card span{font-size:13px;color:var(--muted)}
.chip{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;border:1px solid var(--line)}.chip.done{color:var(--ok)}.chip.pending{color:var(--todo)}.ok{color:var(--ok)}.bad{color:var(--bad)}
.tw{overflow-x:auto}.box{border:1px solid var(--line);border-left:4px solid #8a8f98;border-radius:6px;background:var(--card);padding:6px 12px;margin:12px 0}ul{padding-left:20px}"""
PAGES = [("index", "Overview"), ("geometry", "Geometry"), ("materials", "Materials"), ("mesh", "Mesh"), ("contacts", "Contacts & BCs"),
         ("airflow", "Airflow"), ("method", "Method & verification"), ("results", "Results"), ("calibration", "Calibration"),
         ("conclusions", "Conclusions"), ("viewer3d", "3D viewer")]
THEME = "<script>(function(){try{var t=localStorage.getItem('u666theme');if(t)document.documentElement.dataset.theme=t}catch(e){}})();function tg(){var d=document.documentElement,t=(d.dataset.theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'))=='dark'?'light':'dark';d.dataset.theme=t;try{localStorage.setItem('u666theme',t)}catch(e){}}</script>"


def page(key, title, lead, body, extra_head=""):
    nav = "".join(f'<a href="{k}.html"{" class=on" if k == key else ""}>{t}</a>' for k, t in PAGES)
    (SITE / f"{key}.html").write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>U666 {e(title)}</title>'
        f'<style>{CSS}</style>{THEME}{extra_head}</head><body><nav class="topnav">{nav}<button onclick="tg()" aria-label="theme">theme</button></nav>'
        f'<main><h1>{e(title)}</h1><p class="summary">{lead}</p>{body}<p class="mut">Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by scripts/u666_site.py from results/u666/steps_log.md and the case data.</p></main></body></html>',
        encoding="utf-8")


# ---------------------------------------------------------------- data helpers
GEO, WP = J(RES / "geo.json") or {}, (J(RES / "winding_props.json") or {}).get("rows", [{}])[0]
EB = J(RES / "s8b/eb_s8c_dt1_N3_60s.json")
HS = J(R / "mesh/u666/housing_simple.json") or {}
GEOF = REP / "geo"


def read_nc_check():
    p = R / "mesh/u666/nc_check.log"
    if not p.exists():
        return [], []
    cells, pairs = [], []
    for ln in p.read_text(errors="ignore").splitlines():
        m = re.match(r"(\w+) cells (\d+) (.*?)(?:Max skewness = ([\d.]+))?(.*)$", ln)
        if m and " cells " in ln:
            cells.append((m.group(1), int(m.group(2)), "OK" if "Mesh OK" in ln else "check", m.group(4) or "", "Failed" in ln and ln.split("***")[-1].strip() or ""))
        m = re.match(r"(\w+_to_\w+)\s+([\d.]+) mm2\s+partner\s+([\d.]+)\s+mismatch ([\d.]+) %", ln)
        if m:
            pairs.append(m.groups())
    return cells, pairs


# ---------------------------------------------------------------- duty data (read from WSL postProcessing)
def case_of(d):
    src = J(REP / "sources.json", {})
    return WSL / src.get(d, f"u666_{d}")


def duty_stats(d):
    pp = case_of(d) / "postProcessing"
    out = {}
    if not pp.exists():
        return out
    for f in pp.glob("**/*.dat"):
        m = re.match(r"(T|Tmin|Tavg|Tavgz)_(\w+)$", f.parent.parent.name)
        if not m:
            continue
        kind = {"T": "max", "Tmin": "min", "Tavg": "mean", "Tavgz": "mean"}[m.group(1)]
        rows = []
        for ln in f.read_text(errors="ignore").splitlines():
            if ln.strip() and not ln.startswith("#"):
                try:
                    rows.append([float(x) for x in ln.split()[:2]])
                except ValueError:
                    pass
        if rows:
            a = np.array(rows)
            out.setdefault(m.group(2), {}).setdefault(kind, []).append(a)
    res = {}
    for reg, dd in out.items():
        res[reg] = {}
        for kind, arrs in dd.items():
            a = np.vstack(arrs)
            a = a[np.argsort(a[:, 0], kind="stable")]
            a = a[np.r_[np.diff(a[:, 0]) > 0, True]]
            res[reg][kind] = a
    return res


def t_cross(a, lim):
    i = np.where(a[:, 1] - K >= lim)[0]
    if not len(i):
        return None
    i = i[0]
    if i == 0:
        return a[0, 0]
    t0, t1, y0, y1 = a[i - 1, 0], a[i, 0], a[i - 1, 1] - K, a[i, 1] - K
    return t0 + (lim - y0) / (y1 - y0) * (t1 - t0)


def duty_block(d):
    st = duty_stats(d)
    pk = {}
    if not st:
        return None, pk, pend(f"{d}: no postProcessing in {case_of(d)} yet (run not started or not finished)")
    PL = [("winding", "slot"), ("endw", "endw"), ("magnets", "magnets"), ("rotor", "rotor"), ("housing", "housing"), ("stator", "stator")]
    fig_, ax = plt.subplots(figsize=(9, 4.8), dpi=100)
    cols = dict(zip([p[0] for p in PL], ["#d9822b", "#a35a14", "#b5323c", "#2f9e8f", "#5b6675", "#4f7cb5"]))
    rows = []
    for lab, reg in PL:
        s = st.get(reg) or st.get(lab)
        if not s or "max" not in s:
            continue
        mx = s["max"]
        ax.plot(mx[:, 0] / 60, mx[:, 1] - K, color=cols[lab], lw=1.8, label=f"{lab} max")
        if "mean" in s:
            ax.plot(s["mean"][:, 0] / 60, s["mean"][:, 1] - K, color=cols[lab], lw=1.2, ls="--", label=f"{lab} mean")
        i = int(np.argmax(mx[:, 1]))
        lim = LIM.get(reg)
        tl = t_cross(mx, lim) if lim else None
        rows.append((lab, f"{mx[i,1]-K:.1f}", f"{mx[i,0]/60:.1f}", f"{s['mean'][-1,1]-K:.1f}" if "mean" in s else "", lim or "",
                     "" if not lim else f"{lim-(mx[i,1]-K):+.1f}", "" if not lim else ("not reached" if tl is None else f"{tl/60:.1f} min")))
        pk[lab] = dict(max=mx[i, 1] - K, t=mx[i, 0], lim=lim, tl=tl)
    ax.axhline(155, color="#c0392b", ls=":", lw=1); ax.axhline(100, color="#7d3c98", ls=":", lw=1)
    ax.set_xlabel("time [min]"); ax.set_ylabel("T [C]"); ax.grid(alpha=.3); ax.legend(ncol=3, fontsize=7)
    fig_.tight_layout(); png = REP / f"curves_{d}.png"; fig_.savefig(png); plt.close(fig_)
    body = (fig(png, f"{d}: max (solid) and mean (dashed) per region; dotted lines: 155 C winding and 100 C magnet limits.")
            + tbl(["Region", "peak max T [C]", "at [min]", "mean T at end", "limit [C]", "margin [K]", "time to limit"], rows))
    return st, pk, body


PLANES = [("axial_y0", "axial plane y = 0"), ("radial_stack", "mid-stack radial plane"), ("radial_ew_front", "front end-winding plane"),
          ("radial_ew_rear", "rear end-winding plane")]


# ---------------------------------------------------------------- pages
def p_geometry():
    vol = (EB or {}).get("volumes_cm3", {})
    hv = HS.get("vol_cm3", {})
    hsum = sum(v[0] for v in hv.values()) if hv else None
    rows = [("housing (8 solids)", "1109.8 (CAD run)", f"{hsum:.1f}" if hsum else "1048.7", "-2 % (lugs, feet, screws, blends dropped)"),
            ("outer skin area (cavities filled)", "2927 cm2", "2763 cm2", "-5.6 %; terminal box +5.9 % (fallback cap), without the box +2.5 %"),
            ("fin area", "CAD", "+1 %", "fin profile rebuilt from measured half-widths"),
            ("stator fit bore r 75.0, z -6.3..60.2", "exact", "exact", "kept"), ("bearing seats", "exact", "exact", "kept")]
    pm = [("Stator", "KE250030_1 x173 laminations", "ONE lamination face extruded z -0.35..60.2", "user decision; no 173-body fragment"),
          ("Rotor", "KE250110_1 x180", "extruded z -2.2..60.8, gap annulus r 42.6 fused", "removes overlapping facets at the OD"),
          ("Magnets", "KE250130 x54", "18 extruded columns (segment 1)", "3 axial segments merged"),
          ("Winding", "KE250510 CAD blob (747 cm3)", "slot profile extrusion + end-winding shells", "CAD blob is only representative; 4.7x too much end volume"),
          ("Wedges", "KE250530 x36", "clipped to the stack, merged with the slot opening", "rebuild; 9.5 cm3"),
          ("Liner", "KE250520 x36", "not meshed: contact layer R 1.67e-3", "0.25 mm"),
          ("Seal", "K2200050 lip seal", "plug primitive: disk r 21, z 100.5..106.5 (4.9 cm3)", "CAD seal broke the fragment; KNOB"),
          ("rpocket", "rotor pockets", "air cylinder r 42.45 over the rotor, k 0.03", "otherwise merged into inair (optimistic)"),
          ("End caps", "KE250150/370 brass + nut", "kept", ""), ("Shaft / bearings", "GE250300 / 6205, 6003", "kept (solid ring bearings)", ""),
          ("Dropped", "cables, gland, screws, circlip, sensor, encoder, terminal small parts", "-", "no thermal role or unmeshable")]
    b = f"<h2>CAD check and part map</h2>{steps(1)}"
    b += "<h2>Part map: kept, rebuilt, simplified, dropped</h2>" + tbl(["Part", "CAD", "In the model", "Why"], pm)
    b += "<h2>Simplified housing vs the CAD</h2><p>The CAD housing (28 pieces, B-spline fins, 350 blends) could not be meshed (gmsh PLC errors, OCC defeature hangs, snappy fails, see Mesh). A housing built from planes, cylinders and cones replaces it (<code>scripts/u666_housing_simple.py</code>, knob dict K).</p>"
    b += fig(GEOF / "housing_overlay.png", "CAD housing cut (red lines, from the meshing STL) over the simplified housing cells (grey): axial, radial, and a fin zoom.")
    b += tbl(["Quantity", "CAD", "Simplified", "Note"], rows)
    b += tbl(["Housing part", "volume [cm3]"], [(k, f"{v[0]:.1f}") for k, v in hv.items()]) if hv else ""
    b += "<h2>Region layout</h2>" + fig(GEOF / "radial_layout.png", "Region layout, mid-stack radial plane (z = 30 mm).") + fig(GEOF / "axial_layout.png", "Region layout, axial plane y = 0 (z horizontal).")
    b += "<h2>Lamination extrusion, wedges, seal plug, rpocket, end-winding shells</h2>"
    ew = GEO.get("ew_shells", {}).get("front", {})
    b += (f"<ul><li>Stack: z {GEO.get('stack_z')}, length {GEO.get('stack_len', 0):.2f} mm, bore r {GEO.get('r_bore')}, stator OD r {GEO.get('r_stator')}, rotor r {GEO.get('r_rotor')}, gap {GEO.get('gap_mm', 0):.2f} mm.</li>"
          f"<li>Slot area to bore {GEO.get('slot_area_to_bore_mm2', 0):.1f} mm2; meshed slot winding 101.65 mm2 (Motor-CAD 96.67 with liner); rho and k_ax scaled by 85.54/101.65.</li>"
          f"<li>End-winding shells: r_mid {ew.get('r_mid')} mm, t {ew.get('t', 0):.2f} mm, overhang {ew.get('overhang')} mm; homogenised volume {GEO.get('ew_volume_target_mm3', 0)/1000:.1f} cm3, copper {GEO.get('cu_volume_target_mm3', 0)/1000:.1f} cm3. <mark>CALIBRATION KNOB</mark></li></ul>")
    b += tbl(["Region", "volume [cm3]"], [(k, f"{v:.1f}") for k, v in vol.items()]) if vol else ""
    b += "<h2>Defeature inventory</h2>" + (f'<details><summary>results/u666/defeature_inventory.md</summary>{md((RES / "defeature_inventory.md").read_text(encoding="utf-8").splitlines())}</details>' if (RES / "defeature_inventory.md").exists() else pend("defeature inventory"))
    b += "<h2>Geometry steps (log)</h2>" + steps(4)
    b += '<h2>3D</h2><p>See the <a href="viewer3d.html">3D viewer</a> page (geometry viewer pending, see handoff).</p>'
    page("geometry", "Geometry", "CAD check, part map, and what was kept, rebuilt, simplified or dropped, with reasons.", b)


def p_materials():
    mat = [s for s in SEC if s["id"] == "S2"]
    b = steps(2)
    b += "<h2>Winding homogenisation</h2>"
    b += (f"<p>Kf = A_Cu / A_winding = 47.51 / 85.54 = {WP.get('f_copper','?')}. Transverse (Hashin-Shtrikman lower bound, matrix k_m = varnish/enamel): "
          "<code>k_T = k_m + f_c / ( 1/(k_c - k_m) + (1 - f_c)/(2 k_m) )</code>. Axial rule of mixtures: <code>k_ax = f_c k_c + (1 - f_c) k_m</code>. "
          "rho, cp mass-weighted.</p>")
    b += tbl(["Quantity", "Value", "Note"],
             [("k_T, HS lower bound", f"{WP.get('k_transverse_HS_lower', 0):.3f} W/mK", "used"),
              ("k_T, layered (Wiener series)", f"{WP.get('k_transverse_layered_check', 0):.3f}", "series bound, too pessimistic (judged)"),
              ("k of the strand bundle (HS)", f"{WP.get('k_strand_bundle_HS', 0):.2f}", "conductor + enamel"),
              ("k_ax rule of mixtures", f"{WP.get('k_axial_ROM', 0):.1f}", "scaled by 85.54/101.65 in the meshed slot"),
              ("rho / cp", f"{WP.get('rho_homog', 0):.0f} / {WP.get('cp_homog', 0):.0f}", ""),
              ("liner R", f"{WP.get('R_liner_m2K_per_W', 0):.3g} m2K/W", "0.25 mm / 0.15 -> h about 600")])
    b += "<h2>End winding</h2><p>Fill 0.528, shell homogenised with wire in the (theta, z) sheet: k (r, theta, z) = (1.05, 205, 205) W/mK, rho 5510, cp 473. The shell geometry is a <mark>CALIBRATION KNOB</mark>. No potting (user): the end winding is in air, so the radial k is that of the varnished bundle.</p>"
    b += "<h2>Anisotropy</h2><p>Laminations: 28/28/1.5 W/mK (in-plane/axial), cartesian frame. Winding: cylindrical frame (slot wire along z, end winding along theta). The anisotropic solid on the non-conformal mesh needed the explicit-split fix (S8c).</p>"
    page("materials", "Materials", "Per-region properties, anisotropy, and the winding homogenisation with the bounds considered.", b)


def p_mesh():
    cells, pairs = read_nc_check()
    gc = J(GEOF / "geo_cells.json") or {}
    b = "<h2>Routes tried</h2>" + tbl(["Route", "Outcome", "Why it failed"], [
        ("gmsh conformal tet, CAD housing (Delaunay / HXT)", "failed", "PLC segment-facet intersection on the dirty CAD (tori under 0.05 mm2, fin B-splines, 0.07 mm circle offsets); the 3D result of per-region diagnostics was void (0 tets)"),
        ("fuse regions / fallback cap and gasket prisms", "failed", "housing fuse fails in OCC or loses 370 cm3; 2D fails on inverted cones"),
        ("per-part CAD defeature (OCC)", "impractical", "calls hang (>20 min per 15 faces) or delete the solid; shaft 51/53 only"),
        ("snappyHexMesh from per-region STLs", "dropped", "closed per-region STLs overlap on shared faces; 762 k free-standing zone faces; 8 M cells at levels 3"),
        ("gmsh conformal with SIMPLIFIED housing", "still PLC", "source unknown at that time"),
        ("FINAL: non-conformal per-region mesh + prism extrusion", "works", "each region meshed alone; stator, rotor, winding, wedge, magnets as z-prisms from one 2D mesh; non-conformal coupling")])
    b += "<h2>Final route</h2>" + steps(7, 8)
    b += "<h2>Per-region cells and quality (checkMesh)</h2>" + (tbl(["Region", "cells", "result", "max skewness", "note"], cells) + '<p class="mut">rotor and wedge: skewness above the 4 limit on a few faces; accepted, energy gate met.</p>' if cells else pend("mesh/u666/nc_check.log"))
    b += "<h2>Interface pair areas</h2>" + (tbl(["Pair", "area A [mm2]", "partner [mm2]", "mismatch [%]"], pairs) if pairs else pend("interface areas"))
    b += "<h2>Mesh cross-sections</h2>"
    for k, t in (("radial_mesh", "Mid-stack radial plane"), ("radial_zoom", "One tooth/slot sector"), ("axial_mesh", "Axial plane y = 0"), ("axial_zoom", "Front end winding and end space")):
        b += fig(GEOF / f"{k}.png", t + " (prism regions and tet regions, region colours).")
    if gc:
        regs = sorted({r for d in gc.values() for r in d})
        b += tbl(["Region", "cut triangles, radial", "cut triangles, axial"], [(r, gc["radial"].get(r, ""), gc["axial"].get(r, "")) for r in regs])
    b += "<h2>One picture per region</h2>" + fig(GEOF / "regions_radial.png", "Every region on the mid-stack radial plane z = 30 mm, cut cells with edges (title: cells in the region, cells cut by the plane).") + fig(GEOF / "regions_axial.png", "Every region on the axial plane y = 0.")
    page("mesh", "Mesh", "Every meshing route tried and why it failed, and the final non-conformal per-region mesh with quality and interface tables.", b)


def p_contacts():
    q = [(d, v.get("rpm"), v.get("torque_Nm"), v.get("Q_cu_dc_W"), v.get("Q_cu_ac_W"), v.get("Q_iron_W"), v.get("Q_magnet_W"), v.get("Q_windage_W"), v.get("Q_friction_W"), v.get("Q_total_W")) for d, v in LP.items()]
    b = "<h2>Contact resistances</h2>" + tbl(["Interface", "layer", "R-equivalent", "source"], [
        ("winding / stator (liner)", "0.25 mm, k 0.15", "1.67e-3 m2K/W (h about 600)", "Motor-CAD"),
        ("stator / housing (shrink fit)", "2e-5 m, k 0.026", "7.7e-4 (about 1300 W/m2K)", "old baseline, to re-check"),
        ("magnet / rotor (glue)", "1e-4 m, k 0.2", "5e-4", "old baseline"),
        ("rotor / stator (air gap)", "0.65 mm, k_gap per duty", "Taylor-Couette", "per-duty k_gap"),
        ("endcaps / stator, rotor / wedge", "air gap k", "as gap", ""), ("glue / bearings", "solid ring k 15", "reduced k for ball contacts", "kept"),
        ("inair", "k_inair = h_endspace x 10 mm, windage heat in", "CALIBRATION KNOB", "old method")])
    b += "<h2>Losses per duty and mapping</h2>" + tbl(["duty", "rpm", "Nm", "DC Cu", "AC Cu", "iron", "magnet", "windage", "friction", "total W"], q)
    b += "<ul><li>DC Cu to winding, q = q_ref (1 + 0.00393 (T - T_ref)), T_ref 100 C <mark>PENDING</mark>; AC Cu constant in the slot.</li><li>Iron: stator 0.8 / rotor 0.2 <mark>PLACEHOLDER</mark>. Magnet loss to magnets. Windage to inair. Friction 50/50 front/rear bearing <mark>PLACEHOLDER</mark>.</li></ul>"
    b += "<h2>External h and radiation</h2><p>Per-face h from the external air CFD (see Airflow) plus radiation with eps 0.1 (bare machined Al), ambient 40 C, implemented as a mixed BC with f = (h + h_rad)/(h + h_rad + k/delta). Fallback: uniform 5 W/m2K.</p>"
    b += "<h2>Initial conditions</h2><p>Uniform 40 C (313.15 K) in every region, cold start at ambient.</p>" + steps(5, 6)
    page("contacts", "Contacts & boundaries", "Contact resistances, losses and their mapping, external heat transfer and initial conditions.", b)


def air_block():
    sm = J(WSL / "u666_air_h_summary.json") or {}
    A = REP / "air"
    out = "<h2>Air CFD result</h2>" + fig(A / "air_U.png", "Velocity magnitude on the vertical axial plane x = 0 (left) and the cross-section z = 30 mm (right); motor skin 70 C, ambient 40 C, closed box.")
    out += fig(A / "air_T.png", "Air temperature on the same two planes.")
    if sm:
        cl, c = sm["classes"], sm["corr"]
        out += "<h2>h classes vs correlations</h2>" + tbl(["Class", "area [cm2]", "mean h [W/m2K]", "max h"], [(k, f"{v['area_cm2']:.0f}", f"{v['h_mean']:.2f}", f"{v['h_max']:.1f}") for k, v in cl.items()])
        out += tbl(["Reference", "h [W/m2K]", "comment"], [
            ("CFD skin mean", f"{sm['h_air_skin_mean']:.2f}", "area-weighted over the mapped faces, skin 70 C"),
            ("Churchill-Chu, D 159 / 185 mm cylinder", f"{c['cc_D159']:.1f} / {c['cc_D185']:.1f}", "smooth horizontal cylinder"),
            ("Elenbaas, fin tip / root", f"{c['elenbaas_tip']:.1f} / {c['elenbaas_root']:.2f}", "parallel plates; the root is choked"),
            ("fins in the CFD", f"{cl['fins']['h_mean']:.2f}", "40 % under the correlation: fin gap only 1.5-5 cells wide (inside the 50 % gate; knob)")])
    else:
        out += pend("u666_air_h_summary.json")
    hs = J(A / "hmap_stats.json") or {}
    out += "<h2>h map on the housing</h2>" + fig(A / "h_3d.png", "h on the housing and shaft faces, two 3D views (colour clipped at 8 W/m2K).") + fig(A / "h_unwrapped.png", "Top: h unwrapped around the axis. Bottom: faces that had h = 0 in the CFD map (red).")
    if hs:
        out += ("<h2>Decision: unmapped faces 0 to 2.5 W/m2K</h2><p>Housing and shaft faces more than 3 mm from the air skin (fin-root fill, terminal-box interior, front shaft bore) have no air neighbour in the CFD, so the map gave h = 0 (adiabatic). "
                f"There are {hs['zero_faces']} such faces, {hs['zero_area_cm2']:.0f} cm2 of {hs['total_area_cm2']:.0f} cm2 ({hs['zero_area_cm2']/hs['total_area_cm2']*100:.0f} %). "
                "They are now set to 2.5 W/m2K (enclosed-cavity natural convection; radiation eps 0.1 unchanged); the original map is kept as <code>u666_air_h.json.h0bak</code>. "
                "Applies from duty2; duty1 (5 min) used 0, negligible on a 5 min transient. <mark>CALIBRATION KNOB</mark> (S9 MAIN decision below).</p>")
    else:
        out += pend("h map statistics")
    return out


def p_airflow():
    hs = sorted(glob.glob(str(RES / "h_*.json")) + glob.glob(str(R / "mesh/u666/h_*.json")))
    b = steps(9)
    b += "<h2>Mesh and boundary conditions</h2>" + tbl(["Item", "Value"], [("domain", "x +-330, y -330..520, z -330..420 mm (y up), closed box"), ("mesh", "1.229 M tets (HXT), S_FIN 1.8 / S_SKIN 5 / S_FAR 60 mm; min SICN 0.139; non-orth max 79 deg"),
        ("motor skin", "0.2913 m2, T fixed 343.15 K (assumed 70 C)"), ("box walls", "313.15 K, noSlip"), ("solver", "localEuler pseudo-transient, maxCo 3, upwind, GAMG/GaussSeidel; maxDeltaT must be <= 0.1 (5 gives non-physical 10 m/s)")])
    b += "<h2>h map and correlation check</h2>"
    for h in hs:
        b += f"<p>{Path(h).name}</p>"
    b += ""
    b += air_block()
    b += "<h2>Internal air</h2><p>The internal end spaces are not resolved: a lumped <code>inair</code> region (rho 10, cp 718, k_inair = (15 + 6.75 (omega r)^0.65) x 0.01 m) takes the windage heat and conducts to winding ends, housing, rotor and endcaps. <mark>CALIBRATION KNOB</mark></p>"
    page("airflow", "Airflow", "External natural-convection air CFD for the h map, and the lumped treatment of the internal air.", b)


def p_method():
    b = "<h2>Solver</h2>" + tbl(["Item", "Value"], [("solver", "OpenFOAM 12 foamMultiRun, 10 solid regions, ddt Euler"), ("coupling", "custom coupledTemperatureNC (non-conformal, contact layers, explicit split for anisotropic k)"), ("dt / outers", "dt 1 s, nOuterCorrectors 3 (energy test)"), ("laplacian", "limited corrected 0.33; uncorrected for anisotropic regions"), ("linear", "GAMG DICGaussSeidel, relTol 0.1/0"), ("timing", "4.5 s wall per s simulated (5.9 incl. setup), 1.446 M cells, 4 procs")])
    b += "<h2>Energy test (adiabatic duty1, 1201 W)</h2>" + steps(8)
    b += fig(RES / "s8b/balance_s8c_dt1_N3.png", "Stored minus injected energy, dt 1 s, 3 outers; gate +-1.5 %, result -1.14 % at 60 s.") + fig(RES / "s8b/balance_s8b_dt1_N3.png", "Earlier iteration (S8b) for comparison.")
    if EB:
        rows = [(k, f"{v.get(next(x for x in v if x!='sum')):.2f}", f"{v['sum']:+.3f}") for k, v in EB["iface_W"].items()]
        b += f"<p>Generation {EB['generation_kJ']:.2f} kJ, storage {EB['storage_kJ']:.2f} kJ, error {EB['error_pct']:.2f} %.</p>" + tbl(["Interface pair", "flow one way [W]", "pair sum [W]"], rows)
    page("method", "Method & verification", "Solver settings, the coupled-temperature BC, the energy test and its interface table.", b)


def duty_visuals(d, v, st, pk):
    """contours, animations, observations for one duty (cached by data time inside u666_figs)."""
    case = case_of(d)
    props = J(case / "case_props.json")
    out = ""
    try:
        png = REP / f"contour_{d}.png"
        tf = FG.contour_fig(case, d, None, png)
        out += (fig(png, f"{d}: temperature at t = {tf:.0f} s on the four cut planes, one colour scale; hatched = above the region limit.") if tf is not None else pend(f"{d} contours: no plane output"))
    except Exception as ex:
        out += pend(f"{d} contours failed: {ex}")
    FG.ANIM.mkdir(parents=True, exist_ok=True)
    resid = None
    for kind, fn in (("temp", lambda o: FG.anim_temp(case, d, o, f"{d}: {v.get('rpm')} rpm, {v.get('torque_Nm')} Nm")),
                     ("budget", lambda o: FG.anim_budget(case, d, o, f"{d}: energy stored per region vs injected", props))):
        o = FG.ANIM / f"results_anim_{d}_{kind}.mp4"
        try:
            r = fn(o)
            ok = r[0] if isinstance(r, tuple) else r
            if isinstance(r, tuple):
                resid = r[1]
        except Exception as ex:
            ok = False
            out += pend(f"{d} {kind} animation failed: {ex}")
        cap = {"temp": "Temperature on the axial and mid-stack radial planes from the 40 C start, fixed colour scale, with the winding and magnet traces.",
               "budget": "Energy stored in each region (left), and injected vs stored + ambient outflow (right); storing rate in W per region."}[kind]
        out += vid(o, f"{d}: {cap}") if ok else pend(f"{d} {kind} animation (needs data)")
    out += pend("3D animation skipped: it needs every saved full field reconstructed (1.4 M cells x 10 regions) and a 3D renderer, too heavy while OpenFOAM uses all cores.")
    obs = FG.observations(case, d, props, pk, resid)
    ov = REP / f"observations_{d}.md"
    if ov.exists():
        obs += [ln.lstrip("-* ").strip() for ln in ov.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if obs:
        out += "<h3>Observations</h3><ul>" + "".join(f"<li>{inline(x)}</li>" for x in obs) + "</ul>"
    return out


def compare_fig(allst):
    fig_, axs = plt.subplots(1, 2, figsize=(12, 4.6), dpi=100)
    cols = ["#1f4e8c", "#d9822b", "#2e7d32", "#b5323c", "#7d3c98"]
    for (d, st), c in zip(allst.items(), cols):
        for ax, reg in ((axs[0], "slot"), (axs[1], "magnets")):
            a = (st.get(reg) or {}).get("max")
            if a is not None:
                ax.plot(a[:, 0] / 60, a[:, 1] - K, color=c, lw=1.6, label=d)
    for ax, lim, t in ((axs[0], 155, "winding hot spot [C]"), (axs[1], 100, "magnet max [C]")):
        ax.axhline(lim, color="#c62828", ls="--", lw=1)
        ax.set_title(t); ax.set_xlabel("time [min]"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig_.tight_layout()
    png = REP / "compare_all.png"
    fig_.savefig(png); plt.close(fig_)
    return png


def p_results():
    b = (f'<p class="note">Limits: winding 155 C, magnets 100 C. Cases are read from {e(str(WSL))}. The radial planes of duty1-3 were empty in the run '
         '(plane point given in mm on a metre mesh); they are re-cut from the saved T fields (every 30 s) by scripts/u666_slicefix.sh. Duty4/5 write them every 10 s.</p>')
    allpk, allst, nav = {}, {}, ""
    for d, v in LP.items():
        st, pk, body = duty_block(d)
        allpk[d] = pk
        if st:
            allst[d] = st
        nav += f'<a href="#{d}">{d}</a> '
        b += f'<h2 id="{d}">{d}: {v.get("rpm")} rpm, {v.get("torque_Nm")} Nm, {v.get("Q_total_W")} W, target {v.get("target_min")} min</h2>' + body
        if st:
            b += duty_visuals(d, v, st, pk)
    b += "<h2>Compare all</h2>"
    if any(allpk.values()):
        b += tbl(["duty", "winding peak", "endw peak", "magnets peak", "rotor", "housing", "first limit"],
                 [(d, *[f"{p[r]['max']:.1f}" if r in p else "-" for r in ("winding", "endw", "magnets", "rotor", "housing")],
                   "; ".join(f"{r} {p[r]['tl']/60:.1f} min" for r in p if p[r].get("tl")) or "none") for d, p in allpk.items() if p])
        b += fig(compare_fig(allst), "Winding hot spot and magnet maximum for every duty that has data; dashed: limits. Durations differ per duty (5/15/30/45/45 min).")
    else:
        b += pend("no duty has data yet")
    page("results", "Results", "Per-duty temperature histories, contours, animations and peak tables; filled as the runs finish.", nav + b)
    return allpk


def p_calibration():
    b = pend("test data: T(t) per sensor, sensor locations, ambient, mounting, airflow (not delivered yet). The comparison table and plots fill from results/u666/test/*.csv once present.")
    b += "<h2>Calibration knobs</h2>" + tbl(["Knob", "Now", "Acts on", "Direction"], [
        ("end-winding shell t / overhang / r", "5.17 mm / 30 mm / 55.5", "end-winding temperature", "thicker: cooler"),
        ("liner R", "1.67e-3 m2K/W", "winding to stator", "higher: winding hotter"), ("shrink fit k/t", "0.026 / 2e-5", "stator to housing", ""),
        ("magnet glue", "k 0.2 / 1e-4", "magnet temperature", ""), ("k_inair, windage", "h_endspace x 10 mm", "end-space exchange", ""),
        ("iron split", "0.8/0.2", "rotor/magnet heating", "more rotor: hotter magnets"), ("T_ref copper", "100 C", "winding heat (0.4 %/K)", ""),
        ("friction split", "50/50", "bearings", ""), ("emissivity", "0.1", "skin radiation", ""), ("h map skin dT", "30 K", "skin h", ""),
        ("seal plug", "4.9 cm3", "front shaft path", ""), ("mounting", "suspended", "conduction + convection", "")])
    page("calibration", "Calibration", "Placeholder for the test comparison and the knobs that will be tuned against it.", b)


def p_conclusions():
    b = "<h2>Limitations</h2><ul><li>Simplified housing (-2 % volume), real CAD unmeshable.</li><li>End-winding geometry is a shell, not the CAD.</li><li>Energy gate -1.14 %: winding-side interface losses ~14 W of 1201 W unexplained.</li><li>Internal air lumped; external h at one assumed skin dT, suspended mounting.</li><li>Rotor / wedge skewness above 4 on a few faces.</li></ul>"
    b += "<h2>Feedback needed from the user</h2>" + tbl(["Item", "Used now", "Why it matters"], [
        ("iron loss split", "0.8/0.2 placeholder", "rotor iron heat goes through the magnets"), ("copper T_ref", "100 C pending", "0.4 % per K on winding heat"),
        ("duty4 friction 251 W", "50/50 to bearings", "more than iron and 2x windage: measured or seal/gearbox?"), ("test data", "none", "needed for calibration"),
        ("mounting", "suspended, no feet", "adds conduction path"), ("skin temperature for h", "70 C", "h depends on dT"), ("end-winding geometry", "5 mm shell", "knob"), ("contact values", "old baseline", "re-check against test")])
    b += "<h2>Full step log (traceability)</h2>" + steps(*sorted({int(s["id"][1:]) for s in SEC}))
    page("conclusions", "Conclusions & open questions", "Limitations, assumptions, the questions for the user, and the complete step log.", b)


def p_viewer():
    page("viewer3d", "3D viewer", "Interactive geometry/temperature viewer.", pend("U666 viewer data (scripts/u666_export_viewer.py not written yet; export_viewer.py + viewer3d.js are the template)"))


def p_index(allpk):
    rows = []
    for s in SEC:
        rows.append((s["id"], inline(s["title"]), f'<span class="chip {M.status(s).replace(" ", "")}">{M.status(s)}</span>'))
    cards = "".join(f'<a class="card" href="{k}.html"><b>{t}</b><span>{d}</span></a>' for (k, t), d in zip(PAGES[1:], [
        "CAD check, part map, simplifications", "properties, winding homogenisation", "routes tried, final mesh, quality", "contact R, losses, h, IC", "external air CFD, internal air",
        "solver, energy test", "per-duty T(t), peaks, compare", "test vs CFD, knobs", "limitations, questions, full log", "interactive 3D"]))
    pk = [(d, *[f"{p[r]['max']:.1f}" if r in p else "pending" for r in ("winding", "endw", "magnets", "rotor", "housing")]) for d, p in allpk.items()]
    b = ("<h2>Key findings so far</h2><ul><li>Energy gate met on the non-conformal prism mesh: -1.14 % at 60 s (1.446 M cells).</li>"
         "<li>The CAD housing could not be meshed; a simplified housing (-2 % volume, +1 % fin area) is used.</li><li>DC copper dominates the losses at duty1-3 (1133 / 548 / 324 W).</li>"
         "<li>Duty1/2 done: winding limit 155 C reached at 4.1 / 13.2 min, magnets 100 C at 14.4 min in duty2 (see Results); the external-air h map is done (mean 3.95 W/m2K); duty3-5 and the test calibration are pending.</li></ul>")
    b += "<h2>Pages</h2>" + f'<div class="cards">{cards}</div>' + "<h2>Peak temperatures per duty [C]</h2>" + tbl(["duty", "winding", "end winding", "magnets", "rotor", "housing"], pk)
    b += "<h2>Status of every step</h2>" + tbl(["Step", "Title", "Status"], rows)
    page("index", "U666 benchmark motor: thermal CFD", "OpenFOAM 12 conjugate heat transfer of the U666 benchmark motor, five duty points, to be tuned against the test data.", b)


def render_geo():
    sh = "/mnt/c/" + str(R).replace("\\", "/")[3:] + "/scripts/u666_report_render.sh"
    try:
        for step in ("geo", "extra"):
            subprocess.run(["wsl", "-d", "Ubuntu-24.04", "-u", "cfd", "bash", sh, step], env={**os.environ, "MSYS_NO_PATHCONV": "1"},
                           creationflags=0x4000 if sys.platform == "win32" else 0, timeout=3600)
    except Exception as ex:
        print("render skipped:", ex)


def main():
    if "--no-render" not in sys.argv:
        render_geo()
    SITE.mkdir(parents=True, exist_ok=True); AS.mkdir(exist_ok=True)
    p_geometry(); p_materials(); p_mesh(); p_contacts(); p_airflow(); p_method(); allpk = p_results(); p_calibration(); p_conclusions(); p_viewer(); p_index(allpk)
    print("wrote", SITE / "index.html")


if __name__ == "__main__":
    main()
