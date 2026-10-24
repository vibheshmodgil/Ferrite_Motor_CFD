S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
cd ~/cfd/duty1
for p in processor*; do for d in $p/[0-9]*; do t=${d##*/}; [ $t != 0 ] && [ $((t % 60)) != 0 ] && rm -rf $d; done; done
du -sh .
rm -rf $W/duty1; mkdir -p $W/duty1; cp -r postProcessing $W/duty1/
bash $S/energy_check.sh duty1 0 420 > $W/duty1/energy_T.txt
echo ENERGY_DONE
for t in 60 120 180 240 300 360 420; do bash $S/slices.sh duty1 $t >/dev/null 2>&1; bash $S/heatpaths.sh duty1 $t >/dev/null 2>&1; done
bash $S/slices.sh duty1 420 -0.040 >/dev/null 2>&1
bash $S/export3d.sh solid duty1 420 >/dev/null 2>&1
echo D1POST_DONE
