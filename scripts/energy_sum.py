"""Sum rho cv d(int T dV) per region from energy_check.sh output lines on stdin -> stored energy [J].
    ... | python energy_sum.py [expected_J]"""
import sys
RC = {"housing": 2680 * 900, "stator": 7650 * 460, "rotor": 7650 * 460, "magnets": 4900 * 800, "shaft": 7850 * 460,
      "bearings": 7850 * 460, "inair": 10 * 718, "winding": 0.51 * 8933 * 385 + 0.49 * 1200 * 1500,
      # detailed model (make_case.py MAT): bare-Cu coil, PA66-GF30 bobbin, resin, Cu busbar / strap / terminal bar
      "coil": 8933 * 385, "bobbin": 1350 * 1500, "resin": 1200 * 1500, "busbar": 8933 * 385, "strap": 8933 * 385,
      "tbar": 8933 * 385, "copper": 8933 * 385}
tot = 0
for l in sys.stdin:
    p = l.split()
    if len(p) == 5 and p[0] in RC:
        dE = RC[p[0]] * (float(p[4]) - float(p[2])); tot += dE
        print(f"{p[0]:9s} {dE / 1e3:9.2f} kJ")
print(f"stored    {tot / 1e3:9.2f} kJ" + (f"   expected {float(sys.argv[1]) / 1e3:.2f} kJ  error {100 * (tot / float(sys.argv[1]) - 1):+.1f} %"
                                          if len(sys.argv) > 1 else ""))
