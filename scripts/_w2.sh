cd ~/cfd/u666_etest
for i in $(seq 58); do [ -f log.recon ] && [ ! -e /proc/$(pgrep -o mpirun 2>/dev/null || echo 1)/exe -o -z "$(pgrep mpirun)" ] && break; sleep 10; done
ls; pgrep -c mpirun
