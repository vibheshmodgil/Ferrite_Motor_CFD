source /opt/openfoam12/etc/bashrc; rm -rf ~/chk; mkdir -p ~/chk/system ~/chk/constant; cd ~/chk
echo 'FoamFile { format ascii; class dictionary; object controlDict; } application foamRun; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1; writeControl timeStep; writeInterval 1;' > system/controlDict
gmshToFoam $1 > /dev/null; transformPoints "scale=(1e-3 1e-3 1e-3)" >/dev/null
checkMesh 2>&1 | grep -E "cells:|Max aspect|Min volume|non-orth|severely|skew"
