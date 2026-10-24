# gmsh mesh -> split multi-region OpenFOAM base case.   bash prep_base.sh <msh> <base_dir>
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
MSH=$1; B=$2; S=$(dirname $(readlink -f $0))
rm -rf $B; mkdir -p $B/system $B/0
cat > $B/system/controlDict <<CD
FoamFile { format ascii; class dictionary; object controlDict; }
application foamMultiRun; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 8; timeFormat general;
CD
cp $S/../../OUTPUT/cad/motor_65/instances.json $B/ 2>/dev/null || true
cd $B
gmshToFoam $MSH > log.gmshToFoam 2>&1
transformPoints "scale=(1e-3 1e-3 1e-3)" > log.transform 2>&1
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Max non-orth|skewness|Mesh OK|Failed" log.checkMesh
if [ -n "$MERGE_CU" ]; then  # one copper region; coil/strap/busbar/tbar stay as cellZones inside it
  python3 $S/merge_zones.py constant/polyMesh/cellZones constant/polyMesh/cellZonesSplit copper coil strap busbar tbar
  splitMeshRegions -cellZonesFileOnly cellZonesSplit -overwrite > log.split 2>&1
else
  splitMeshRegions -cellZonesOnly -overwrite > log.split 2>&1
fi
ls constant
for r in $(ls constant); do [ -d constant/$r/polyMesh ] && echo "$r: $(grep -oE '^\s{4}\w+' constant/$r/polyMesh/boundary | tr -d ' ' | tr '\n' ' ')"; done
