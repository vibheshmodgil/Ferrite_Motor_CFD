for p in $(pgrep -f "pipeline.sh|air_case.sh|stage2.sh|run_case.sh"); do kill $p 2>/dev/null; done
for p in $(pgrep -f "foamRun|foamMultiRun|mpirun"); do kill $p 2>/dev/null; done
sleep 3; pgrep -fa "foamRun|foamMultiRun|pipeline.sh|air_case.sh" | grep -v pgrep || echo "all stopped"
