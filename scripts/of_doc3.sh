source /opt/openfoam12/etc/bashrc 2>/dev/null
S=$FOAM_SRC
awk '/^Description/,/^SourceFiles/' $S/fvModels/general/codedFvModel/codedFvModel.H | head -70
grep -n "addSup\|eqn\|he()" $S/fvModels/general/heatSource/heatSource.C | head -20
ls $FOAM_APP/modules/solid/; grep -n "thermo.he\|heEqn\|fvModels" $FOAM_APP/modules/solid/thermophysicalPredictor.C | head
grep -rn "codeAddSup" $FOAM_TUTORIALS --include=fvModels -l 2>/dev/null | head -3
