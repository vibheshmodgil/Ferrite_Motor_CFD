source /opt/openfoam12/etc/bashrc 2>/dev/null; cd ~/cfd/continuous; ls -d 18000
foamPostProcess -region winding -func "patchAverage(patch=winding_to_inair, fields=(T))" -time 18000 2>&1 | tail -8
