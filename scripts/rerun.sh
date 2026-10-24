# rerun an existing case from 0 for N steps: bash rerun.sh <case> <endTime>
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
cd ~/cfd/$1; rm -rf postProcessing processor*/[1-9]* ; sed -i "s/^endTime .*/endTime         $2;/" system/controlDict
mpirun -np 4 foamMultiRun -parallel > log.run 2>&1; grep FATAL -A5 log.run | head
bash $(dirname $(readlink -f $0))/hist.sh $1
