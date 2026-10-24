# wait for stage1 (peak + air CFD) to finish, then copy peak results and run stage2
until [ -f ~/cfd/air/log.reconstruct ] && ! pgrep -f "foamRun|foamMultiRun" >/dev/null; do sleep 30; done
W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results

bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/stage2.sh > ~/cfd/stage2.out 2>&1
echo STAGE2_DONE >> ~/cfd/stage2.out
