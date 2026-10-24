#!/bin/bash
# low-priority single-thread render. usage: u666_report_render.sh geo | duty <duty> ...
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD; O=$S/results/u666/report; mkdir -p $O
export OMP_NUM_THREADS=1 PYTHONPATH=$S/scripts
if [ "$1" = geo ]; then
  [ -f $O/geo/radial_mesh.png ] && [ "$2" != force ] && { echo geo cached; exit 0; }
  source /opt/openfoam12/etc/bashrc; W=~/rep/geo; mkdir -p $W; cd $W
  cp -r ~/cfd/u666_base_nc/constant ~/cfd/u666_base_nc/system . 2>/dev/null
  for r in winding stator rotor magnets wedge housing inair endcaps shaft bearings; do [ -f VTK/$r/geo_0.vtk ] || nice -n 19 foamToVTK -region $r -ascii -noZero -time 0 -fields '()' >/dev/null 2>&1; done
  nice -n 19 python3 $S/scripts/u666_report_render.py geo $W/VTK $O/geo
elif [ "$1" = extra ]; then
  # mesh per-region, housing CAD overlay, air planes, h map (each cached by its output file)
  source /opt/openfoam12/etc/bashrc; W=~/rep/geo; N="nice -n 19 python3 $S/scripts/u666_report_render.py"
  [ -f $O/geo/regions_radial.png ] && [ -f $O/geo/regions_axial.png ] || $N regions $W/VTK $O/geo
  [ -f $O/geo/housing_overlay.png ] || $N overlay $W/VTK $S/mesh/u666/stl/housing.stl $O/geo
  if [ ! -f $O/air/air_T.png ] && [ -f ~/cfd/u666_air/450/T ]; then
    A=~/rep/air; mkdir -p $A; cd $A; ln -sfn ~/cfd/u666_air/constant constant; ln -sfn ~/cfd/u666_air/system system; ln -sfn ~/cfd/u666_air/450 450
    ls $A/VTK/*450.vtk >/dev/null 2>&1 || nice -n 19 foamToVTK -time 450 -noZero -fields '(T U)' > log.vtk 2>&1
    F=$(ls $A/VTK/*450.vtk 2>/dev/null | head -1); [ -n "$F" ] && $N air $F $O/air
  fi
  [ -f $O/air/h_3d.png ] || $N hmap $W/VTK ~/cfd/u666_air_h.json ~/cfd/u666_air_h.json.h0bak $O/air
else
  nice -n 19 python3 $S/scripts/u666_report_render.py "$@"
fi
