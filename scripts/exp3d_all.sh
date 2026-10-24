S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
bash $S/export3d.sh solid peak_torque 200
bash $S/export3d.sh solid continuous 18000
bash $S/export3d.sh fluid air
for t in 50 100 150 250; do bash $S/export3d.sh solid peak_torque $t; done
echo EXP_DONE > ~/cfd/exp3d.done
