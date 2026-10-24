source /opt/openfoam12/etc/bashrc 2>/dev/null || source ~/.bashrc
mkdir -p ~/rep && cd ~/rep && rm -rf geo && mkdir geo && cd geo
cp -r ~/cfd/u666_base_nc/constant ~/cfd/u666_base_nc/system . 
ls system; ls constant/rotor/polyMesh | head
for r in winding stator rotor magnets wedge housing inair endcaps shaft bearings; do
 nice -n 19 foamToVTK -region $r -ascii -noZero -time 0 -fields '()' > log.$r 2>&1; tail -2 log.$r
done
ls VTK
