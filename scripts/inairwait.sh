f=/home/cfd/cfd/inair_continuous/log.run
until grep -q "kept main pocket" ~/cfd/inair.log 2>/dev/null; do sleep 10; done
grep "kept main pocket" ~/cfd/inair.log
for i in $(seq 1 60); do
  [ -f $f ] && { [ "$(grep -c '^Time =' $f)" -ge 15 ] && break; grep -q 'sigHandler\|FATAL' $f && break; }
  sleep 15
done
grep -c '^Time =' $f; grep -m1 -A3 'FATAL\|sigHandler' $f | head -4
grep 'continuity' $f | tail -1; grep 'Solving for p_rgh' $f | tail -1 | cut -c1-100; grep ExecutionTime $f | tail -1
