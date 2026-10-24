"""WSL render step (python3 + vtk + matplotlib), single thread. Run via scripts/u666_report_render.sh (nice 19).
  geo  <geo_vtk_dir> <out_dir>      region-layout + mesh cross-sections from foamToVTK of the base case
  duty <duty_pp_dir> <out_dir> ...  per-duty figures (see duty())
"""
import sys, os, glob, json
import numpy as np
import vtk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

REG = ["housing", "stator", "winding", "wedge", "rotor", "magnets", "endcaps", "shaft", "bearings", "inair"]
COL = dict(housing="#8e99a8", stator="#4f7cb5", winding="#d9822b", wedge="#e8c547", rotor="#2f9e8f",
           magnets="#b5323c", endcaps="#8d6bb0", shaft="#444b55", bearings="#9c6b3f", inair="#cfe6f3")


def read(path):
    r = vtk.vtkGenericDataObjectReader(); r.SetFileName(path); r.Update(); return r.GetOutput()


def cut(ds, origin, normal):
    p = vtk.vtkPlane(); p.SetOrigin(*origin); p.SetNormal(*normal)
    c = vtk.vtkCutter(); c.SetCutFunction(p); c.SetInputData(ds); c.Update()
    t = vtk.vtkTriangleFilter(); t.SetInputData(c.GetOutput()); t.Update()
    return t.GetOutput()


def tris(pd):
    pts = np.array([pd.GetPoint(i) for i in range(pd.GetNumberOfPoints())])
    ids = pd.GetPolys().GetData()
    a = np.array([ids.GetValue(i) for i in range(ids.GetNumberOfValues())]).reshape(-1, 4)[:, 1:]
    return pts, a


def geo(vdir, out):
    os.makedirs(out, exist_ok=True)
    cuts = {"radial": ((0, 0, 0.030), (0, 0, 1)), "axial": ((0, 0, 0), (0, 1, 0))}
    data = {k: {} for k in cuts}
    for r in REG:
        f = os.path.join(vdir, r, "geo_0.vtk")
        if not os.path.exists(f):
            continue
        ds = read(f)
        for k, (o, n) in cuts.items():
            pts, a = tris(cut(ds, o, n))
            if len(a):
                data[k][r] = (pts, a)
    cells = {k: {r: len(v[1]) for r, v in d.items()} for k, d in data.items()}
    json.dump(cells, open(os.path.join(out, "geo_cells.json"), "w"))
    for k, d in data.items():
        # 2D coordinates (mm): radial x,y ; axial z (horizontal), x (vertical)
        def xy(pts):
            return (pts[:, [0, 1]] if k == "radial" else pts[:, [2, 0]]) * 1000
        for mode in ("layout", "mesh", "zoom"):
            fig, ax = plt.subplots(figsize=(8, 8) if k == "radial" else (11, 6), dpi=110)
            for r, (pts, a) in d.items():
                P = xy(pts)[a]
                if mode == "layout":
                    ax.add_collection(PolyCollection(P, facecolors=COL[r], edgecolors=COL[r], linewidths=0.2, label=r))
                else:
                    ax.add_collection(PolyCollection(P, facecolors=COL[r], alpha=0.35, edgecolors="#222", linewidths=0.12 if mode == "mesh" else 0.4))
            ax.set_aspect("equal")
            allp = np.vstack([xy(p) for p, _ in d.values()])
            if mode == "zoom":
                if k == "radial":
                    ax.set_xlim(35, 80); ax.set_ylim(0, 25)   # one tooth/slot sector near +x
                else:
                    ax.set_xlim(40, 100); ax.set_ylim(35, 100)  # front end winding / end space
            else:
                ax.set_xlim(allp[:, 0].min() - 3, allp[:, 0].max() + 3); ax.set_ylim(allp[:, 1].min() - 3, allp[:, 1].max() + 3)
            ax.set_xlabel("x [mm]" if k == "radial" else "z [mm]"); ax.set_ylabel("y [mm]" if k == "radial" else "x [mm]")
            if mode == "layout":
                h = [plt.Rectangle((0, 0), 1, 1, color=COL[r]) for r in d]
                ax.legend(h, list(d), ncol=5, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.08), frameon=False)
            fig.tight_layout(); fig.savefig(os.path.join(out, f"{k}_{mode}.png")); plt.close(fig)
    print("geo done", cells)


def stl_cut(path, origin, normal):
    r = vtk.vtkSTLReader(); r.SetFileName(path); r.Update()
    pd = r.GetOutput(); b = pd.GetBounds(); sc = 1e-3 if max(b[1] - b[0], b[3] - b[2]) > 10 else 1.0   # mm -> m
    p = vtk.vtkPlane(); p.SetOrigin(*[o / sc for o in origin]); p.SetNormal(*normal)
    c = vtk.vtkCutter(); c.SetCutFunction(p); c.SetInputData(pd); c.Update()
    o = c.GetOutput(); pts = np.array([o.GetPoint(i) for i in range(o.GetNumberOfPoints())]) * sc
    ids = o.GetLines().GetData(); a = np.array([ids.GetValue(i) for i in range(ids.GetNumberOfValues())])
    seg, j = [], 0
    while j < len(a):
        k = a[j]; l = a[j + 1:j + 1 + k]; seg += [(l[q], l[q + 1]) for q in range(k - 1)]; j += 1 + k
    return pts, np.array(seg)


def regions(vdir, out):
    """one panel per region: cut cells with edges, own crop; radial z=30 mm and axial y=0."""
    os.makedirs(out, exist_ok=True)
    cuts = {"radial": ((0, 0, 0.030), (0, 0, 1)), "axial": ((0, 0, 0), (0, 1, 0))}
    info = {}
    for k, (o, n) in cuts.items():
        items = []
        for r in REG:
            f = os.path.join(vdir, r, "geo_0.vtk")
            if not os.path.exists(f):
                continue
            ds = read(f); pts, a = tris(cut(ds, o, n))
            if len(a):
                xy = (pts[:, [0, 1]] if k == "radial" else pts[:, [2, 0]]) * 1000
                items.append((r, xy[a], ds.GetNumberOfCells()))
        n_ = len(items); cols = 3; rows = (n_ + cols - 1) // cols
        fig, axs = plt.subplots(rows, cols, figsize=(14, 4.4 * rows), dpi=100); axs = np.atleast_2d(axs)
        for ax in axs.ravel():
            ax.axis("off")
        for ax, (r, P, nc) in zip(axs.ravel(), items):
            ax.add_collection(PolyCollection(P, facecolors=COL[r], alpha=0.45, edgecolors="#111", linewidths=0.25))
            ax.set_xlim(P[..., 0].min() - 2, P[..., 0].max() + 2); ax.set_ylim(P[..., 1].min() - 2, P[..., 1].max() + 2)
            ax.set_aspect("equal"); ax.set_title(f"{r}: {nc} cells in region, {len(P)} cut", fontsize=10)
        fig.tight_layout(); fig.savefig(os.path.join(out, f"regions_{k}.png")); plt.close(fig)
        info[k] = {r: nc for r, _, nc in items}
    json.dump(info, open(os.path.join(out, "region_cells.json"), "w"))
    print("regions done")


def overlay(vdir, stl, out):
    """CAD housing (STL cut, red lines) over the simplified housing (cut cells, grey): axial y=0, radial z=30 mm, fin zoom."""
    os.makedirs(out, exist_ok=True)
    ds = read(os.path.join(vdir, "housing", "geo_0.vtk"))
    cuts = {"axial": ((0, 0, 0), (0, 1, 0)), "radial": ((0, 0, 0.030), (0, 0, 1))}
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.4), dpi=100)
    for ax, (k, zoom) in zip(axs, (("axial", False), ("radial", False), ("axial", True))):
        o, n = cuts[k]
        pts, a = tris(cut(ds, o, n)); cp, seg = stl_cut(stl, o, n)
        f = (lambda p: (p[:, [0, 1]] if k == "radial" else p[:, [2, 0]]) * 1000)
        ax.add_collection(PolyCollection(f(pts)[a], facecolors="#9aa3ae", edgecolors="none", alpha=0.8))
        c2 = f(cp)
        ax.add_collection(matplotlib.collections.LineCollection(c2[seg], colors="#d32f2f", linewidths=0.7))
        ax.set_aspect("equal")
        if zoom:
            ax.set_xlim(-10, 70); ax.set_ylim(60, 110)
        else:
            ax.set_xlim(f(pts)[:, 0].min() - 5, f(pts)[:, 0].max() + 5); ax.set_ylim(f(pts)[:, 1].min() - 5, f(pts)[:, 1].max() + 5)
        ax.set_title({"axial": "axial y = 0 (z horizontal)", "radial": "radial z = 30 mm"}[k] + (", zoom on the fins" if zoom else ""), fontsize=10)
        ax.set_xlabel("z [mm]" if k == "axial" else "x [mm]"); ax.set_ylabel("x [mm]" if k == "axial" else "y [mm]")
    fig.suptitle("housing: CAD cut (red lines) over the simplified housing used in the mesh (grey cells)", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(out, "housing_overlay.png")); plt.close(fig)
    print("overlay done")


def air(vtkfile, out):
    """velocity and temperature on two planes of the external-air case (foamToVTK internalMesh of the final time)."""
    os.makedirs(out, exist_ok=True)
    ds = read(vtkfile)
    planes = {"x = 0 (axial, vertical)": ((0, 0, 0), (1, 0, 0), (2, 1)), "z = 30 mm (cross-section)": ((0, 0, 0.030), (0, 0, 1), (0, 1))}
    for name, fld, cmap, lab in (("air_U", "U", "viridis", "|U| [m/s]"), ("air_T", "T", "inferno", "T [C]")):
        fig, axs = plt.subplots(1, 2, figsize=(13, 6.5), dpi=100)
        data = []
        for pn, (o, n, ax_) in planes.items():
            p = vtk.vtkPlane(); p.SetOrigin(*o); p.SetNormal(*n)
            c = vtk.vtkCutter(); c.SetCutFunction(p); c.SetInputData(ds); c.Update()
            t = vtk.vtkTriangleFilter(); t.SetInputData(c.GetOutput()); t.Update(); g = t.GetOutput()
            pts, a = tris(g); arr = g.GetPointData().GetArray(fld)
            v = np.array([np.linalg.norm(arr.GetTuple3(i)) if fld == "U" else arr.GetValue(i) - 273.15 for i in range(g.GetNumberOfPoints())])
            data.append((pn, pts[:, list(ax_)] * 1000, a, v))
        vmax = max(d[3].max() for d in data); vmin = 40.0 if fld == "T" else 0.0
        for ax, (pn, xy, a, v) in zip(axs, data):
            tp = ax.tripcolor(xy[:, 0], xy[:, 1], a, v, shading="gouraud", cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_aspect("equal"); ax.set_xlim(-250, 300 if pn.startswith("x") else 250); ax.set_ylim(-250, 400)
            ax.set_title(pn, fontsize=10); ax.set_xlabel("z [mm]" if pn.startswith("x") else "x [mm]"); ax.set_ylabel("y [mm] (up)")
        fig.colorbar(tp, ax=axs, label=lab, shrink=0.8); fig.savefig(os.path.join(out, name + ".png")); plt.close(fig)
    print("air done")


def hmap(vdir, hjson, hbak, out):
    """h on the housing + shaft faces: unwrapped (theta, z), two 3D views, and the faces that were h = 0."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    os.makedirs(out, exist_ok=True)
    H, B = json.load(open(hjson)), json.load(open(hbak))
    P, hv, bv = [], [], []
    for reg in ("housing", "shaft"):
        f = glob.glob(os.path.join(vdir, reg, "defaultFaces", "*.vtk"))[0]
        pd = read(f); pts = np.array([pd.GetPoint(i) for i in range(pd.GetNumberOfPoints())]); ids = pd.GetPolys().GetData()
        a = np.array([ids.GetValue(i) for i in range(ids.GetNumberOfValues())]); polys, j = [], 0
        while j < len(a):
            k = a[j]; polys.append(pts[a[j + 1:j + 1 + k]]); j += 1 + k
        h = np.array(H[reg]["defaultFaces"]); b = np.array(B[reg]["defaultFaces"])
        assert len(h) == len(polys), (reg, len(h), len(polys))
        P += polys; hv += list(h); bv += list(b)
    hv, bv = np.array(hv), np.array(bv)
    cen = np.array([p.mean(0) for p in P]) * 1000
    th = np.degrees(np.arctan2(cen[:, 1], cen[:, 0])); rr = np.hypot(cen[:, 0], cen[:, 1]); o = np.argsort(rr)
    fig, axs = plt.subplots(2, 1, figsize=(13, 9), dpi=100)
    sc = axs[0].scatter(cen[o, 2], th[o], c=np.clip(hv[o], 0, 8), s=1.5, cmap="viridis", vmin=0, vmax=8)
    axs[0].set_title("h on the housing and shaft faces, unwrapped (outermost radius drawn last)")
    fig.colorbar(sc, ax=axs[0], label="h [W/m2K] (clipped at 8; fin max 36)")
    ch = bv == 0
    axs[1].scatter(cen[o, 2], th[o], c="#cfcfcf", s=1.5); oo = o[ch[o]]
    axs[1].scatter(cen[oo, 2], th[oo], c="#d32f2f", s=2.5)
    axs[1].set_title(f"faces that had h = 0 in the CFD map (red, {ch.sum()} faces) and were set to 2.5 W/m2K")
    for ax in axs:
        ax.set_xlabel("z [mm]"); ax.set_ylabel("theta around the axis [deg]")
    fig.tight_layout(); fig.savefig(os.path.join(out, "h_unwrapped.png")); plt.close(fig)
    areas = np.array([sum(0.5 * np.linalg.norm(np.cross(p[q] - p[0], p[q + 1] - p[0])) for q in range(1, len(p) - 1)) for p in P])
    json.dump(dict(zero_faces=int(ch.sum()), zero_area_cm2=float(areas[ch].sum() * 1e4), total_area_cm2=float(areas.sum() * 1e4),
                   h_area_mean=float((hv * areas).sum() / areas.sum())), open(os.path.join(out, "hmap_stats.json"), "w"))
    col = matplotlib.colormaps["viridis"](np.clip(hv, 0, 8) / 8)
    fig = plt.figure(figsize=(14, 6.5), dpi=100)
    for i, (el, az) in enumerate(((20, -60), (20, 120))):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection([p[:, [2, 0, 1]] * 1000 for p in P], facecolors=col, edgecolors="none", linewidths=0))
        ax.view_init(el, az)
        ax.set_xlim(-30, 120); ax.set_ylim(-90, 90); ax.set_zlim(-90, 90); ax.set_box_aspect((150, 180, 180)); ax.set_axis_off()
    fig.suptitle("h map on the housing and shaft (viridis 0..8 W/m2K): two views", fontsize=12)
    fig.savefig(os.path.join(out, "h_3d.png")); plt.close(fig)
    print("hmap done")


if __name__ == "__main__":
    if sys.argv[1] == "geo":
        geo(sys.argv[2], sys.argv[3])
    elif sys.argv[1] in ("regions", "overlay", "air", "hmap"):
        globals()[sys.argv[1]](*sys.argv[2:])
    else:
        import u666_report_duty as D
        D.run(sys.argv[2:])
