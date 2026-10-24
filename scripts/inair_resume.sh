source /opt/openfoam12/etc/bashrc 2>/dev/null || true
cd ~/cfd/inair_continuous
ls processor0 | grep -E '^[0-9]+$' | sort -n | tail -2
reconstructPar -latestTime > log.rec_resume 2>&1
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/inair_post.sh        # results from the latest saved state now
echo POST_DONE
mpirun -np 4 foamRun -parallel > log.run3 2>&1                            # continue to 2000 (startFrom latestTime)
reconstructPar -latestTime > log.rec_final 2>&1
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/inair_post.sh
echo INAIR_FINAL_DONE
