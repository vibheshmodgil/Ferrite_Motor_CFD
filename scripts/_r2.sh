source /opt/openfoam12/etc/bashrc
export FOAM_SIGFPE=false; cd ~/cfd/u666_etest
sed -i 's/^endTime .*/endTime 60;/; s/^writeInterval .*/writeInterval 60;/' system/controlDict
(time decomposePar -allRegions > log.decompose 2>&1) 2> time.decompose
(time mpirun -np 4 foamMultiRun -parallel > log.run 2>&1) 2> time.run
