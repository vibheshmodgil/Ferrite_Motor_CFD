cd ~/cfd/u666_etest
for it in 5 20 50 99; do echo it$it; awk -v it=$it '$0 ~ "PIMPLE: Iteration "it"$"{f=1} f&&/Solving for e/{n++; if(n%2==1) printf "%s %s;", $1, $9} n>=20{exit}' log.run | sed 's/,//g'; echo; done
