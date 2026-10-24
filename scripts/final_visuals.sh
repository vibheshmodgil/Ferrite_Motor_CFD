# Everything visual that needs the final internal-air CFD (run from Git Bash in the CFD folder)
set -x
cd /c/Users/vibhe/Downloads/OUTPUT/CFD
PY=.venv/Scripts/python; PV="/c/Program Files/ParaView 6.2.0/bin/pvpython.exe"
S18=results/continuous/slices_18000; S40=results/continuous/slices_18000_z-0.040
# 1. flow pictures (streamlines) + animations with the solid parts drawn and labelled
$PY -I scripts/animate_flow.py results/air/air_z.vtk z results/anim/air_z.mp4 "Air around motor_65, radial mid-plane (z = 5 mm)" 1 0.45 --solids $S18
$PY -I scripts/animate_flow.py results/air/air_x.vtk x results/anim/air_x.mp4 "Air around motor_65, axial mid-plane (rear left, drive end right)" 1 0.45 --solids $S18
$PY -I scripts/animate_flow.py results/air/air_z.vtk z - "Air around motor_65, radial mid-plane (z = 5 mm)" 1 0.45 --solids $S18 --still results/figs/flow_ext_z.png
$PY -I scripts/animate_flow.py results/air/air_x.vtk x - "Air around motor_65, axial mid-plane (rear left, drive end right)" 1 0.45 --solids $S18 --still results/figs/flow_ext_x.png
$PY -I scripts/animate_flow.py results/inair_continuous/inair_z.vtk z results/anim/inair_z.mp4 "Air inside motor_65 at 3000 rpm: drive-end space, radial plane z = -40 mm" 0.025 --solids $S40
$PY -I scripts/animate_flow.py results/inair_continuous/inair_x.vtk x results/anim/inair_x.mp4 "Air inside motor_65 at 3000 rpm: axial mid-plane (rear left, drive end right)" 0.025 --solids $S18
$PY -I scripts/animate_flow.py results/inair_continuous/inair_z.vtk z - "Air inside motor_65 at 3000 rpm: drive-end space, radial plane z = -40 mm" 0.025 --solids $S40 --still results/figs/flow_int_z.png
$PY -I scripts/animate_flow.py results/inair_continuous/inair_x.vtk x - "Air inside motor_65 at 3000 rpm: axial mid-plane (rear left, drive end right)" 0.025 --solids $S18 --still results/figs/flow_int_x.png
# 2. 3D: continuous cut-away with outside plume + inside swirl, still + turntable
INAIR=results/vtk3d/inair_continuous/internal.vtk
"$PV" --force-offscreen-rendering scripts/render3d.py results/vtk3d/continuous_18000 results/figs/3d_continuous_inside "Continuous 24 N·m @ 3000 rpm at 5 h: inside the motor — parts (quarter cut away) and the end-space air swirl" --inair $INAIR --range 85 135 --dist 0.42 --turntable 72
"$PV" --force-offscreen-rendering scripts/render3d.py results/vtk3d/continuous_18000 results/figs/3d_continuous_ext "Continuous 24 N·m @ 3000 rpm at 5 h: motor (quarter cut away) and the air plume around it" --air results/vtk3d/air/internal.vtk --range 40 135 --dist 1.0
$PY -I scripts/frames2mp4.py results/anim/3d_turntable.mp4 20 1 0 results/figs/3d_continuous_inside_frames/f*.png
$PY -I scripts/make_report.py
echo FINAL_VISUALS_DONE
