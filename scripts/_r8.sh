source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
cd ~/cfd/u666_etest
for r in bearings endcaps housing inair magnets shaft stator wedge rotor winding; do sed -i 's/PBiCGStab; preconditioner DILU;/PCG; preconditioner DIC;/' system/$r/fvSolution; done
sed -i 's/^endTime .*/endTime 10;/; s/^writeInterval .*/writeInterval 10;/' system/controlDict
for N in 1 4; do
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors $N/" system/fvSolution
rm -rf postProcessing processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
echo N=$N; bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/_t.sh | awk '{print $1,$3}' | sed 's/\/0\/volFieldValue.dat//' | tr '\n' ' '
done
grep "Solving for e" log.dbg | tail -12 | cut -c1-130
