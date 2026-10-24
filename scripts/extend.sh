# continue a finished long run to 12 h of motor time from its last write (2-minute steps)
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
C=~/cfd/$1; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
[ -f $W/$1/done ] && exit 0
cd $C || exit 1
sed -i 's/^startFrom .*/startFrom       latestTime;/; s/^endTime .*/endTime         43200;/; s/^deltaT .*/deltaT          120;/; s/^writeInterval .*/writeInterval   3600;/' system/controlDict
mpirun -np 4 foamMultiRun -parallel > log.run2 2>&1
mkdir -p $W/$1; cp -r postProcessing $W/$1/
grep -q "^[[:space:]]*End$" log.run2 && touch $W/$1/done
