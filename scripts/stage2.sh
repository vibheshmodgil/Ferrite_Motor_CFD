# h from the air CFD -> the 4 long load points -> copy monitor histories to Windows results/
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
cd ~/cfd/air; T=$(foamListTimes -latestTime | tail -1)
foamPostProcess -func writeCellCentres -time $T > log.cc 2>&1
cd ~/cfd/base_solids
for r in housing shaft; do foamPostProcess -region $r -func writeCellCentres -time 0 > log.cc_$r 2>&1; done
python3 $S/map_h.py ~/cfd/air $T ~/cfd/base_solids ~/cfd/h_cfd.json || exit 1
# guard: natural convection on a finned housing at dT 60 K is a few W/m2K (Churchill-Chu ~5.4 on the envelope)
python3 -c "import json,statistics as s; h=s.mean(json.load(open('$HOME/cfd/h_cfd.json'))['housing']['defaultFaces']); print('mean housing h',round(h,2)); exit(0 if 2<h<12 else 1)" || { echo 'h OUT OF PHYSICAL RANGE - stopping'; exit 1; }
mkdir -p $W; cp ~/cfd/h_cfd.json $W/
for lp in ${@:-continuous peak_power cruise max_speed}; do
  [ -f $W/$lp/done ] && { echo "== $lp already done"; continue; }
  date; echo "== $lp"
  HFILE=~/cfd/h_cfd.json bash $S/run_case.sh $lp
  rm -rf $W/$lp; mkdir -p $W/$lp; cp -r ~/cfd/$lp/postProcessing $W/$lp/
  grep -q "^[[:space:]]*End$" ~/cfd/$lp/log.run && touch $W/$lp/done
done
date
