source /opt/openfoam12/etc/bashrc; unset FOAM_SIGFPE; cd ~/cfd/u666_air; rm -rf processor*/[1-9]*; foamDictionary system/controlDict -entry endTime -set 5 >/dev/null
timeout 600 mpirun -np 4 foamRun -parallel > log.t 2>&1; grep -E "^Time|p_rgh|solution" log.t | tail -12
