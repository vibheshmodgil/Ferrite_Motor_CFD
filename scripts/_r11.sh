source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
cd ~/cfd/u666_etest

rm -rf postProcessing processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
bash $S/_t.sh | awk '{print $1,$3}' | sed 's/\/0\/volFieldValue.dat//' | tr '\n' ' '
