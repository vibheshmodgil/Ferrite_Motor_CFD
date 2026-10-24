source /opt/openfoam12/etc/bashrc 2>/dev/null
cd $FOAM_TUTORIALS/multiRegion/CHT/coolingCylinder2D; find . -type f | sort | tr '\n' ' '; echo
for f in system/controlDict constant/solid/physicalProperties constant/solid/thermophysicalTransport system/solid/fvSolution system/solid/fvSchemes 0/solid/T 0/solid/p; do echo "=== $f"; sed -n '/^FoamFile/,/^}/d;/^\s*$/d;/^\/\//d;p' $f 2>/dev/null | head -60; done
echo "=== fluid T/U/p_rgh (heads)"; for f in 0/fluid/T 0/fluid/U 0/fluid/p_rgh 0/fluid/p constant/fluid/physicalProperties constant/fluid/momentumTransport constant/g system/fluid/fvSolution system/fluid/fvSchemes; do echo "--- $f"; sed -n '/^FoamFile/,/^}/d;/^\s*$/d;/^\/\//d;p' $f 2>/dev/null | head -70; done
