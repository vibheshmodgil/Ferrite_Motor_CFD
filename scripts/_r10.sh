source /opt/openfoam12/etc/bashrc
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/u666_build_ctnc.sh | tail -1 | cut -c1-30
unset FOAM_SIGFPE; export NCDBG2=1
cd ~/cfd/u666_etest
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors 1/" system/fvSolution
rm -rf postProcessing processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
grep "^\[0\] NCDBG2 rotor" log.dbg | head -12
