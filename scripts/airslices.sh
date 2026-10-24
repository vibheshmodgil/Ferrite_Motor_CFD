# external air CFD: U and T on the radial (z = 5 mm) and axial (x = 0) mid-planes -> results/air/air_{z,x}.vtk
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
cd ~/cfd/air; LT=$(foamListTimes -latestTime | tail -1); W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/air; mkdir -p $W
for ax in z x; do
  n=$([ $ax = z ] && echo "(0 0 1)" || echo "(1 0 0)"); p=$([ $ax = z ] && echo "(0 0 0.005)" || echo "(0 0 0)")
  rm -rf postProcessing/cutPlaneSurface*
  foamPostProcess -solver fluid -func "cutPlaneSurface(point=$p, normal=$n, U, T)" -time $LT > /dev/null 2>&1
  f=$(find postProcessing -path "*cutPlaneSurface*" -name "*.vtk" | head -1); [ -n "$f" ] && cp "$f" $W/air_$ax.vtk
done
bash $(dirname $(readlink -f $0))/skin.sh > /dev/null 2>&1
f=$(find postProcessing -path "*patchSurface*" -name "*.vtk" | head -1); [ -n "$f" ] && cp "$f" $W/motor_skin.vtk
ls $W
