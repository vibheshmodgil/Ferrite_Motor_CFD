source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
pkill mpirun
ADIABATIC=1 JOULE_TC=0 $XENV python3 $S/u666_make_case.py ~/cfd/u666_base_nc ~/cfd/u666_etest etest --lp-file $S/../u666_loadpoints.json
cd ~/cfd/u666_etest
sed -i 's/^endTime .*/endTime 10;/; s/^writeInterval .*/writeInterval 10;/' system/controlDict
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors ${N:-20}/" system/fvSolution
decomposePar -allRegions > log.decompose 2>&1
mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
bash $S/_t.sh | awk '{print $1,$3}' | sed 's/\/0\/volFieldValue.dat//' | tr '\n' ' '
