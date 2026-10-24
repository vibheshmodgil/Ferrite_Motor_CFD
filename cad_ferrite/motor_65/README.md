# Motor variant 65 – 65 mm stator, 66 mm rotor, terminals inside the housing

Second complete motor design (the first one, with the external terminal cap, is in `../motor`).

| | `../motor` | **this folder** |
|---|---|---|
| Stator stack | 63 mm | **65 mm** (teeth, bobbins, coils stretched 1 mm each side) |
| Rotor stack | 65 mm | **66 mm** (0.5 mm overhang each side of the stator) |
| Phase terminals | outside, under a gasketed cap at 31° | **inside the housing**: M8 press-in studs on the terminal bars |
| Cable exit | 3 x M20 IP68 glands in the cap top (r 130 + glands) | **3 x M20 IP68 glands in flat bosses on the housing wall** (domes to r ≈ 115) |
| Radial envelope at the terminals | ≈ r 150 | **≈ r 115** (fins r 94) |
| Body length (hub face to rear cover) | 129.1 mm | **141.6 mm** (+2 stack, +10.5 for the lug / nut stack inside) |
| Mass | ≈ 11.4 kg | ≈ 11.5 kg |

**Open first:** `MOTOR_65.SLDASM` (or `MOTOR_65.step`). `CHECKS_motor65.txt`: 355 part pairs, **0 overlaps, every clearance OK**.

## How the terminals work
```
busbar plate ─ riser ─► flat Cu bar 3 x 10, 4 mm above the other plates
                          └─► round pad with an M8 PRESS-IN STUD (flush underneath), inside the housing
                                 cable lug 35 mm² on the pad, washer, thin nut
                                 lug barrel points radially out
                                        └─► M20 IP68 gland in a boss on the housing wall ─► cable out
```
* Studs at 12° (L1), 50.5° (L3), 72° (L2). L1 and L3 sit next to their busbar terminals; the L2 bar runs in at 31°,
  round at r 42 (inside every lug palm) and out to its stud, so no bar passes under another phase's lug.
* Encoder cable: M16 IP68 gland at 92°.
* IP67: shaft lip seal (drive end), rear cover spigot O-ring, IP68 glands with O-rings on the wall bosses. No terminal box,
  no extra cover. Service: remove the rear cover (5 x M5) and the three nuts are in front of you.

## Parts
Same as `../motor` except: `tooth_65`, `bobbin_A_65`, `bobbin_B_65`, `04_coil_65` (65 mm stator), `busbar_L*_65`,
`link_strap_65` (raised 1 mm), `terminal_bar_L1/L2/L3` (new routing), `stud_M8_press_in` (replaces bolt, terminal block,
cap and gasket), `housing` (gland bosses, longer rear), `rear_cover`, `key_8x7x56`.

## Rebuild
```
python build_stator65.py    # 65 mm stator parts from the variant-B ones
python build_motor65.py     # motor parts + instances.json
python check_motor65.py     # -> CHECKS_motor65.txt (~6 min)
python sw_build_motor65.py  # SolidWorks: coil sweep, SLDPRT, MOTOR_65.SLDASM, MOTOR_65.step
```
Still to confirm (as for `../motor`): bearing part number for 52 / 30 / 15 (not a standard deep-groove size).
