L=~/cfd/air/log.run
n0=$(grep -c '^Time =' $L); t0=$(grep ExecutionTime $L | tail -1 | awk '{print $3}')
sleep 90
n1=$(grep -c '^Time =' $L); t1=$(grep ExecutionTime $L | tail -1 | awk '{print $3}')
echo "$n0 -> $n1 iterations, $t0 -> $t1 s"
