"""U666 CFD report: ONE command regenerates Report/U666_report.html from whatever data exists.

    python scripts/u666_report.py            # low-priority WSL render (geo cached, duties if their case exists) + build
    python scripts/u666_report.py --no-render  # build only from results/u666/report/*

Sources: results/u666/steps_log.md (method), results/u666/report/geo/*.png (render step 'geo'),
results/u666/report/<duty>/ (render step 'duty': curves.png, contours.png, anim_*.gif, peaks.json, stats.json),
results/u666/report/sources.json {duty: "/home/cfd/cfd/<case>"} (default ~/cfd/u666_<duty>),
results/u666/report/observations_<duty>.md (optional hand notes, bullets).
"""
import base64, html, io, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import u666_method_report as M  # reuse markdown/section helpers, CSS and schematic
from PIL import Image

R = M.R
REP = R / "results/u666/report"
OUT = R / "Report/U666_report.html"
e, inline, md = html.escape, M.inline, M.md
DUTIES = [("duty1", "5 min", "10:45"), ("duty2", "15 min", "12:15"), ("duty3", "30 min", "15:15"),
          ("duty4", "45 min", "19:45"), ("duty5", "45 min", "00:15")]
BUDGET = 13.5e6
_size = [0]


def b64(path, maxw=1100):
    p = Path(path)
    if p.suffix == ".gif":
        d = p.read_bytes(); mime = "image/gif"
    else:
        im = Image.open(p)
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        b = io.BytesIO(); im.convert("RGB").quantize(160, method=Image.Quantize.MEDIANCUT).save(b, "PNG", optimize=True)
        d = b.getvalue(); mime = "image/png"
    _size[0] += len(d)
    return f"data:{mime};base64,{base64.b64encode(d).decode()}"


def fig(path, cap, maxw=1100):
    p = Path(path)
    if not p.exists():
        return f'<p class="ph">[figure pending: {e(p.name)}]</p>'
    return f'<figure><img src="{b64(p, maxw)}" alt="{e(cap)}" loading="lazy"><figcaption>{inline(cap)}</figcaption></figure>'


def sec_key(s):
    m = re.match(r"S(\d+)([a-z]?)", s["id"])
    return int(m.group(1)), m.group(2)


def sections():
    secs = M.parse()
    for s in secs:
        t = s["title"].lower()
        s["st"] = "pending" if t.rstrip().endswith("pending") or "— pending" in t else \
            "in progress" if re.search(r"not yet|in progress", t) or M.status(s) == "in progress" else "done"
    ids = {}
    for s in secs:
        ids.setdefault(s["id"], []).append(s)
    keep = [s for s in secs if not (s["st"] == "pending" and len(ids[s["id"]]) > 1)]
    return sorted(keep, key=sec_key)


EXTRA = {  # figures inserted after a method section
    "S4": lambda: fig(REP / "geo/radial_layout.png", "Region layout, mid-stack radial plane (z = 30 mm). Housing grey, stator blue, winding orange, wedge yellow, rotor green, magnets red, shaft dark, internal air pale.", 800)
    + fig(REP / "geo/axial_layout.png", "Region layout, axial plane y = 0 (z horizontal, x vertical).", 1100),
    "S7c": lambda: fig(REP / "geo/radial_mesh.png", "Mesh, mid-stack radial plane: z-prism (extruded) regions for stator, rotor, winding, wedge, magnets; tet for the rest.", 900)
    + fig(REP / "geo/radial_zoom.png", "Zoom, one tooth/slot sector.", 800)
    + fig(REP / "geo/axial_mesh.png", "Mesh, axial plane y = 0 (non-conformal regions meet at the interfaces).", 1100)
    + fig(REP / "geo/axial_zoom.png", "Zoom, front end winding and end space (prism stack on the left, tet end space on the right).", 800),
    "S8c": lambda: fig(R / "results/u666/s8b/balance_s8c_dt1_N3.png", "Adiabatic energy test, duty1 losses (1201 W): stored minus injected energy, dt 1 s, 3 outer iterations. Gate +-1.5 %, result -1.14 % at 60 s.", 900),
}


def cells_table():
    try:
        c = json.loads((REP / "geo/geo_cells.json").read_text())
    except Exception:
        return ""
    regs = sorted({r for d in c.values() for r in d})
    rows = "".join(f"<tr><td>{r}</td><td>{c['radial'].get(r, '')}</td><td>{c['axial'].get(r, '')}</td></tr>" for r in regs)
    return f'<div class="tw"><table><tr><th>Region</th><th>cut triangles, radial plane</th><th>cut triangles, axial plane</th></tr>{rows}</table></div><p class="mut">Cut-triangle counts are a mesh-density indicator on the two figure planes (total 1.446 M cells, see S8c).</p>'


def fmt_t(t):
    return "not reached" if t is None else f"{t/60:.1f} min"


def duty_block(d, tgt, eta):
    D = REP / d
    info = json.loads((D / "info.json").read_text()) if (D / "info.json").exists() else None
    h = f'<section id="{d}"><h2>{d} <span class="mut">target {tgt}</span> '
    if not info or not info["have"]:
        return h + f'<span class="chip pending">pending</span></h2><p>Expected at about {eta} local. This section fills in automatically when the run writes data (re-run <code>python scripts/u666_report.py</code>).</p></section>'
    h += '<span class="chip inprogress">data</span></h2>'
    pk = json.loads((D / "peaks.json").read_text()) if (D / "peaks.json").exists() else {}
    h += fig(D / "curves.png", f"{d}: max (solid) and mean (dashed) temperature per region, with the 155 C winding and 100 C magnet limits.", 1000)
    if pk:
        def row(r, v):
            L = v["limit"]
            c = ["" if L is None else L, "" if L is None else "%+.1f" % (L - v["max"]), "" if L is None else fmt_t(v["t_limit"])]
            return "<tr><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td>%.1f</td>%s</tr>" % (
                r, v["max"], v["t_max"] / 60, v["max_end"], v["mean_end"], "".join("<td>%s</td>" % x for x in c))
        rows = "".join(row(r, v) for r, v in pk.items())
        h += f'<div class="tw"><table><tr><th>Region</th><th>peak max T [C]</th><th>at [min]</th><th>max T at end</th><th>mean T at end</th><th>limit [C]</th><th>margin [K]</th><th>time to limit</th></tr>{rows}</table></div>'
        obs = []
        for r, v in pk.items():
            if v["limit"]:
                obs.append(f"{r}: peak {v['max']:.1f} C, " + (f"limit {v['limit']} C crossed at {fmt_t(v['t_limit'])}." if v["t_limit"] is not None else f"stays {v['limit'] - v['max']:.1f} K below the {v['limit']} C limit."))
        h += "<div class='box a'><h4>Observations</h4><ul>" + "".join(f"<li>{e(o)}</li>" for o in obs) + "</ul>"
        f = REP / f"observations_{d}.md"
        if f.exists():
            h += md(f.read_text(encoding="utf-8").splitlines())
        h += "</div>"
    h += fig(D / "contours.png", f"{d}: temperature on the monitored planes at the last available time (common colour scale).", 1100)
    for k, n in (("axial", "axial plane y = 0"), ("mid", "mid-stack radial plane")):
        g = D / f"anim_{k}.gif"
        if g.exists():
            h += f'<figure><img src="{b64(g)}" alt="animation {n}" loading="lazy"><figcaption>{d}: animation of the {n} ({info["have"].get("gif_" + k, "?")} saved times).</figcaption></figure>'
    return h + "</section>"


FEEDBACK = """<section id="feedback"><h2>Feedback / open questions</h2>
<p>Each item below is a placeholder that moves the result. Please confirm or give the real value.</p>
<div class="tw"><table><tr><th>Item</th><th>Used now</th><th>Why it matters / what we need</th></tr>
<tr><td>Iron loss split stator / rotor</td><td>0.8 / 0.2 (<mark>PLACEHOLDER</mark>)</td><td>Rotor iron heat goes through the magnets, so a larger rotor share raises magnet temperature directly. Need the Motor-CAD split.</td></tr>
<tr><td>Copper reference temperature for DC loss</td><td>100 C (<mark>PENDING</mark>)</td><td>q = q_ref (1 + 0.00393 (T - T_ref)). If Motor-CAD used a different T_ref the winding heat is biased by about 0.4 % per K.</td></tr>
<tr><td>duty4 friction loss</td><td>251 W</td><td>More than iron (193 W) and more than twice windage (108 W). Is it measured, or does it include a seal or gearbox? It goes 50/50 into the two bearings.</td></tr>
<tr><td>Test data</td><td>none yet</td><td>Need T(t) per sensor, the sensor locations, ambient, mounting and airflow, to calibrate the knobs below.</td></tr>
<tr><td>Mounting</td><td>suspended, no feet or plate</td><td>Real mounting adds a conduction path and changes the natural-convection flow.</td></tr>
<tr><td>Skin temperature for the h map</td><td>70 C (dT 30 K over 40 C ambient)</td><td>h depends on dT. If the real skin is much colder or hotter the h map should be redone at that dT.</td></tr>
<tr><td>End-winding geometry</td><td>5 mm shell, 30 mm overhang, r 55.5</td><td>CALIBRATION KNOB. The CAD blob is only representative.</td></tr>
<tr><td>Simplified housing</td><td>-2 % volume, +1 % fin area</td><td>Lugs, feet, screws omitted; terminal box +5.9 % skin area. Real CAD could not be meshed.</td></tr>
<tr><td>Internal air (inair), windage heat</td><td>lumped k_inair, windage into inair</td><td>CALIBRATION KNOB for the end-space convection.</td></tr>
<tr><td>Contact resistances</td><td>liner 1.67e-3, shrink fit 2e-5 m / 0.026, glue 1e-4 / 0.2</td><td>Carried over from the old baseline, to be re-checked against the test.</td></tr>
</table></div></section>"""


def render():
    sh = "/mnt/c/" + str(R).replace("\\", "/")[3:] + "/scripts/u666_report_render.sh"
    wsl = ["wsl", "-d", "Ubuntu-24.04", "-u", "cfd"]
    env = {"MSYS_NO_PATHCONV": "1"}
    import os
    env = {**os.environ, **env}
    low = 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS
    kw = dict(env=env, creationflags=low if sys.platform == "win32" else 0)
    subprocess.run(wsl + ["bash", sh, "geo"], **kw)
    try:
        src = json.loads((REP / "sources.json").read_text())
    except Exception:
        src = {}
    for d, _, _ in DUTIES:
        case = src.get(d, f"/home/cfd/cfd/u666_{d}")
        ok = subprocess.run(wsl + ["test", "-d", case + "/postProcessing"], **kw).returncode == 0
        if ok:
            subprocess.run(wsl + ["bash", sh, "duty", case, "/mnt/c/" + str(REP / d).replace("\\", "/")[3:]], **kw)


def main():
    if "--no-render" not in sys.argv:
        try:
            render()
        except Exception as ex:
            print("render skipped:", ex)
    secs = sections()
    byid = {s["id"]: s for s in secs}
    for s in secs:
        s["cls"] = s["st"].replace(" ", "")
    knobs, qs = [], []
    for s in secs:
        for ln in s["lines"]:
            if ln.startswith("|") and not re.search(r"placeholder|pending", ln, re.I):
                continue
            t = re.sub(r"^\s*- ", "", ln).strip()
            if re.search(r"calibration knob|placeholder|pending|to be re-checked", ln, re.I):
                knobs.append((s["id"], t))
    chips = "".join(f'<a class="chip {s["cls"]}" href="#{s["id"]}">{s["id"]}<small>{s["st"]}</small></a>' for s in secs)
    chips += "".join(f'<a class="chip {"done" if (REP / d / "info.json").exists() else "pending"}" href="#{d}">{d}<small>{eta}</small></a>' for d, _, eta in DUTIES)
    body = ""
    for s in secs:
        a = M.pick(s["lines"], "assumption")
        p = M.pick(s["lines"], r"problem|attempt|open question")
        used = set(map(id, a)) | set(map(id, p))
        rest = [l for l in s["lines"] if id(l) not in used]
        body += f'<section id="{s["id"]}"><h2>{s["id"]} {inline(s["title"])} <span class="chip {s["cls"]}">{s["st"]}</span></h2>{md(rest)}'
        if a:
            body += f'<div class="box a"><h4>Assumptions</h4>{md(a)}</div>'
        if p:
            body += f'<div class="box"><h4>Problems &amp; fixes</h4>{md(p)}</div>'
        if s["id"] in EXTRA:
            body += EXTRA[s["id"]]()
        if s["id"] == "S7c":
            body += cells_table()
        body += "</section>"
        if s["id"] == "S9":   # duties go after the method sections that precede them
            pass
    duty_html = "".join(duty_block(*d) for d in DUTIES)
    wp = {}
    try:
        wp = json.loads((R / "results/u666/winding_props.json").read_text())["rows"][0]
    except Exception:
        pass

    def f(k, dg=3):
        return f"{wp[k]:.{dg}g}" if k in wp else "pending"
    formula = f"""<section id="formula"><h2>Winding formula</h2>
<p>Slot fill Kf = 47.51 / 85.54 = {f('f_copper')}. <code>k_T = k_m + f_c / ( 1/(k_c - k_m) + (1 - f_c) / (2 k_m) )</code> (Hashin-Shtrikman lower bound) = {f('k_transverse_HS_lower')} W/m K;
<code>k_ax = f_c k_c + (1 - f_c) k_m</code> = {f('k_axial_ROM')} W/m K; rho {f('rho_homog',4)} kg/m3, cp {f('cp_homog',4)} J/kg K; liner R = 0.25e-3/0.15 = {f('R_liner_m2K_per_W')} m2K/W.</p></section>"""
    kt = "".join(f"<tr><td>{a}</td><td>{inline(b)}</td></tr>" for a, b in knobs) or "<tr><td colspan=2>none</td></tr>"
    css = M.CSS + "\nfigure{margin:10px 0}img{max-width:100%;height:auto;border-radius:4px}figcaption{font-size:.8rem;color:var(--mut)}.mut{color:var(--mut)}.ph{color:var(--pend);font-style:italic}"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>U666 CFD Report</title><style>{css}</style></head><body><main>
<h1>U666 CFD Report</h1><p class="mut">Benchmark motor thermal CHT (OpenFOAM 12): method S0-S11, geometry and mesh figures, and the five duty runs as they finish. Generated {__import__('datetime').datetime.now():%Y-%m-%d %H:%M} from <code>results/u666/steps_log.md</code> and <code>results/u666/report/</code>. Re-run <code>python scripts/u666_report.py</code> to refresh.</p>
<div class="strip">{chips}</div>
<nav class="toc"><a href="#knobs">Knobs</a><a href="#heat">Heat paths</a><a href="#tables">Tables</a><a href="#formula">Formula</a><a href="#duties">Duties</a><a href="#feedback">Feedback</a></nav>
<section id="knobs"><h2>Open assumptions and calibration knobs</h2><div class="tw"><table><tr><th>Step</th><th>Item</th></tr>{kt}</table></div></section>
<section id="heat"><h2>Heat paths</h2>{M.SCHEM}</section>
<section id="tables"><h2>Loss table (S5)</h2>{M.table_of(byid.get('S5', {'lines': []}))}<h2>Materials table (S2)</h2>{M.table_of(byid.get('S2', {'lines': []}))}</section>
{formula}
{body}
<h2 id="duties" style="margin-top:28px">Duty results (S10)</h2>{duty_html}
{FEEDBACK}
</main></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    sz = OUT.stat().st_size
    print(OUT, f"{sz/1e6:.2f} MB")
    if sz > 14e6:
        print("WARNING: over 14 MB, lower maxw / gif count")


if __name__ == "__main__":
    main()
