"""SolidWorks for motor variant 65: native sweep of the 65 mm coil, every STEP part -> SLDPRT (coloured),
MOTOR_65.SLDASM from instances.json, then MOTOR_65.step.
    python sw_build_motor65.py
"""
import json, math, os, time
import numpy as np
import pythoncom, win32com.client
from win32com.client import VARIANT, gencache

D = os.path.dirname(os.path.abspath(__file__))
I = json.load(open(os.path.join(D, "instances.json")))
NUL = VARIANT(pythoncom.VT_DISPATCH, None)
sw = win32com.client.Dispatch("SldWorks.Application")
sw.Visible = True
ref = lambda v=0: VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, v)
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    log.append(s)


def save_as(doc, path, opts=1):
    e, w = ref(), ref()
    ok = doc.Extension.SaveAs3(path, 0, opts, NUL, NUL, e, w)
    say("  saved %-34s %s err %s" % (os.path.basename(path), ok, e.value))
    return ok


def import_step(name, color, transparency=0.0):
    out = os.path.join(D, name + ".SLDPRT")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(os.path.join(D, name + ".step")):
        return out                                          # already imported from this STEP
    p = os.path.join(D, name + ".step")
    doc = sw.LoadFile4(p, "r", sw.GetImportFileData(p), ref())
    sol, sht = doc.GetBodies2(0, True), doc.GetBodies2(1, True)
    ns, nh = (0 if sol is None else len(sol)), (0 if sht is None else len(sht))
    say("  %-28s solids %d sheets %d%s" % (name, ns, nh, "" if nh == 0 and ns >= 1 else "   <-- PROBLEM"))
    doc.MaterialPropertyValues = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [*color, 1.0, 1.0, 0.5, 0.4, transparency, 0.0])
    save_as(doc, out)
    sw.CloseDoc(doc.GetTitle)
    return out


say("SolidWorks rev", sw.RevisionNumber)
sw.CloseAllDocuments(True)
paths = {}
CLEAR = {"housing": 0.55, "rear_cover": 0.55, "terminal_cap": 0.5}     # see-through so the inside is visible in the assembly
for name, p in I["parts"].items():
    paths[name] = import_step(name, p["color"], CLEAR.get(name, 0.0))
STATOR = {"tooth_65": (0.35, 0.37, 0.40), "bobbin_A_65": (0.95, 0.85, 0.30), "bobbin_B_65": (0.95, 0.85, 0.30),
          "busbar_L1_65": (1.00, 0.62, 0.26), "busbar_L2_65": (0.13, 0.76, 0.84), "busbar_L3_65": (0.78, 0.49, 1.00),
          "link_strap_65": (0.85, 0.85, 0.88)}
for name, col in STATOR.items():
    paths[name] = import_step(name, col)


def build_coil():                                   # native SolidWorks sweep, OD 3.00, as the v7 coil
    out = os.path.join(D, "04_coil_65.SLDPRT")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(os.path.join(D, "coil_65_centreline.npy")):
        return out
    W = np.load(os.path.join(D, "coil_65_centreline.npy"))
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(W, axis=0), axis=1))])
    Q = W[np.unique(np.searchsorted(s, np.append(np.arange(0, s[-1], 0.5), s[-1])))]
    doc = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
    sm = doc.SketchManager
    sm.Insert3DSketch(True)
    sm.AddToDB = True
    sm.CreateSpline2(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) / 1000.0 for v in Q.ravel()]), True)
    sm.AddToDB = False
    sm.Insert3DSketch(True)
    doc.ClearSelection2(True)
    doc.Extension.SelectByID2("3DSketch1", "SKETCH", 0, 0, 0, False, 4, NUL, 0)
    doc.FeatureManager.InsertProtrusionSwept4(False, False, 0, False, False, 0, 0, False, 0, 0, 0, 0, True, True, True, 0, True, True, 0.003, 0)
    sol, sht = doc.GetBodies2(0, True), doc.GetBodies2(1, True)
    vol = sol[0].GetMassProperties(1.0)[3] * 1e9 if sol else 0
    say("  coil sweep: solids %d sheets %d  volume %.0f mm3 (pi*1.5^2*L %.0f)" % (0 if sol is None else len(sol), 0 if sht is None else len(sht), vol, math.pi * 2.25 * s[-1]))
    doc.MaterialPropertyValues = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0.78, 0.44, 0.16, 1.0, 1.0, 0.6, 0.4, 0.0, 0.0])
    save_as(doc, out)
    save_as(doc, os.path.join(D, "04_coil_65.step"), 1 | 2)
    sw.CloseDoc(doc.GetTitle)
    return out


paths["04_coil_65"] = build_coil()
for i in I["instances"]:
    paths.setdefault(i["part"], os.path.join(D, i["part"] + ".SLDPRT"))
for p in sorted(set(paths.values())):
    sw.OpenDoc6(p, 1, 1, "", ref(), ref())

_la = pythoncom.LoadTypeLib(os.path.join(sw.GetExecutablePath, "sldworks.tlb")).GetLibAttr()   # SW2026: property = install folder
SWT = gencache.GetModuleForTypelib(_la[0], _la[1], _la[3], _la[4])
mu = SWT.IMathUtility(SWT.ISldWorks(sw._oleobj_).GetMathUtility()._oleobj_)

asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
asm = sw.ActiveDoc
comps = []
t = time.time()
for i in I["instances"]:
    R, tr = i["R"], i["t"]
    c = asm.AddComponent5(paths[i["part"]], 0, "", False, "", 0.0, 0.0, 0.0)
    arr = [R[0][0], R[1][0], R[2][0], R[0][1], R[1][1], R[2][1], R[0][2], R[1][2], R[2][2],
           tr[0] / 1000.0, tr[1] / 1000.0, tr[2] / 1000.0, 1.0, 0.0, 0.0, 0.0]          # axes as columns, translation in m
    SWT.IComponent2(c._oleobj_).Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, arr))
    comps.append(c)
say("  %d components placed (%.0f s)" % (len(comps), time.time() - t))
asm.ClearSelection2(True)
for c in comps:
    c.Select4(True, NUL, False)
asm.FixComponent()
asm.ForceRebuild3(False)
asm.ShowNamedView2("*Isometric", 7)
asm.ViewZoomtofit2()
save_as(asm, os.path.join(D, "MOTOR_65.SLDASM"))
save_as(asm, os.path.join(D, "MOTOR_65.step"), 1 | 2)
say("  MOTOR_65: %d components" % asm.GetComponentCount(False))
open(os.path.join(D, "sw_build.log"), "w").write("\n".join(log) + "\n")
