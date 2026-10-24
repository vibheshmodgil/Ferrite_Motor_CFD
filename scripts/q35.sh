# duty3 then duty5 baseline (rest of queue3.sh)
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
export NP=3
WRITE=300 bash $S/duty_runs.sh duty3:2700:$(seq -s: 300 300 2700) > ~/cfd/duty3.log 2>&1
WRITE=450 bash $S/duty_runs.sh duty5:4050:$(seq -s: 450 450 4050) > ~/cfd/duty5.log 2>&1
