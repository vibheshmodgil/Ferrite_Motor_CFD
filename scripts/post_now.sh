S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
for spec in "peak_torque 200" "continuous 18000" "continuous 43200" "peak_power 36000" "peak_power 43200"; do
  set -- $spec
  [ -d $W/$1/slices_$2 ] || bash $S/slices.sh $1 $2 > /dev/null 2>&1
  [ -f $W/$1/heatflow_$2.txt ] || bash $S/heatpaths.sh $1 $2 > /dev/null 2>&1
  echo "done $1 $2"
done
echo POST_NOW_DONE
