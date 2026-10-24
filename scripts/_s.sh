# summary of ~/cfd/u666_e2: last time, wall, balance, interface pair sums
cd ~/cfd/u666_e2
echo "steps $(grep -c "^deltaT = " log.run) wall_run $(( $(cat t_end) - $(cat t_start) )) s"
grep -iE "fatal|nan " log.run | head -3
ADIAB=1 python3 /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/u666_energy_balance.py . duty1 x > log.balance 2>&1; tail -1 log.balance | cut -c1-60
python3 - <<'PY'
import json; d = json.load(open('energy_balance.json'))
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items() if k not in ('iface_W', 'volumes_cm3')})
for k, v in d.get('iface_W', {}).items():
    print(k, {a: round(b, 2) for a, b in v.items()})
PY
