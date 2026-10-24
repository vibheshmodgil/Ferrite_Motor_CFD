f=/home/cfd/cfd/inair_continuous/log.run2
grep '^Time =' $f | tail -1; grep continuity $f | tail -1; grep -c FATAL $f
ps -eo etime,pcpu,rss,cmd --sort=-rss | grep -E "python|foam|mpirun" | grep -v grep | head -6 | cut -c1-140
grep -a "Meshing 3D\|Meshing 2D\|Meshing 1D\|Info    : Done meshing" ~/cfd/mesh/detailed.log | tail -3
