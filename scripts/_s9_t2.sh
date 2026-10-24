source /opt/openfoam12/etc/bashrc; cd ~/cfd/u666_air; pkill -x foamRun
rm -rf processor*/[1-9]* [1-9]*; sed -i "s/maxDeltaT 5;/maxDeltaT ${MDT:-0.02};/" system/fvSolution
foamDictionary system/controlDict -entry endTime -set ${END:-60} > /dev/null; foamDictionary system/controlDict -entry writeInterval -set 20 > /dev/null
mpirun -np 4 foamRun -parallel > log.t2 2>&1; reconstructPar -latestTime > /dev/null 2>&1
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/u666_aircheck.sh 2>&1 | tail -1; grep -c "^Time" log.t2
