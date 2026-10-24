# peak-torque transient, then the external natural-convection CFD
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
cd ~; date
bash $S/run_case.sh peak_torque > ~/cfd/peak.out 2>&1; date
bash $S/air_case.sh /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/mesh/air.msh > ~/cfd/air.out 2>&1; date
cat ~/cfd/air.out
