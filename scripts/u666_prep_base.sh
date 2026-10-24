# U666: gmsh mesh (or a snappy case dir) -> split multi-region OpenFOAM base case.   bash u666_prep_base.sh <msh> <base_dir>
# Same as prep_base.sh; cellZones slot+endw -> region winding, bearing_f+bearing_r -> bearings, rotor+rpocket -> rotor
# (the zones are kept inside the regions).
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
MSH=$1; B=$2; S=$(dirname $(readlink -f $0))
rm -rf $B; mkdir -p $B/system $B/0
cat > $B/system/controlDict <<CD
FoamFile { format ascii; class dictionary; object controlDict; }
application foamMultiRun; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 8; timeFormat general;
CD
cd $B
if [ -d $MSH ]; then   # snappy case (u666_snappy.sh): polyMesh already in m, outside patch = defaultFaces
  mkdir -p constant && cp -r $MSH/constant/polyMesh constant/
else
  gmshToFoam $MSH > log.gmshToFoam 2>&1
  transformPoints "scale=(1e-3 1e-3 1e-3)" > log.transform 2>&1
fi
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Max non-orth|skewness|Mesh OK|Failed|\*\*\*" log.checkMesh
Z=constant/polyMesh
python3 $S/merge_zones.py $Z/cellZones $Z/cz1 winding slot endw
python3 $S/merge_zones.py $Z/cz1 $Z/cz0 bearings bearing_f bearing_r
if grep -q seal $Z/cellZones; then python3 $S/merge_zones.py $Z/cz0 $Z/cz2 wedge wedge seal; else mv $Z/cz0 $Z/cz2; fi   # shaft seal: polymer = wedge material
if grep -q rpocket $Z/cellZones; then python3 $S/merge_zones.py $Z/cz2 $Z/cellZonesSplit rotor rotor rpocket; else mv $Z/cz2 $Z/cellZonesSplit; fi
rm -f $Z/cz0 $Z/cz1 $Z/cz2
splitMeshRegions -cellZonesFileOnly cellZonesSplit -overwrite > log.split 2>&1
ls constant
for r in $(ls constant); do [ -d constant/$r/polyMesh ] && echo "$r: $(grep -oE '^\s{4}\w+' constant/$r/polyMesh/boundary | tr -d ' ' | tr '\n' ' ')"; done
