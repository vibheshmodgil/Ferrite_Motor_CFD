# Design9795 duty-report visuals (run from Git Bash):  bash scripts/duty_visuals.sh ext|duty1|duty2|duty4|inair <case>|3d <case>
#   ext    external natural-convection air (shared by all duty points): animations + streamline stills
#   dutyN  temperature-rise + heat-flow animations (needs results/dutyN slices_<t>, heatflow_<t>) and the internal-air
#          animations/stills (needs results/inair_dutyN)
#   3d dutyN  3D cut-away at the last vtk3d time (needs results/vtk3d/dutyN_<t>)
# Outputs: results/anim_duty/*.mp4, results/figs_duty/*.png. Each step skips if its input is missing.
# The part outlines on the flow pictures come from results/continuous/slices_* (same mesh, geometry only).
set -x
cd /c/Users/vibhe/Downloads/OUTPUT/CFD
PY=".venv/Scripts/python -I"; PV="/c/Program Files/ParaView 6.2.0/bin/pvpython.exe"
A=results/anim_duty; F=results/figs_duty; mkdir -p $A $F
G=results/continuous/slices_18000; G40=results/continuous/slices_18000_z-0.040
declare -A NAME=([duty1]="Duty 1, grade 12.3 % @ 23 km/h, 37 N·m @ 1782 rpm" [duty2]="Duty 2, grade 17.6 % @ 16 km/h, 26.3 N·m @ 2550 rpm" [duty3]="Duty 3, grade 25 % @ 11 km/h, 20 N·m @ 3637 rpm" [duty4]="Duty 4, flat road 60 km/h, 3.24 N·m @ 9339 rpm" [duty5]="Duty 5, grade 7 % @ 30 km/h, 12.43 N·m @ 1612 rpm")
declare -A RPM=([duty1]=1782 [duty2]=2550 [duty3]=3637 [duty4]=9339 [duty5]=1612)
flow() {  # src ax tag title slow
  $PY scripts/animate_flow.py "$1" $2 $A/$3.mp4 "$4" $5 auto --solids $6
  $PY scripts/animate_flow.py "$1" $2 - "$4" $5 auto --solids $6 --still $F/$3.png
}
case $1 in
ext)
  flow results/air/air_z.vtk z ext_air_z "Air around the motor, radial mid-plane z = 5 mm" 1 $G
  flow results/air/air_x.vtk x ext_air_x "Air around the motor, axial mid-plane (rear left, drive end right)" 1 $G ;;
duty1|duty2|duty3|duty4|duty5|inair)
  c=$1; [ $1 = inair ] && c=$2   # inair <case>: only the internal-air part
  n=${NAME[$c]}
  if [ $1 != inair ]; then
    [ -n "$(ls -d results/$c/slices_* 2>/dev/null)" ] && $PY scripts/animate_temp.py $c $A/temp_$c.mp4 "$n: temperature rise" 12
    [ -n "$(ls results/$c/heatflow_*.txt 2>/dev/null)" ] && $PY scripts/animate_heat.py $c $c $A/heat_$c.mp4 "$n: heat flow" 12
  fi
  I=results/inair_$c
  if [ -f $I/inair_z.vtk ]; then
    flow $I/inair_z.vtk z inair_z_$c "Inside air, ${RPM[$c]} rpm, drive-end space z = -40 mm" 0.025 $G40
    flow $I/inair_x.vtk x inair_x_$c "Inside air, ${RPM[$c]} rpm, axial mid-plane (rear left, DE right)" 0.025 $G
  fi ;;
3d)
  c=$2; d=$(ls -d results/vtk3d/${c}_* 2>/dev/null | sort -t_ -k2 -n | tail -1)
  [ -z "$d" ] && exit 0
  args=(); [ -f results/vtk3d/inair_$c/internal.vtk ] && args=(--inair results/vtk3d/inair_$c/internal.vtk)
  "$PV" --force-offscreen-rendering scripts/render3d.py $d $F/3d_$c "${NAME[$c]} at ${d##*_} s: cut-away" "${args[@]}" --dist 0.42 --turntable 72
  $PY scripts/frames2mp4.py $A/3d_$c.mp4 20 1 0 $F/3d_${c}_frames/f*.png ;;
esac
echo DUTY_VISUALS_DONE $1 $2
