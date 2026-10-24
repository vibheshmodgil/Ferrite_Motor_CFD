#!/bin/bash
# usage: u666_slicefix.sh <case> ; fills the (empty, unit bug mm vs m) radial cut planes of a FINISHED duty case from the saved
# T fields (every 30 s). Single process, nice 19. Output lands in postProcessing/<region>/S_<plane>_<region>/<t>/<plane>.vtk.
source /opt/openfoam12/etc/bashrc; unset FOAM_SIGFPE
C=$1; cd $C || exit 1
nice -n 19 reconstructPar -allRegions -fields '(T)' -newTimes > log.slicefix_reco 2>&1
declare -A PT=([radial_stack]=0.0299 [radial_ew_front]=0.075 [radial_ew_rear]=-0.0153)
declare -A RG=([radial_stack]="housing stator winding wedge rotor magnets shaft inair" [radial_ew_front]="housing winding inair shaft endcaps" [radial_ew_rear]="housing winding inair shaft endcaps")
for p in "${!PT[@]}"; do for r in ${RG[$p]}; do
  cat > system/S_${p}_$r <<EOT
type surfaces; libs ("libsampling.so"); writeControl timeStep; writeInterval 1; log false;
surfaceFormat vtk; interpolationScheme cell; fields (T);
surfaces ( $p { type cutPlane; planeType pointAndNormal; interpolate false; point (0 0 ${PT[$p]}); normal (0 0 1); } );
EOT
  nice -n 19 foamPostProcess -func S_${p}_$r -region $r -time '1:' > log.slicefix_${p}_$r 2>&1
  rm -f system/S_${p}_$r
done; done
