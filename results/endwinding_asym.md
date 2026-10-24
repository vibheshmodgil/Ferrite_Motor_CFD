# Why the rear (non-drive-end) end winding runs hotter

Front = drive end (z < 0, mounting face). Rear = non-drive end (z > 0, rear cover, busbars, glands). The end turns are the coil parts outside the stack, |z| > 32.5 mm.
Data:
- Baseline model (smeared winding): results/vtk3d/duty1_420, duty4_2700, plus patch heat flows of ~/cfd/duty1 at 420 s.
- Detailed model (real wire): results/detailed/duty1/vtk3d_420 and duty4/vtk3d_2700, plus a foamToVTK export of det_duty4 at 900 s.
- Script: scripts/endwinding_asym.py.

## Temperatures

| | front end turns max / mean [C] | rear end turns max / mean [C] | rear - front (max) |
|---|---|---|---|
| baseline duty1, 420 s | 157.6 / 137.1 | **178.4 / 161.1** | **+20.8** |
| baseline duty4, 2700 s | 213.9 / 201.3 | **223.8 / 214.9** | **+9.9** |
| detailed duty1, 420 s (coil only) | 160.2 / 150.0 | 160.9 / 149.3 | +0.7 |
| detailed duty4, 900 s (coil only) | 129.4 / 125.9 | 129.6 / 125.4 | +0.2 |
| detailed duty4, 2700 s (coil only) | 218.5 / 213.2 | 218.6 / 212.3 | +0.1 |

The baseline hot spot sits at z = +37 mm (duty1) and +34 mm (duty4), at the rear end turn next to the stack.

## Local heat sources and cooling per end

| | front (drive end) | rear (non-drive end) |
|---|---|---|
| End-turn copper loss, detailed duty4 at 900 s | 41.9 W (23.8 cm3) | 45.0 W (25.6 cm3) |
| Busbar + strap + terminal-bar Joule loss | 0 | all of it (z 47-60 mm). duty1: about 27 W at 20 C and about 40 W hot. duty4: 6.2 W at 900 s. Detailed model only; the baseline has none. |
| Bearings (one heat source on two equal rings) | duty1 6.3 W, duty4 54.7 W | the same |
| Gap from end turns to the end wall | about 5 mm (end turns reach z -42; front wall inner face z -47.2) | about 33 mm (end turns reach z +42; cover inner face z 75.5), with busbars and terminal bars in between |
| End-space air volume (detailed mesh) | 140 cm3 | 701 cm3 (5x) |
| End wall | 5 mm, cast in one piece with the barrel and the drive-end mounting face (332 cm2, CFD h 5.5) | separate 3 mm bolted cover (272 cm2, h 5.8). The model fuses it to the housing, so no contact resistance: optimistic |
| Outer barrel over the end region | ring fins from z -44 | bare barrel z 30-67.5 (CFD h 3.8) plus the 4 gland bosses |
| Inner housing area seen by end-space air | 261 cm2 | 551 cm2 |

## Heat flows per end (W)

| | front | stack | rear |
|---|---|---|---|
| baseline duty1, 420 s: winding to end-space air | 81.4 | 123.4 | 72.5 |
| baseline duty1, 420 s: end-space air to housing | **61.3** | 32.4 | **39.7** |
| baseline duty1, 420 s: housing to ambient | 20.6 | 35.0 | 19.4 |
| baseline duty1, 420 s: housing into bearings (then into the shaft) | 21.9 | - | 8.7 |
| detailed duty4, 900 s: copper to resin | 32.6 | 151.5 | 21.8 |
| detailed duty4, 900 s: copper to end-space air (exposed leads) | 0 | 0 | 16.2 |
| detailed duty4, 900 s: resin to end-space air | 19.8 | 20.5 | 9.0 |
| detailed duty4, 900 s: end-space air to housing | 18.1 | 29.1 | 47.6 |
| detailed duty4, 900 s: housing to ambient | 37.1 | 60.6 | 41.0 |
| detailed duty4, 900 s: mean housing temperature [C] | 102.0 | 102.8 | 104.9 |

## Reasons, ranked

1. **The baseline's smeared winding magnifies the asymmetry.** The baseline winding block has an isotropic k of 1 W/mK, so a hot end cannot shed heat along the wire to the cooler end. In the detailed model each coil is one continuous copper conductor (k 390), and the two ends stay within 1 C of each other (duty1 160.2 vs 160.9 C; duty4 218.5 vs 218.6 C). Most of the +21 C (duty1) and +10 C (duty4) rear excess is therefore an artefact of the baseline model. In the real motor the rear-side penalty is spread over the whole winding and raises its average, not one end.
2. **The rear end turns are 6x further from a cold wall.** At the front the end turns sit about 5 mm from the cast end wall; at the rear there are 33 mm of end space (5x the air volume) before the cover. Both models treat the end-space air as an effective conductivity (k 0.45 W/mK in duty1, 1.03 in duty4), so the resistance grows with that path length. In baseline duty1 the front end space passes 61 W to the housing through 261 cm2, the rear only 40 W through twice the area (551 cm2).
3. **The rear has less outside cooling.** The front end region sits under the fins and next to the drive-end face, which is the best-cooled outer surface (h 5.5, plus the mounting bosses). The rear barrel (z 30-67.5) is bare apart from the gland bosses, and the rear cover is a thin 3 mm bolted plate. The rear housing runs about 3 C warmer (104.9 vs 102.0 C, detailed duty4 at 900 s). The real cover-to-housing joint, an O-ring spigot plus 5 x M5 screws, would add a contact resistance the model leaves out.
4. **The busbars, straps and terminal bars all sit at the rear.** Their Joule loss is 27-40 W in duty1 and 6 W in duty4 at 900 s, all at z 47-60 mm, and they are joined by copper to the rear coil leads. The detailed model includes them; the baseline does not, so the real rear end is somewhat worse than the baseline suggests.
5. **The end-turn copper loss is nearly symmetric.** Rear 45.0 W vs front 41.9 W (+7 %), because the rear end turns are slightly longer (25.6 vs 23.8 cm3). This is a minor cause.
6. **The bearings are symmetric and do not cause it.** Both rings are equal and share one heat source (54.7 W each side in duty4). The front bearing boss carries more heat into the shaft (22 vs 9 W in baseline duty1), which helps the front slightly.

## How to bring the two ends together

- **Fins on the rear barrel.** The fin variant now running (tapered rings H16 p11.5 over z -44..67.5, with cut-outs round the glands) adds 3 rings over the bare rear barrel, the zone with h 3.8 and no fins today.
- **A heat path from the busbars to the housing.** A thermal gap pad or potting between the busbar plates and terminal bars (z 47-60) and the rear housing wall (r 82) or the cover would send the 27-40 W of busbar heat, plus the heat flowing out of the rear coil leads, to the housing instead of the end-space air.
- **Shorten the rear end-space path.** Pot the rear end turns, or fill the rear end space with a conductive compound (k about 1 W/mK, against 0.45-1 W/mK for the stagnant air equivalent), bridging the 33 mm gap to the housing. Inner ribs on the rear cover reaching toward the end turns would also help.
- **Make the cover a real heat sink.** Use a thicker cover (5 mm, matching the front wall) and thermal paste on the spigot. Outer ribs on the cover face would help, but only if the 205 mm OD and the glands allow them.
