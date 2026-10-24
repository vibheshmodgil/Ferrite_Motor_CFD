# Time-step convergence check: continue the continuous case from 5 h for 30 min of motor time with
# different time steps / coupling iterations and compare the winding hot spot at 5.5 h.
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
for spec in "dt60_c1 60 1" "dt30_c3 30 3" "dt120_c3 120 3"; do
  set -- $spec; C=~/cfd/dtcheck_$1
  [ -f $C/done ] && continue
  rm -rf $C; mkdir -p $C; cd ~/cfd/continuous
  cp -r constant system 0 $C/ 2>/dev/null
  for p in processor*; do mkdir -p $C/$p; cp -r $p/constant $p/18000 $C/$p/; done
  cp -r dynamicCode $C/ 2>/dev/null
  cd $C
  sed -i 's/^startFrom .*/startFrom       latestTime;/; s/^endTime .*/endTime         19800;/; s/^deltaT .*/deltaT          '$2';/; s/^writeInterval .*/writeInterval   1800;/' system/controlDict
  sed -i 's/nOuterCorrectors [0-9]*;/nOuterCorrectors '$3';/' system/fvSolution
  mpirun -np 4 foamMultiRun -parallel > log.run 2>&1 && touch done
  echo "$1: $(tail -1 postProcessing/winding/T_winding/18000/volFieldValue.dat)"
done
echo DTCHECK_DONE
