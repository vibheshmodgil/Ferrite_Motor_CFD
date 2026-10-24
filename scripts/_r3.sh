source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE; cd ~/cfd/u666_etest
rm -rf processor*; rm -rf postProcessing; decomposePar -allRegions > log.decompose 2>&1
(time mpirun -np 4 foamMultiRun -parallel > log.run 2>&1) 2> time.run
