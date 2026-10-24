pkill mpirun
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
ADIAB=1 python3 $S/u666_energy_balance.py ~/cfd/u666_etest etest $S/../u666_loadpoints.json 2>&1 | tail -3 | cut -c1-1200
