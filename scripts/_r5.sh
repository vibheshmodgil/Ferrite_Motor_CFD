source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
cd ~/cfd/u666_etest
pkill mpirun; sleep 2
sed -i 's/tolerance 1e-7;/tolerance 1e-7; maxIter 3;/' system/*/fvSolution
sed -i 's/^endTime .*/endTime 10;/; s/^writeInterval .*/writeInterval 10;/' system/controlDict
rm -rf processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
for r in inair endcaps housing rotor; do echo $r; grep -c nan processor*/10/$r/T; done
