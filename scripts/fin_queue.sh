# fin study queue (tmux "finq"): wait for the eps-0.1 duty4 baseline, full post -> results/duty4_eps01, then the
# one fin variant (tapered rings H16 p11.5)
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
until grep -q "done\|FAILED" ~/cfd/fin_baseline.log 2>/dev/null; do sleep 60; done
C=fin_baseline_eps0.1_duty4
echo "=== $(date '+%F %T') post $C -> results/duty4_eps01"
for t in 420 840 1260 1680; do bash $S/slices.sh $C $t > /dev/null 2>&1; bash $S/heatpaths.sh $C $t > /dev/null 2>&1; done
bash $S/export3d.sh solid $C 1680 > /dev/null 2>&1
rm -rf $W/duty4_eps01; mkdir -p $W/duty4_eps01
cp -r $W/fins/baseline_eps0.1/. $W/duty4_eps01/; mv $W/$C/* $W/duty4_eps01/ && rmdir $W/$C
[ -d $W/vtk3d/${C}_1680 ] && mv $W/vtk3d/${C}_1680 $W/duty4_eps01/vtk3d_1680
echo "=== $(date '+%F %T') post done"; ls $W/duty4_eps01
AIR_SKIN=3 bash $S/fin_variant.sh ring_h16_p11.5 102 -44.25 67.5 > ~/cfd/fin_ring_h16.log 2>&1
echo QUEUE_END >> ~/cfd/fin_ring_h16.log
