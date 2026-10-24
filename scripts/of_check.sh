source /opt/openfoam12/etc/bashrc 2>/dev/null
echo "version: $WM_PROJECT_VERSION"; free -g | head -2
ls $FOAM_SRC/fvModels/ | head; echo ---
find $FOAM_SRC -maxdepth 4 -type d -iname "*heatSource*"; find $FOAM_SRC -maxdepth 6 -type d -iname "*coded*" | head
echo ---; find $FOAM_SRC -iname "*anisotropic*" | head
echo ---; find $FOAM_SRC -path "*coupledTemperature*" -maxdepth 8 | head -3; find $FOAM_SRC -iname "externalTemperature*" | head -3
ls $FOAM_TUTORIALS/multiRegion/CHT 2>/dev/null || ls $FOAM_TUTORIALS | head -30
