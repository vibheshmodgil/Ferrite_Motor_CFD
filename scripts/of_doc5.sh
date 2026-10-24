source /opt/openfoam12/etc/bashrc 2>/dev/null
ls $FOAM_SRC/thermophysicalModels/solidThermo/ $FOAM_SRC/thermophysicalModels/solidThermo/solidThermo
grep -rn "AnIso\|anisotropic" $FOAM_SRC/thermophysicalModels/solidThermo --include=*.H | head
awk '/^Description/,/^SourceFiles/' $FOAM_SRC/thermophysicalModels/solidThermo/solidThermo/constSolidThermo.H | head -60
grep -n "lookup\|subDict\|readIfPresent\|\"" $FOAM_SRC/ThermophysicalTransportModels/solid/anisotropic/anisotropic.C | head -30
which gcc g++ wmake
