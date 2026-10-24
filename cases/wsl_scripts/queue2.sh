S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
until grep -q "ALL DONE" ~/cfd/duty.log; do sleep 30; done
echo "=== $(date +%T) energy test (production settings)"
bash $S/energy_test.sh prod > ~/cfd/etest_prod.log 2>&1; tail -n 8 ~/cfd/etest_prod.log
for spec in duty1:420:1782 duty4:2700:9339; do
  IFS=: read c t rpm <<< "$spec"
  echo "=== $(date +%T) inair $c"
  bash $S/inair_cfd.sh $c $t $rpm > ~/cfd/inair_$c.log 2>&1
  bash $S/inair_post.sh $c > /dev/null 2>&1
  bash $S/export3d.sh fluid inair_$c > /dev/null 2>&1
  rm -rf ~/cfd/inair_$c/processor*
  df -h / | tail -n 1
done
echo "=== $(date +%T) QUEUE2 DONE"
