"""Section pictures of the temperature field for the report (ParaView pvpython, offscreen).

    pvpython render.py <slices_dir> <out_prefix> "<title>" [Tmin Tmax]

Reads <region>_z.vtk / <region>_x.vtk written by slices.sh; writes <out_prefix>_z.png and _x.png in deg C.
"""
import glob, os, sys
from paraview.simple import *

src, out, title = sys.argv[1:4]
rng = [float(v) for v in sys.argv[4:6]] if len(sys.argv) > 5 else None

for ax, cam in (("z", ((0, 0, 0.6), (0, 1, 0))), ("x", ((0.6, 0, 0), (0, 1, 0)))):
    files = sorted(glob.glob(os.path.join(src, f"*_{ax}.vtk")))
    if not files:
        continue
    parts = [LegacyVTKReader(FileNames=[f]) for f in files]
    data = AppendDatasets(Input=parts)
    tc = Calculator(Input=data, AttributeType="Point Data", ResultArrayName="T_C", Function="T-273.15")
    v = CreateRenderView(); v.ViewSize = [1600, 1150]; v.OrientationAxesVisibility = 0
    v.Background = [1, 1, 1]; v.UseColorPaletteForBackground = 0
    d = Show(tc, v); ColorBy(d, ("POINTS", "T_C"))
    lut = GetColorTransferFunction("T_C"); lut.ApplyPreset("Turbo", True)
    lo, hi = rng or tc.PointData["T_C"].GetRange()
    lut.RescaleTransferFunction(lo, hi)
    # region outlines: feature edges of each slice, thin grey
    for p in parts:
        e = Show(FeatureEdges(Input=p, BoundaryEdges=1, FeatureEdges=0, NonManifoldEdges=0), v)
        e.AmbientColor = e.DiffuseColor = [0.25, 0.25, 0.25]; e.LineWidth = 1.2; e.ColorArrayName = ['POINTS', '']
    bar = GetScalarBar(lut, v); bar.Title = "Temperature [°C]"; bar.ComponentTitle = ""
    bar.TitleColor = bar.LabelColor = [0.1, 0.1, 0.1]; bar.TitleFontSize = 20; bar.LabelFontSize = 18
    bar.Orientation = "Vertical"; bar.WindowLocation = "Any Location"; bar.Position = [0.86, 0.15]
    bar.ScalarBarLength = 0.7; bar.RangeLabelFormat = "{:.0f}"; bar.AutomaticLabelFormat = 0; bar.LabelFormat = "{:.0f}"; d.SetScalarBarVisibility(v, True)
    t = Text(Text=title + ("  —  mid-stack section (z = 5 mm)" if ax == "z" else "  —  axial section (x = 0)"))
    td = Show(t, v); td.Color = [0.1, 0.1, 0.1]; td.FontSize = 22; td.WindowLocation = "Upper Left Corner"
    for s, pos in ((("Drive end (output)", [0.6, 0.06]), ("Rear (busbar side)", [0.16, 0.06])) if ax == "x" else ()):
        n = Show(Text(Text=s), v); n.Color = [0.35, 0.35, 0.35]; n.FontSize = 18; n.WindowLocation = "Any Location"; n.Position = pos
    v.CameraPosition, v.CameraViewUp = cam; v.CameraFocalPoint = (0, 0, 0 if ax == "z" else 0.0)
    v.CameraParallelProjection = 1; ResetCamera(v); v.CameraParallelScale *= 0.92
    SaveScreenshot(f"{out}_{ax}.png", v, ImageResolution=[1600, 1150], TransparentBackground=0)
    print("wrote", f"{out}_{ax}.png", "range", lo, hi)
    Delete(v)
