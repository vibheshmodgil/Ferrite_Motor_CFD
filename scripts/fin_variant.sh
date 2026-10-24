# One housing-fin variant end to end, one heavy job at a time (start inside tmux):
#   bash fin_variant.sh <name> <R_tip_mm> <z0_mm> <z1_mm>      (finned span for the envelope emissivity)
# housing STEP (make_housing_fins.py) -> solid + air meshes -> base case -> external-air CFD -> h + envelope eps
# -> duty4 to 1680 s (fin_run.sh) -> results/fins/<name>/
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
v=$1; RT=$2; Z0=$3; Z1=$4
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; M=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/mesh; F=$M/fins/$v
step() { echo "=== $(date '+%F %T') $v $*"; }
export AIR_SKIN=${AIR_SKIN:-3} CAD=/mnt/c/Users/vibhe/Downloads/OUTPUT/OUTPUT/cad/motor_65 HOUSING_STEP=$F/housing.step MESH_TAG=_$v NTHREADS=3
for kind in solids air; do
  out=$M/$([ $kind = solids ] && echo motor_solids || echo air)_$v.msh
  [ -f $out ] && continue
  step "mesh $kind"
  nice ~/venv/bin/python -I $S/build_mesh.py --$kind-only > $F/mesh_$kind.log 2>&1
  grep -E "pieces|tets:" $F/mesh_$kind.log | tail -12
done
step "base case"
B=~/cfd/base_fin_$v
[ -d $B/constant/housing ] || bash $S/prep_base.sh $M/motor_solids_$v.msh $B
(cd $B && for r in housing shaft; do foamPostProcess -region $r -func writeCellCentres -time 0 > log.cc_$r 2>&1; done)
step "external-air CFD"
A=~/cfd/air_$v
if [ ! -d $A/3000 ]; then AIRC=$A bash $S/air_case.sh $M/air_$v.msh; fi
AIRC=$A bash $S/aircheck.sh || { step "AIR CFD NOT PHYSICAL - stopping"; exit 1; }
(cd $A && foamPostProcess -func writeCellCentres -time 3000 > log.cc 2>&1)
python3 $S/air_h_zones.py $A 3000 | tail -1 | tee $F/air_hA.txt
python3 $S/map_h.py $A 3000 $B ~/cfd/h_fin_$v.json
python3 $S/fin_eps.py $B ~/cfd/h_fin_$v.json ~/cfd/h_fin_${v}_eps.json $RT $Z0 $Z1
mkdir -p /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/fins/$v
cp ~/cfd/h_fin_${v}_eps.json /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/fins/h_fin_${v}_eps.json
step "duty4"
bash $S/fin_run.sh $v $B ~/cfd/h_fin_${v}_eps.json
step "ALL DONE"
