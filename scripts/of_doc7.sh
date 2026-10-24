source /opt/openfoam12/etc/bashrc 2>/dev/null
cd $FOAM_TUTORIALS/fluid; ls
d=buoyantCavity; ls -R $d | head -30
for f in system/fvSolution system/fvSchemes system/controlDict constant/physicalProperties constant/pRef 0/p_rgh 0/p; do echo "=== $f"; sed '1,/^}/d' $d/$f | grep -v '^\s*$\|^//' | head -60; done
grep -rl prghTotalPressure . | head -3
