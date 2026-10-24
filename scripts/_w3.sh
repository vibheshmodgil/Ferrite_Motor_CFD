cd ~/cfd/u666_etest
for i in $(seq 57); do grep -q "Time = 20s" log.run && break; sleep 10; done
grep "Time =" log.run|tail -1; grep -c "PIMPLE: Iteration" log.run; date
