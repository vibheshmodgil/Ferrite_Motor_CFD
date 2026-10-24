source /opt/openfoam12/etc/bashrc 2>/dev/null
sed -n '/^Description/,/^SourceFiles/p' $FOAM_SRC/thermophysicalModels/solidThermo/constAnisoSolidThermo/constAnisoSolidThermo.H | head -50
