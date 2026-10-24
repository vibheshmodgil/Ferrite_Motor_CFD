for i in $(seq 57); do pgrep mpirun >/dev/null || break; sleep 10; done
pgrep -c mpirun
