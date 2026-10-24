source /opt/openfoam12/etc/bashrc 2>/dev/null
cd $FOAM_TUTORIALS
grep -rl "anisotropic" --include=* . | head
f=$(grep -rl "model *anisotropic" . | head -1); echo "== $f"; cat $f | sed -n 8,80p
d=$(dirname $f); ls $d; cat $d/physicalProperties 2>/dev/null | sed -n 8,60p
echo; ls multiRegion/CHT/heatExchanger multiRegion/CHT/circuitBoardCooling 2>/dev/null
ls -R multiRegion/CHT/coolingSphere | head -50
