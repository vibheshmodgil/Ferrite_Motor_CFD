cd ~/cfd/u666_etest
awk '/Calculating couplings/{reg=$1; n=$5" "$8} /Source min\/average\/max coverage/{s=$0} /Target min\/average\/max coverage/{print reg, n, "src", substr(s,index(s,"=")+2), "| tgt", substr($0,index($0,"=")+2)}' log.dbg | head -24
