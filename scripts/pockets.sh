source /opt/openfoam12/etc/bashrc 2>/dev/null
C=~/cfd/pockets; rm -rf $C; mkdir -p $C/system $C/constant; cd $C
cp -r ~/cfd/inair_continuous/system/controlDict system/
cp -r ~/cfd/inair_continuous/constant/polyMesh constant/
splitMeshRegions -makeCellZones -overwrite > log.split 2>&1
grep -A20 "Number of regions" log.split | head -25
