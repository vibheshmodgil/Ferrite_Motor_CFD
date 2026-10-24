S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
source /opt/openfoam12/etc/bashrc
ADIABATIC=1 JOULE_TC=0 python3 $S/u666_make_case.py ~/cfd/u666_base_nc ~/cfd/u666_etest etest --lp-file $S/../u666_loadpoints.json
cd ~/cfd/u666_etest; sed -i 's/^endTime .*/endTime 30;/; s/^writeInterval .*/writeInterval 30;/' system/controlDict
unset FOAM_SIGFPE
decomposePar -allRegions > log.decompose 2>&1
rm -f log.run; (time mpirun -np 4 foamMultiRun -parallel > log.run 2>&1) 2> time.run
