"""Airflow pictures for the report (pvpython, offscreen).

    pvpython render_air.py <vtk_dir> <out_prefix> <kind> "<title>"
kind = external : air_z.vtk / air_x.vtk  -> _speed_{z,x}.png, _temp_{z,x}.png ; motor_skin.vtk -> _h.png
kind = internal : inair_z.vtk / inair_x.vtk -> same names
"""
import os, sys
from paraview.simple import *

src, out, kind, title = sys.argv[1:5]
DT = 60.0                                   # external CFD: skin 100 C, ambient 40 C


def view():
    v = CreateRenderView(); v.ViewSize = [1600, 1150]; v.OrientationAxesVisibility = 0
    v.Background = [1, 1, 1]; v.UseColorPaletteForBackground = 0
    return v


def bar(lut, v, d, name, fmt="{:.2f}"):
    b = GetScalarBar(lut, v); b.Title = name; b.ComponentTitle = ""
    b.TitleColor = b.LabelColor = [0.1, 0.1, 0.1]; b.TitleFontSize = 20; b.LabelFontSize = 18
    b.WindowLocation = "Any Location"; b.Position = [0.87, 0.15]; b.ScalarBarLength = 0.7
    b.AutomaticLabelFormat = 0; b.LabelFormat = fmt; b.RangeLabelFormat = fmt
    d.SetScalarBarVisibility(v, True)


def label(v, text):
    t = Show(Text(Text=text), v); t.Color = [0.1, 0.1, 0.1]; t.FontSize = 22; t.WindowLocation = "Upper Left Corner"


def camera(v, ax, zoom):
    v.CameraPosition = (0, 0, 1) if ax == "z" else (1, 0, 0)
    v.CameraFocalPoint = (0, 0, 0); v.CameraViewUp = (0, 1, 0); v.CameraParallelProjection = 1
    ResetCamera(v); v.CameraParallelScale *= zoom


pre = "air" if kind == "external" else "inair"
for ax in ("z", "x"):
    f = os.path.join(src, f"{pre}_{ax}.vtk")
    if not os.path.exists(f):
        continue
    plane = LegacyVTKReader(FileNames=[f])
    sp = Calculator(Input=plane, AttributeType="Point Data", ResultArrayName="speed", Function="mag(U)")
    tc = Calculator(Input=sp, AttributeType="Point Data", ResultArrayName="T_C", Function="T-273.15")
    where = "radial mid-plane (z = 5 mm)" if (ax == "z" and kind == "external") else \
            "radial plane in the drive-end space (z = -40 mm)" if ax == "z" else "axial mid-plane (x = 0)"
    zoom = 0.75 if kind == "external" else 0.95
    # speed + direction arrows
    v = view(); d = Show(tc, v); ColorBy(d, ("POINTS", "speed"))
    lut = GetColorTransferFunction("speed"); lut.ApplyPreset("Viridis", True)
    hi = tc.PointData["speed"].GetRange()[1]; lut.RescaleTransferFunction(0.0, hi)
    g = Glyph(Input=tc, GlyphType="Arrow"); g.OrientationArray = ["POINTS", "U"]; g.ScaleArray = ["POINTS", "No scale array"]
    g.ScaleFactor = 0.012 if kind == "external" else 0.004
    g.GlyphMode = "Uniform Spatial Distribution (Surface Sampling)"; g.MaximumNumberOfSamplePoints = 900
    gd = Show(g, v); gd.AmbientColor = gd.DiffuseColor = [1, 1, 1]; gd.ColorArrayName = ["POINTS", ""]; gd.Opacity = 0.85
    bar(lut, v, d, "Air speed [m/s]", "{:.2f}" if hi < 5 else "{:.1f}")
    label(v, f"{title}: air speed, {where}")
    camera(v, ax, zoom)
    SaveScreenshot(f"{out}_speed_{ax}.png", v, ImageResolution=[1600, 1150]); Delete(v)
    # temperature
    v = view(); d = Show(tc, v); ColorBy(d, ("POINTS", "T_C"))
    lut = GetColorTransferFunction("T_C"); lut.ApplyPreset("Turbo", True)
    lo, hi = tc.PointData["T_C"].GetRange(); lut.RescaleTransferFunction(lo, hi)
    bar(lut, v, d, "Air temperature [°C]", "{:.0f}")
    label(v, f"{title}: air temperature, {where}")
    camera(v, ax, zoom)
    SaveScreenshot(f"{out}_temp_{ax}.png", v, ImageResolution=[1600, 1150]); Delete(v)
    print("wrote", ax)

skin = os.path.join(src, "motor_skin.vtk")
if kind == "external" and os.path.exists(skin):
    s = LegacyVTKReader(FileNames=[skin])
    cd = CellDatatoPointData(Input=s)
    h = Calculator(Input=cd, AttributeType="Point Data", ResultArrayName="h", Function=f"abs(wallHeatFlux)/{DT}")
    v = view(); d = Show(h, v); ColorBy(d, ("POINTS", "h"))
    lut = GetColorTransferFunction("h"); lut.ApplyPreset("Turbo", True); lut.RescaleTransferFunction(0.0, 12.0)
    bar(lut, v, d, "h [W/m²K]", "{:.1f}")
    label(v, f"{title}: convective h on the motor skin (natural convection, ΔT = 60 K)")
    v.CameraPosition = (0.55, 0.35, -0.6); v.CameraFocalPoint = (0, 0, -0.01); v.CameraViewUp = (0, 1, 0)
    ResetCamera(v); v.CameraParallelScale *= 0.85
    SaveScreenshot(f"{out}_h.png", v, ImageResolution=[1600, 1150]); Delete(v)
    print("wrote h")
