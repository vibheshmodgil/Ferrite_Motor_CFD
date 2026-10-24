cd ~/cfd/inair_continuous
sed -i 's/^startFrom latestTime;$/startFrom latestTime; startTime 0; stopAt endTime; endTime 2000; deltaT 1;/' system/controlDict
grep -n "startFrom\|deltaT\|writeInterval" system/controlDict
