# Everything still to compute, strictly one heavy job at a time. Start detached:
#   nohup bash pipeline.sh > ~/cfd/pipeline.log 2>&1 &
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
step() { echo "=== $(date '+%F %T') $*"; }

step "1. external natural-convection CFD (closed box, walls at ambient)"
if [ ! -f ~/cfd/h_cfd.json ]; then          # done once: h mean 4.02 W/m2K, U max 0.56 m/s
  bash $S/air_case.sh /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/mesh/air.msh
  bash $S/aircheck.sh || { step "AIR CFD NOT PHYSICAL - stopping"; exit 1; }
fi

step "2. baseline: CFD h -> continuous, peak_power, cruise, max_speed"
bash $S/extend.sh continuous          # first 5 h already computed; continue it to 12 h
bash $S/stage2.sh || { step "STAGE 2 STOPPED"; exit 1; }

step "3. baseline section planes at the end of each long run"
# sections + heat paths at the limit time (nearest write) and at 12 h; peak torque at 200 s (just past its limit)
for spec in "peak_torque 200" "continuous 18000" "continuous 43200" "peak_power 36000" "peak_power 43200"             "cruise 43200" "max_speed 43200"; do
  set -- $spec
  [ -d $W/$1/slices_$2 ] || bash $S/slices.sh $1 $2 > /dev/null 2>&1
  [ -f $W/$1/heatflow_$2.txt ] || bash $S/heatpaths.sh $1 $2 > /dev/null 2>&1
done

step "3b. internal air CFD (rotor-driven end-space flow) at the continuous point"
[ -f $W/inair_continuous/wall_q.txt ] || bash $S/inair_cfd.sh continuous 18000 3000
mkdir -p $W/air && cp -r ~/cfd/air/postProcessing $W/air/ 2>/dev/null

step "4. detailed geometry + mesh (real coils, bobbins, resin, busbars)"
mkdir -p ~/cfd/mesh
[ -f ~/cfd/mesh/motor_detailed.msh ] || CAD=/mnt/c/Users/vibhe/Downloads/OUTPUT/OUTPUT/cad/motor_65 OUT=~/cfd/mesh \
  ~/venv/bin/python -I $S/build_mesh_detailed.py > ~/cfd/mesh/detailed.log 2>&1
grep -aE "pieces|tets|Error|Traceback" ~/cfd/mesh/detailed.log | tail -20
[ -f ~/cfd/mesh/motor_detailed.msh ] || { step "MESH FAILED"; exit 1; }
cp ~/cfd/mesh/motor_detailed_regions.json $W/ 2>/dev/null

step "5. detailed base case"
[ -d ~/cfd/base_detailed/constant/coil ] || bash $S/prep_base.sh ~/cfd/mesh/motor_detailed.msh ~/cfd/base_detailed | tail -20

step "6. detailed runs"
for lp in peak_torque continuous peak_power max_speed cruise; do
  step "   detailed $lp"
  [ -f $W/detailed/$lp/done ] && { step "   $lp already done"; continue; }
  BASE=~/cfd/base_detailed PREFIX=det_ HFILE=~/cfd/h_cfd.json bash $S/run_case.sh $lp
  mkdir -p $W/detailed/$lp; cp -r ~/cfd/det_$lp/postProcessing $W/detailed/$lp/
  grep -q "^[[:space:]]*End$" ~/cfd/det_$lp/log.run && touch $W/detailed/$lp/done
done
step "ALL DONE"
