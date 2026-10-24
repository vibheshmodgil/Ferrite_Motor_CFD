source /opt/openfoam12/etc/bashrc
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/u666_build_ctnc.sh | tail -1 | cut -c1-40
unset FOAM_SIGFPE; export NCDBG=1
cd ~/cfd/u666_etest
rm -rf processor*/10; mpirun -np 4 foamMultiRun -parallel > log.dbg 2>&1
grep NCDBG log.dbg | grep -v "nan: 00000" | head
