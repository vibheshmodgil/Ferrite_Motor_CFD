# Design9795_1 (copper) losses at the slide-3 duty points

Source: `Design9795_1/lab_100C.json` (FEMM d-q map + Motor-CAD loss settings, lab_model v3, skew 3 slices; 52 V, MI 0.95, winding and magnets 100 C), bilinear interpolation. Checked against Motor-CAD Lab `Map_1.xlsx` (interpolated) and the old v7 `femm_em/eff.json`. CFD input: `loadpoints.json` duty1..duty5 from `scripts/loadpoints_9795.py`. v7 is shown for comparison only.

## Losses [W] (FEMM-Lab / Motor-CAD / old v7)

| point | rpm | N.m | Cu DC 100C | Cu AC | stator Fe | rotor Fe | bearings | windage | **total** | I_line A | id/iq phase pk A | V_ph pk (max 49.4) | T_max at speed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| duty1 | 1782 | 37.0 | 580 / 584 / 533 | 30 / 33 / 0 | 63 / 70 / 43 | 18 / 21 / 4 | 13 / 13 / 7 | 5 / 5 / 1 | **709 / 725 / 588** | 293 / 294 / 281 | -70/229 | 28.1 | 44.0 |
| duty2 | 2550 | 26.3 | 285 / 288 / 254 | 32 / 35 / 0 | 84 / 90 / 58 | 22 / 25 / 6 | 20 / 20 / 10 | 9 / 9 / 1 | **452 / 466 / 328** | 206 / 207 / 194 | -34/164 | 36.2 | 44.0 |
| duty3 | 3637 | 20.0 | 166 / 171 / 150 | 39 / 42 / 0 | 115 / 120 / 78 | 28 / 31 / 8 | 32 / 32 / 15 | 14 / 14 / 3 | **394 / 410 / 253** | 157 / 159 / 149 | -23/126 | 47.6 | 35.6 |
| duty4 | 9339 | 3.24 | 97 / 100 / 117 | 149 / 136 / 0 | 154 / 167 / 74 | 31 / 40 / 7 | 109 / 109 / 37 | 47 / 47 / 19 | **587 / 599 / 254** | 120 / 122 / 132 | -96/21 | 49.2 | 13.4 |
| duty5 | 1612 | 12.43 | 66 / 68 / 54 | 3 / 3 / 0 | 32 / 33 / 24 | 6 / 7 / 2 | 11 / 11 / 6 | 5 / 5 / 1 | **123 / 128 / 88** | 99 / 100 / 90 | -8/80 | 19.7 | 44.1 |

All five points are inside the 52 V envelope. duty4 is at the voltage limit (49.2 of 49.4 V, deep field weakening, pf 0.5). Magnet loss is 0 in both models. Direct re-solve of the d-q map at the exact point agrees with the map interpolation within 1 %.
OP2 cross-check (9339 rpm, 3.27 N.m, alu9795_ops.json copper): Cu 98 + AC 150 + Fe 185 + mech 156 = 590 W, I 120.7 A. Same as duty4 here.

## Audit: v7 (main) vs Design9795_1

| item | v7 | Design9795_1 | effect on losses |
|---|---|---|---|
| Stack length | 65 mm | 64 mm | -1.5 % flux/torque/iron mass; slightly shorter MLT |
| Stator | v7 segmented CAD profile (fieldlab_v7), bore 107 | Motor-CAD Parallel Tooth, OD 160, bore 107, tooth 15.54, slot depth 17.65, opening 5.58 | different tooth/yoke B, so different iron |
| Rotor | opening 10, X 18, Y 8.5, Z 6, glue 0.1, bridge 2, offset 3.5 | opening 7.05, X 18.86, Y 9.17, Z 7.11, glue 0.0625, bridge 1.0, offset 5.0 | thinner bridges: less leakage, more flux |
| Shaft | 30 mm, non-magnetic (air) | 25 mm, magnetic SCM420 | extra flux path; flux map fitted to Motor-CAD |
| Magnet | Y40-class ferrite, Br20 0.45 T, -0.20 %/K, mu_r 1.10, solved at 35 C (calibrated to 45 N.m) | DMEGC DM4654, Br20 0.46 T, -0.1797 %/K, mu_r 1.08, solved at 100 C (Br 0.394 T) | v7 had 11 % more Br than a 100 C magnet: less current per N.m, so v7 copper is too low |
| Steel B-H / stacking | catalogue M235-35A, stacking 0.95 | Motor-CAD M235-35A curve, FEA fill 1.0 (mass 0.97) | q-axis flux +3-8 % |
| Iron loss coefficients | KH 0.0177 f B^2 + KE 6.2e-5 f^2 B^2 | Kh 0.02533 f B^2.07 + 2 pi^2 x 2.199e-6 (n f)^2 B_n^2 per harmonic, minor loops Kc 0.65 | higher hysteresis, harmonic eddy |
| Iron field | no-load snapshot scaled by |psi|/psi_m | full-cycle FEA Fourier per element, on-load | captures armature reaction and slot harmonics |
| Build factor | 1.5 | 1.6 stator and rotor | +7 % |
| Rotor iron | 10 % of stator | own FEA (about 18-28 % of stator) | rotor 2-4x v7 |
| AC copper | none | strand eddy from slot B^2, Motor-CAD hybrid adjustment 2 | +30 W at duty1, +149 W at duty4 |
| Resistance | 2.90 mm wire, 6.732 mOhm/coil at 100 C | SWG 11 2.9464 mm, MLT 203.6 mm, 6.740 mOhm/coil at 100 C (alpha 0.003862) | about equal |
| End winding | not modelled | 1.954 uH/phase | small extra voltage |
| Mechanical | 4e-3 n + 2.2e-7 n^2 (56 W at 9339) | (11.85+8.89)(n/2600)^1.3 bearings + 8.89 (n/2600)^1.3 windage (156 W at 9339) | 2.8x at top speed |
| Skew | none | 3 slices, -2/0/+2 mech deg | torque ripple/harmonics down; slightly less torque |
| Limits/control | 52 V, MI 0.95, 360 A rms, 11 kW DC, inverter eff 0.97; minimum loss | 52 V, MI 0.95, 360 A rms, 280 A DC (14.56 kW), converter 0; MTPA (least current) | different d-q choice at part load |
| Magnet loss | none | ~0 (ferrite 100 ohm.m; Motor-CAD 0 W) | none |

## Battery voltage (stored d-q map, MI 0.95, DC limit 280 A)

| point | V_dc | reachable | T_max at speed N.m | I_line A | id phase pk A | I_dc A | Cu DC | Cu AC | Fe st+rot | mech | total W |
|---|---|---|---|---|---|---|---|---|---|---|---|
| duty1 | 52 | yes | 44.0 | 294 | -69 | 146 | 584 | 30 | 81 | 18 | 713 |
| duty1 | 48 | yes | 44.0 | 294 | -69 | 158 | 584 | 30 | 81 | 18 | 713 |
| duty1 | 44 | yes | 44.0 | 294 | -69 | 173 | 584 | 30 | 81 | 18 | 713 |
| duty4 | 52 | yes | 13.4 | 120 | -96 | 70 | 97 | 148 | 185 | 156 | 586 |
| duty4 | 48 | yes | 12.3 | 130 | -104 | 77 | 114 | 172 | 182 | 156 | 624 |
| duty4 | 44 | yes | 11.1 | 140 | -113 | 85 | 133 | 199 | 180 | 156 | 668 |

3.24 N.m stays reachable up to 12 000 rpm (the model's top speed) at 52, 48 and 44 V. At 9339 rpm, lower voltage needs more negative id: +38 W at 48 V, +81 W at 44 V, nearly all copper (DC + AC). duty1 is not voltage-limited, so only the DC battery current changes.

## Caveats

- AC copper (`winding_ac`) is a constant W. Physically it falls about 1/rho as the winding heats (about -13 % at 140 C vs 100 C), so at duty4 a constant value is slightly conservative.
- Stator iron runs 5-10 % below Motor-CAD and rotor iron 15-25 % below. Motor-CAD totals are 2-4 % higher. For a conservative CFD, scale stator iron by about 1.08 and rotor iron by about 1.25.
- Magnets are fixed at 100 C. A hotter magnet gives lower Br and more current, so copper rises at duty1.
- Mechanical loss uses Motor-CAD's default bearing/windage scaling (not measured). At duty4 it is 156 W, 27 % of the total.
- The busbar (`busbar_20C`, from the 360.3 A study) is not included in these motor totals.
