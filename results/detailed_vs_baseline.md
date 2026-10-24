# Detailed vs baseline thermal model

## duty1

| quantity | baseline | detailed |
|---|---|---|
| end time [s] | 477 | 477 |
| winding / coil max at end [C] | 190.2 | 171.2 |
| winding / coil mean at end [C] | 150.7 | 159.1 |
| magnet max at end [C] | 77.5 | 74.4 |
| housing max at end [C] | 86.4 | 88.6 |
| stator max at end [C] | 113.4 | 109.2 |
| time to 155 C winding [s] | 316 | 388 |
| time to 100 C magnet [s] | None | None |
| busbar max at end [C] | - | 148.6 |
| strap max at end [C] | - | 138.4 |
| tbar max at end [C] | - | 147.4 |
| bobbin max at end [C] | - | 151.4 |
| resin max at end [C] | - | 170.8 |

Heat crossing interfaces (W, + = into the first region), baseline at t = 420.0, detailed at t = 420.0:

- baseline: inair:inair_to_winding +277.3, winding:winding_to_inair -277.3, winding:winding_to_stator -276.7, housing:housing_to_stator +167.3, housing:housing_to_inair +133.4, inair:inair_to_housing -133.4, inair:inair_to_rotor -92.6, housing:defaultFaces -75.0, magnets:magnets_to_rotor +72.6, inair:inair_to_stator -56.0, housing:housing_to_bearings -30.8, bearings:bearings_to_housing +30.7
- detailed: copper:copper_to_resin -607.0, resin:resin_to_copper +605.0, bobbin:bobbin_to_resin +243.6, resin:resin_to_bobbin -243.6, bobbin:bobbin_to_stator -228.2, housing:housing_to_stator +190.2, resin:resin_to_stator -170.1, housing:housing_to_inair +127.2, inair:inair_to_housing -127.2, resin:resin_to_inair -126.3, inair:inair_to_resin +126.2, inair:inair_to_rotor -81.9

Global energy balance, detailed run (generation vs outflow + storage): -0.8 to +0.3 %

## duty4

| quantity | baseline | detailed |
|---|---|---|
| end time [s] | 2700 | 2700 |
| winding / coil max at end [C] | 223.8 | 218.8 |
| winding / coil mean at end [C] | 209.4 | 212.9 |
| magnet max at end [C] | 197.9 | 194.0 |
| housing max at end [C] | 197.0 | 195.6 |
| stator max at end [C] | 201.6 | 197.4 |
| time to 155 C winding [s] | 1224 | 1300 |
| time to 100 C magnet [s] | 800 | 851 |
| busbar max at end [C] | - | 204.6 |
| strap max at end [C] | - | 198.0 |
| tbar max at end [C] | - | 202.2 |
| bobbin max at end [C] | - | 211.7 |
| resin max at end [C] | - | 218.7 |

Heat crossing interfaces (W, + = into the first region), baseline at t = 2700.0, detailed at t = 2700.0:

- baseline: housing:defaultFaces -390.7, housing:housing_to_stator +190.5, inair:inair_to_housing -178.7, housing:housing_to_inair +178.0, winding:winding_to_inair -149.3, inair:inair_to_winding +149.2, winding:winding_to_stator -108.2, bearings:bearings_to_housing -73.7, housing:housing_to_bearings +73.2, magnets:magnets_to_rotor +38.2, inair:inair_to_rotor -34.3, bearings:bearings_to_shaft -26.0
- detailed: housing:defaultFaces -384.8, copper:copper_to_resin -249.4, resin:resin_to_copper +245.1, housing:housing_to_stator +199.6, inair:inair_to_housing -165.6, housing:housing_to_inair +164.7, resin:resin_to_bobbin -96.0, bobbin:bobbin_to_resin +95.8, bobbin:bobbin_to_stator -92.3, bearings:bearings_to_housing -72.6, housing:housing_to_bearings +72.1, resin:resin_to_stator -69.9

Global energy balance, detailed run (generation vs outflow + storage): -2.1 to -1.7 %

## Why they differ
- Hot spot vs mean: the baseline winding is a smeared block with isotropic k = 1 W/mK, so heat cannot run along the
  wire and the slot centre peaks (duty1 max - mean ~40 K). The real wire (k 390) spreads heat along every turn
  (max - mean ~12 K): lower hot spot and a later 155 C crossing, but a HIGHER winding mean.
- Higher mean: all copper heat must cross the resin (0.25 W/mK) and the PA66 bobbin (0.35 W/mK) to reach the teeth.
  The baseline lumps this into one 1.7 mm / 0.30 W/mK layer and lets the end-winding block dump heat straight into
  the end-space air (duty1: 277 W baseline winding -> inair, vs 53 W copper -> inair + 126 W resin -> inair).
- Magnets / housing: within ~3-5 C; the stator-to-housing path and the outer h are the same. The magnets cross
  100 C slightly later in duty4 (851 vs 800 s) because less end-winding heat reaches the end-space air and rotor.
- Busbars / strap / terminal bars run 10-35 C below the coil hot spot: heated mainly by conduction from the coil
  leads; their own Joule heat is small (duty1 ~29 W at 20 C, of which busbar_20C 18.7 W).

## Model approximations (detailed mesh)
- CAD is the v7 motor_65 assembly: 65 mm stack vs 64 mm in Design9795_1, 30 mm shaft vs 25 mm; stator OD, bore and
  rotor diameter match.
- Coil = bare 2.9 mm Cu re-swept from the CAD centreline; the 0.05 mm enamel is meshed as resin (0.25 ~ 0.22 W/mK).
- Bobbin simplified (the CAD bobbins float 0.10-0.25 mm off the tooth with overlapping micro-faces and would not
  mesh): box sleeve + stepped end walls sharing the tooth faces, 4457 vs 4773 mm3 per bobbin, >= 0.27 mm from wire.
- coil, strap, busbar and tbar merged into one region "copper" (same metal, physically continuous); each part is a
  cellZone with its own Joule source. As separate regions the segregated Cu-Cu coupling stalled (energy -1.3 %).
- 4 tiny (4 mm3) air pockets in the rear-cover screw holes got no cells (adiabatic voids). 2 cells with aspect
  ratio 1225 fail checkMesh (acceptable for solid conduction); max non-orthogonality 88.8, skewness 3.14.
- Outer h re-mapped from the external-air CFD onto the detailed housing faces (results/h_cfd_detailed.json).
- Adiabatic energy test, 300 s: -0.9 % (results/energy_test_detailed.json). duty4 global balance is -1.7 to -2.1 %
  (baseline -1.16 %): the 60 s steps hit the 100-corrector cap early in the run, so treat duty4 temperatures as
  ~1-2 % of stored heat low.
- duty1: both runs end at 477 s (the baseline died there); fields saved at 420 s.

