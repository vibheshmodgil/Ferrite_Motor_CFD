"""Render results/u666/steps_log.md (+ json) into Report/U666_method.html. stdlib only, idempotent."""
import html, json, re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
LOG = R / "results/u666/steps_log.md"
OUT = R / "Report/U666_method.html"
e = html.escape


def inline(s):
    s = e(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(CALIBRATION KNOB|PLACEHOLDER|PENDING)", r"<mark>\1</mark>", s)
    return s


def md(lines):
    """minimal markdown: bullets (2-level), tables, paragraphs."""
    out, i, depth = [], 0, 0

    def close(to=0):
        nonlocal depth
        while depth > to:
            out.append("</ul>")
            depth -= 1

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            close()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| ]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = "<div class=tw><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>"
            for r in rows[1:]:
                t += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        m = re.match(r"^(\s*)- (.*)", ln)
        if m:
            d = 1 + len(m.group(1)) // 2
            while depth < d:
                out.append("<ul>")
                depth += 1
            close(d)
            out.append(f"<li>{inline(m.group(2))}</li>")
        elif ln.strip():
            close()
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    close()
    return "\n".join(out)


def parse():
    secs, cur = [], None
    for ln in LOG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (S\d+)\s*(.*)", ln)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "lines": []}
            secs.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
    return secs


def status(s):
    if "pending" in s["title"].lower():
        return "pending"
    if re.search(r"status:\s*in progress", "\n".join(s["lines"]).lower()):
        return "in progress"
    return "done"


def pick(lines, key):
    """top-level bullets whose head matches key, with their indented children."""
    res, on = [], False
    for ln in lines:
        if ln.startswith("- "):
            on = bool(re.match(rf"^- \**({key})", ln, re.I))
        elif ln.strip() and not ln.startswith(" "):
            on = False
        if on:
            res.append(ln)
    return res


def table_of(sec):
    ls = [l for l in sec["lines"] if l.startswith("|")]
    return md(ls) if ls else "<p>pending</p>"


SCHEM = """<svg viewBox="0 0 640 330" role="img" aria-label="Heat path schematic" style="width:100%;height:auto">
<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0L8,4L0,8z" fill="var(--ink)"/></marker></defs>
<g font-size="12" fill="var(--ink)">
<g fill="var(--card)" stroke="var(--line)"><rect x="10" y="30" width="90" height="36" rx="6"/><rect x="150" y="30" width="80" height="36" rx="6"/><rect x="280" y="30" width="80" height="36" rx="6"/><rect x="410" y="30" width="90" height="36" rx="6"/><rect x="540" y="30" width="90" height="36" rx="6"/>
<rect x="10" y="130" width="90" height="36" rx="6"/><rect x="150" y="130" width="80" height="36" rx="6"/><rect x="540" y="130" width="90" height="36" rx="6"/>
<rect x="10" y="230" width="90" height="36" rx="6"/><rect x="150" y="230" width="80" height="36" rx="6"/><rect x="280" y="230" width="80" height="36" rx="6"/><rect x="410" y="230" width="90" height="36" rx="6"/></g>
<g stroke="var(--ink)" marker-end="url(#ar)" fill="none"><path d="M100 48H148"/><path d="M230 48H278"/><path d="M360 48H408"/><path d="M500 48H538"/>
<path d="M55 130V68"/><path d="M100 148H148"/><path d="M230 140L585 68"/><path d="M230 155L540 148"/>
<path d="M55 230V168"/><path d="M100 248H148"/><path d="M230 248H278"/><path d="M360 248H408"/><path d="M500 240L585 168"/><path d="M585 130V68"/><path d="M320 230V68"/><path d="M190 130V68" stroke-dasharray="3"/></g>
<g stroke="none"><text x="20" y="52">Winding</text><text x="160" y="52">liner R</text><text x="300" y="52">Stator</text><text x="418" y="52">shrink-fit R</text><text x="552" y="52">Housing</text>
<text x="14" y="152">Winding ends</text><text x="170" y="152">inair</text><text x="545" y="152">h + radiation</text><text x="545" y="182">to ambient</text>
<text x="20" y="252">Rotor</text><text x="165" y="252">air gap</text><text x="296" y="252">Shaft</text><text x="418" y="252">Bearings</text>
<text x="20" y="300">Paths: winding, liner R, stator, shrink-fit R, housing, h + radiation, ambient.</text><text x="20" y="318">Ends to inair to housing/rotor; rotor to air gap to stator; rotor to shaft to bearings to housing.</text></g></g></svg>"""

CSS = """:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mut:#5b6675;--line:#d5dae1;--acc:#1f5fae;--done:#2e7d32;--prog:#b26a00;--pend:#7a828e;--warn:#fff3c4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#12161c;--card:#1a2029;--ink:#e6e9ee;--mut:#9aa4b2;--line:#303846;--acc:#6aa7f0;--done:#6fcf7a;--prog:#f0b24a;--pend:#8d96a3;--warn:#4a4217}}
:root[data-theme="dark"]{--bg:#12161c;--card:#1a2029;--ink:#e6e9ee;--mut:#9aa4b2;--line:#303846;--acc:#6aa7f0;--done:#6fcf7a;--prog:#f0b24a;--pend:#8d96a3;--warn:#4a4217}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;padding:0 16px 40px;overflow-x:hidden}
main{max-width:960px;margin:auto}h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:0}h4{margin:.2rem 0}
section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:14px 0;scroll-margin-top:90px}
.strip{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0;display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--line)}
.chip{display:inline-block;border:1px solid currentColor;border-radius:12px;padding:1px 9px;font-size:.8rem;text-decoration:none;font-weight:600}
.chip small{display:block;font-weight:400;font-size:.65rem}.done{color:var(--done)}.inprogress{color:var(--prog)}.pending{color:var(--pend)}
nav.toc{background:var(--bg);display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.85rem;padding:6px 0}a{color:var(--acc)}
.box{border-left:4px solid var(--prog);background:var(--bg);padding:6px 10px;margin:8px 0}.box.a{border-color:var(--acc)}
.tw{overflow-x:auto;max-width:100%}table{border-collapse:collapse;font-size:.85rem}td,th{border:1px solid var(--line);padding:3px 7px;text-align:left;vertical-align:top}
code{background:var(--bg);padding:0 3px;border-radius:3px;word-break:break-word}mark{background:var(--warn);color:var(--ink);padding:0 3px}
ul{padding-left:1.2rem;margin:.3rem 0}"""


def main():
    secs = parse()
    byid = {s["id"]: s for s in secs}
    for s in secs:
        s["st"] = status(s)
    try:
        wp = json.loads((R / "results/u666/winding_props.json").read_text())["rows"][0]
    except Exception:
        wp = {}
    try:
        geo = (R / "mesh/u666/geo.log").read_text().strip().splitlines()[-1]
    except Exception:
        geo = "pending"

    knobs, qs = [], []
    for s in secs:
        for ln in s["lines"]:
            if ln.startswith("|") and not re.search(r"placeholder|pending", ln, re.I):
                continue
            t = re.sub(r"^\s*- ", "", ln).strip()
            if re.search(r"calibration knob|placeholder|pending|to be re-checked", ln, re.I):
                knobs.append((s["id"], t))
            if "?" in ln or re.search(r"user (confirmation|split)", ln, re.I):
                qs.append((s["id"], t))

    def cls(s):
        return s["st"].replace(" ", "")

    chips = "".join(f'<a class="chip {cls(s)}" href="#{s["id"]}">{s["id"]}<small>{s["st"]}</small></a>' for s in secs)
    toc = "".join(f'<a href="#{s["id"]}">{s["id"]} {e(s["title"].split("—")[0].strip())}</a>' for s in secs)
    body = ""
    for s in secs:
        a = pick(s["lines"], "assumption")
        p = pick(s["lines"], r"problem|attempt|open question")
        used = set(map(id, a)) | set(map(id, p))
        rest = [l for l in s["lines"] if id(l) not in used]
        body += f'<section id="{s["id"]}"><h2>{s["id"]} {inline(s["title"])} <span class="chip {cls(s)}">{s["st"]}</span></h2>{md(rest)}'
        if a:
            body += f'<div class="box a"><h4>Assumptions</h4>{md(a)}</div>'
        if p:
            body += f'<div class="box"><h4>Problems &amp; fixes</h4>{md(p)}</div>'
        if s["id"] == "S4":
            body += f"<p>Latest geo.log line: <code>{e(geo)}</code></p>"
        body += "</section>"

    def f(k, d=3):
        return f"{wp[k]:.{d}g}" if k in wp else "pending"

    formula = f"""<section id="formula"><h2>Winding formula</h2>
<p>Slot fill Kf = A_copper / A_winding = 47.51 / 85.54 = {f('f_copper')}. Matrix (varnish + enamel) k_m = 0.2 to 0.25 W/m·K, copper k_c.</p>
<p><b>Transverse, Hashin–Shtrikman lower bound:</b><br><code>k_T = k_m + f_c / ( 1/(k_c − k_m) + (1 − f_c) / (2 k_m) )</code><br>
result k_T = {f('k_transverse_HS_lower')} W/m·K (strand bundle {f('k_strand_bundle_HS')}; layered Wiener check {f('k_transverse_layered_check')}, judged too pessimistic).</p>
<p><b>Axial, rule of mixtures:</b> <code>k_ax = f_c·k_c + (1 − f_c)·k_m</code> = {f('k_axial_ROM')} W/m·K.</p>
<p><b>Density, heat capacity (mass weighted):</b> <code>rho = Σ f_i rho_i</code>, <code>cp = Σ f_i rho_i cp_i / rho</code> gives rho {f('rho_homog',4)} kg/m³, cp {f('cp_homog',4)} J/kg·K.
Fractions: copper {f('f_copper')}, enamel {f('f_enamel')}, varnish {f('f_varnish')}.</p>
<p><b>Liner:</b> R = t/k = 0.25e-3 / 0.15 = {f('R_liner_m2K_per_W')} m²K/W.</p></section>"""

    kt = "".join(f"<tr><td>{a}</td><td>{inline(b)}</td></tr>" for a, b in knobs) or "<tr><td colspan=2>none</td></tr>"
    qt = "".join(f"<li><b>{a}</b> {inline(b)}</li>" for a, b in qs) or "<li>none</li>"
    empty = {"lines": []}

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>U666 CFD Method Log</title><style>{CSS}</style></head><body><main>
<h1>U666 CFD Method Log</h1><p style="color:var(--mut)">Benchmark motor: tune the CFD to the test, then apply to our motor. Generated from <code>results/u666/steps_log.md</code>; values not in the sources are shown as pending.</p>
<div class="strip">{chips}</div><nav class="toc"><a href="#knobs">Knobs</a><a href="#questions">Questions</a><a href="#heat">Heat paths</a><a href="#tables">Tables</a><a href="#formula">Formula</a>{toc}</nav>
<section id="knobs"><h2>Calibration knobs (check first if the CFD does not match the test)</h2><div class="tw"><table><tr><th>Step</th><th>Item</th></tr>{kt}</table></div></section>
<section id="questions"><h2>Open questions for the user</h2><ul>{qt}</ul></section>
<section id="heat"><h2>Heat paths</h2>{SCHEM}</section>
<section id="tables"><h2>Loss table (S5)</h2>{table_of(byid.get('S5', empty))}<h2>Materials table (S2)</h2>{table_of(byid.get('S2', empty))}</section>
{formula}
{body}</main></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
