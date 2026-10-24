# S8c: assemble + checkMesh + adiabatic duty1 energy test via _e2.sh (env DT N END ASM)
ASM=${ASM:-1} DT=${DT:-1} N=${N:-3} END=${END:-60} bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/_e2.sh > /home/cfd/cfd/log.e2 2>&1
echo EXIT $? >> /home/cfd/cfd/log.e2
