"""3D cut-away of the motor (quarter removed) coloured by temperature, with 3D air streamlines outside and inside.

    pvpython render3d.py <solid_dir> <out_prefix> "<title>" [--air ext.vtk] [--inair int.vtk] [--turntable N] [--range lo hi]

Solids and air share one temperature colour scale, so heat leaving the parts into the air is visible.
Writes <out_prefix>.png and, with --turntable N, N frames <out_prefix>_frames/f####.png for a rotating video.
"""
import glob, math, os, sys
from paraview.simple import *

args = sys.argv[1:]
opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d
src, out, title = args[0], args[1], args[2]
AIR, INAIR = opt("--air"), opt("--inair")
NTURN = int(opt("--turntable", "0"))
rng = [float(args[args.index("--range") + 1]), float(args[args.index("--range") + 2])] if "--range" in args else None

v = CreateRenderView(); v.ViewSize = [1600, 1100]; v.OrientationAxesVisibility = 0
v.Background = [1, 1, 1]; v.UseColorPaletteForBackground = 0
lut = GetColorTransferFunction("T_C"); lut.ApplyPreset("Turbo", True)

solids = [LegacyVTKReader(FileNames=[f]) for f in sorted(glob.glob(os.path.join(src, "*.vtk")))]
allsol = AppendDatasets(Input=solids)
cd = CellDatatoPointData(Input=allsol)
tc = Calculator(Input=cd, AttributeType="Point Data", ResultArrayName="T_C", Function="T-273.15")
# remove the quarter x > 0, y > 0 (upper front quadrant, seen from the camera)
clip = Clip(Input=tc); clip.ClipType = "Box"; clip.Crinkleclip = 0
clip.ClipType.Position = [0.0, 0.0, -0.3]; clip.ClipType.Length = [0.3, 0.3, 0.6]
try:
    clip.Invert = 0
except AttributeError:
    pass
d = Show(clip, v); ColorBy(d, ("POINTS", "T_C")); d.Specular = 0.3
lo, hi = rng or tc.PointData["T_C"].GetRange()
lut.RescaleTransferFunction(lo, hi); lut.AutomaticRescaleRangeMode = "Never"


def streamlines(path, centre, radius, n, tube, opacity=1.0, length=2.0):
    r = LegacyVTKReader(FileNames=[path])
    p = CellDatatoPointData(Input=r)
    c = Calculator(Input=p, AttributeType="Point Data", ResultArrayName="T_C", Function="T-273.15")
    st = StreamTracer(Input=c, SeedType="Point Cloud"); st.Vectors = ["POINTS", "U"]
    st.SeedType.Center = centre; st.SeedType.Radius = radius; st.SeedType.NumberOfPoints = n
    st.MaximumStreamlineLength = length; st.IntegrationDirection = "BOTH"
    tb = Tube(Input=st); tb.Radius = tube; tb.NumberofSides = 8
    sd = Show(tb, v); ColorBy(sd, ("POINTS", "T_C")); sd.Opacity = opacity
    lut.RescaleTransferFunction(lo, hi); return sd


if AIR and os.path.exists(AIR):
    streamlines(AIR, [0.0, -0.03, -0.02], 0.12, 90, 0.0008, opacity=0.6, length=0.6)
if INAIR and os.path.exists(INAIR):
    streamlines(INAIR, [0.0, 0.0, -0.045], 0.07, 260, 0.0005, length=1.5)
    streamlines(INAIR, [0.0, 0.0, 0.055], 0.07, 260, 0.0005, length=1.5)

bar = GetScalarBar(lut, v); bar.Title = "Temperature [°C]"; bar.ComponentTitle = ""
bar.TitleColor = bar.LabelColor = [0.1, 0.1, 0.1]; bar.TitleFontSize = 20; bar.LabelFontSize = 18
bar.WindowLocation = "Any Location"; bar.Position = [0.89, 0.15]; bar.ScalarBarLength = 0.7
bar.AutomaticLabelFormat = 0; bar.LabelFormat = "{:.0f}"; bar.RangeLabelFormat = "{:.0f}"
d.SetScalarBarVisibility(v, True)
t = Show(Text(Text=title), v); t.Color = [0.1, 0.1, 0.1]; t.FontSize = 22; t.WindowLocation = "Upper Left Corner"

v.CameraFocalPoint = [0.0, 0.0, 0.0]; v.CameraViewUp = [0, 1, 0]
R = float(opt("--dist", "0.55")); EL = 0.32
def place(az):
    a = math.radians(az)
    v.CameraPosition = [R * math.sin(a), R * EL, R * math.cos(a)]
place(38); v.CameraViewAngle = 30
dist = R * math.sqrt(1 + EL * EL)
SaveScreenshot(out + ".png", v, ImageResolution=[1600, 1100]); print("wrote", out + ".png")
if NTURN:
    fd = out + "_frames"; os.makedirs(fd, exist_ok=True)
    for i in range(NTURN):
        az = 38 + 360.0 * i / NTURN; a = math.radians(az)
        v.CameraPosition = [dist * math.sin(a) * math.cos(math.radians(18)), dist * math.sin(math.radians(18)), dist * math.cos(a) * math.cos(math.radians(18))]
        Render(v); SaveScreenshot(os.path.join(fd, f"f{i:04d}.png"), v, ImageResolution=[1280, 880])
    print("wrote", NTURN, "frames")
