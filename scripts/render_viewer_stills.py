"""Report stills from the site's 3D viewer (headless Chrome, no WSL load): exploded and rotor views per detailed point.

    .venv/Scripts/python -I scripts/render_viewer_stills.py [duty4 ...]     -> results/figs_duty/3d_det_<lp>_{exploded,rotor}.png
Needs the viewer data (export_viewer.py) and the site (make_report_duty.py --site). Skips a shot if available RAM < 1.5 GB.
"""
import json, os, subprocess, sys, tempfile, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_viewer import OUTD, guard
import make_report_duty as M

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PAGE = os.path.join(M.OUT, "Design9795_site", "viewer3d.html")
ALLP = "housing,stator,winding,busbar,strap,tbar,resin,bobbin,rotor,magnets,shaft,bearings"


def shot(out, **q):
    guard()
    url = "file:///" + os.path.abspath(PAGE).replace("\\", "/") + "?shot&" + urllib.parse.urlencode(q)
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        f"--user-data-dir={prof}", "--virtual-time-budget=30000", "--window-size=1400,900", "--hide-scrollbars",
                        f"--screenshot={out}", url], check=True, capture_output=True, timeout=180)
    from PIL import Image, ImageOps
    im = Image.open(out).convert("RGB")
    box = ImageOps.invert(im).getbbox()                 # drop the empty white band below the model
    im.crop((0, 0, im.width, min(im.height, box[3] + 30))).save(out)
    print("wrote", out)


if __name__ == "__main__":
    man = json.loads(open(os.path.join(OUTD, "manifest.js")).read().split("=", 1)[1].rstrip().rstrip(";"))["entries"]
    for lp in sys.argv[1:] or [k.split("/")[0] for k in man if k.endswith("/detailed")]:
        e = man[f"{lp}/detailed"]; t = e["times"][-1]
        name = f"{lp}, detailed model"
        shot(os.path.join(M.FG, f"3d_det_{lp}_exploded.png"), lp=lp, model="detailed", t=t, ex=650, cx=500, cz=1000, parts=ALLP, zoom=1.15,
             title=f"{name}: exploded half section")
        shot(os.path.join(M.FG, f"3d_det_{lp}_cut.png"), lp=lp, model="detailed", t=t, ex=0, cx=500, cz=1000, parts=ALLP,
             title=f"{name}: half section")
        shot(os.path.join(M.FG, f"3d_det_{lp}_rotor.png"), lp=lp, model="detailed", t=t, ex=0, cx=500, cz=1000,
             parts="rotor,magnets,shaft,bearings", zoom=1.3, title=f"{name}: rotor, magnets, shaft and bearings")
