source /opt/openfoam12/etc/bashrc
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
ADIABATIC=1 JOULE_TC=0 ROTOR_ISO=28 python3 $S/u666_make_case.py ~/cfd/u666_base_nc ~/cfd/u666_etest etest --lp-file $S/../u666_loadpoints.json
unset FOAM_SIGFPE
cd ~/cfd/u666_etest
sed -i 's/^endTime .*/endTime 10;/; s/^writeInterval .*/writeInterval 10;/' system/controlDict
decomposePar -allRegions > log.decompose 2>&1
for N in 1 4; do
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors $N/" system/fvSolution
rm -rf postProcessing processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
echo N=$N; bash $S/_t.sh | awk '{print $1,$3}' | sed 's/\/0\/volFieldValue.dat//' | tr '\n' ' '
done
grep "Solving for e" log.dbg | tail -20 | cut -c1-130
