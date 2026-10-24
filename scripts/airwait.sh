L=~/cfd/air/log.run
until [ -f $L ] && { [ "$(grep -c '^Time =' $L)" -ge 60 ] || grep -q "FATAL\|exception" $L; }; do sleep 10; done
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/airpeek.sh; grep ExecutionTime $L | tail -1
