# U666 benchmark CFD: step log (single source for the method report)
Each entry has: date/time · step · inputs · method · assumptions · values · problems · status · files.
The main agent and the GEO agent append to this file; the REPORT agent renders it.

## S0 Inputs (2026-10-22)
- CAD: `U666 CAD/U666_L4_20261022/ge250440_step.stp` (Creo, GE250440_ASM, mm, axis z). 73 unique solids, 480 instances, 599 solids after import. No materials in the STEP ("NOT SPECIFIED").
- Losses: from the user's Motor-CAD (Ansys) screenshots, saved in `loadpoints_u666.json`. Each speed was checked as P_em/T_em, and each loss sum was checked against the total.
- Winding: user's Motor-CAD winding screenshot. 36 slots, stranded and overlapping (distributed), wire 0.76 mm with copper 0.71 mm, 5 strands in hand, 120 conductors drawn per slot.
- Motor-CAD slot data: slot area 97.57 mm², winding area 85.54 mm², copper 47.51 mm², wedge 0.89 mm², liner 0.25 mm, MLT 187.76 mm, end-winding fill 0.528.
- User statements: NdFeB magnets (not ferrite), NO busbar, BRASS rotor end caps, housing cast Al then machined (bare), NO potting, and the CAD winding body is only representative.
- Purpose: U666 is the benchmark motor with test data. Tune the CFD to the test, then apply the method to our motor. Use the same duty1–5 load points as last time.

## S1 CAD check and part map
- Inventory script: `scripts/u666_cadinv.py`, output `mesh/u666/inv.json`. The STEP import takes 18 min; the BREP cache is `mesh/u666/u666.brep`.
- Global bbox: x -100..246, y -647..98, z -101..149 mm. The phase cables reach y -647.
- Part map:
  - Stator: KE250030_1 ×173 laminations, OD 150, z -0.4..60.2.
  - Rotor: KE250110_1 ×180, OD 85.8, z -2.2..60.8.
  - Magnets: KE250130 ×54, r 23.9–40.3.
  - Brass end caps: KE250150 (z 60.8–65.8) and KE250370 (z -10..-2); nut KE250320.
  - Shaft: GE250300.
  - Bearings: 6205-2RSH front (z 78–93), SKF 6003-2Z rear (z -30..-20).
  - Housing: KE250089_1 (714 cm³, OD about 200). Front seat: KE250269.
  - Rear cover: KE250179_1 (270 cm³). Rear sleeve: KE250380.
  - Rear cap and plate: KE250200 / KE250300.
  - Liners: KE250520 ×36 (r 45.5–66.2). Wedges: KE250530 ×36 (r 44–48).
  - CAD winding: KE250510 (747 cm³, representative only).
- Dropped:
  - the 3 phase cables (GE250410/420/430) and the gland/connector (GE250480);
  - screws and washers; the circlip; the seal K2200050;
  - the sensor (KE250190) and the encoder (KE250340/310);
  - the terminal-block small parts.
- Problem: plane-face sampling for the radii gave wrong values (parametric bounds go past the trimmed faces). Only the cylindrical-face radii were used.

## S2 Materials (rho kg/m³, cp J/kg·K, k W/m·K)
| Region | Material | rho | cp | k | Source |
|---|---|---|---|---|---|
| Housing and cover | cast Al, machined, ε 0.1 | 2680 | 900 | 150 | kept from the last run; user: cast + machined |
| Stator and rotor | laminated steel | 7650 | 460 | 28/28/1.5 (in-plane/axial) | kept |
| Magnets | sintered NdFeB | 7500 | 440 | 9 | user: NdFeB; handbook values |
| Rotor end caps | brass CuZn39Pb3 | 8470 | 380 | 115 | user: brass; handbook values |
| Shaft | steel | 7850 | 460 | 45 | kept |
| Bearings | steel ring, reduced k | 7850 | 460 | 15 | kept |
| Winding in the slot | homogenised (see S3) | 5510 (scaled) | 473 | 1.12 transverse / 217 axial | S3 |
| End winding | homogenised | – | 473 | (r, θ, z) = (1.05, 205, 205) | S3; GEO proposal approved |
- Busbar, strap and tbar from the old model are REMOVED (no busbar in U666).

## S3 Winding homogenisation
- Script: `scripts/u666_winding_props.py`, output `results/u666/winding_props.json`.
- Transverse k: Hashin–Shtrikman lower bound (copper in a varnish+enamel matrix, k 0.25/0.2). A layered (Wiener series) model gives a lower bound of about 0.54 at Kf 0.555, which we judged too pessimistic.
- Axial k: rule of mixtures. rho and cp: mass-weighted.
- Kf = 47.51/85.54 = 0.555, giving k_T 1.12, k_ax 217, rho 5510, cp 473.
- End-winding fill 0.528 gives k_T about 1.05 and k_wire about 205.
- Liner 0.25 mm, k 0.15: R = 1.67e-3 m²K/W (h about 600 W/m²K), applied as a contact layer at the winding/stator interface.
- Assumptions: enamel/varnish rho and cp are typical values. The varnish fills all voids.

## S4 Geometry simplification (GEO agent)
- Attempt 1 (15:59) took over 50 min: it intersected the B-spline CAD winding with slabs. That approach was dropped.
- Attempt 2 stalled for more than 30 min after the BREP load (deleting about 450 solids, or the magnet sections).
- USER decision: build each lamination stack from ONE lamination face, extruded over the stack length.
  - Stator: z -0.35..60.2. Rotor: z -2.2..60.8.
  - Slots and pockets come from the profile.
  - The 3 axial magnet segments become 18 extruded columns.
- The wedges are clipped to the stack and merged with the slot opening.
- The liner is not meshed; it is the S3 contact layer. The slot winding fills 96.7 mm², with rho scaled by 85.54/96.67 so the copper mass and heat capacity are exact.
- Winding rebuilt (the CAD body was deleted):
  - slot profile extruded over the stack;
  - end windings as rings: shells about 5 mm thick at the slot mid-radius, overhang about 30 mm (matching the CAD).
  - Copper: in-slot 103.6 cm³ plus end windings 57.0 cm³ = 160.6 cm³ = 36 × 47.51 × 187.76/2.
  - The end-winding homogenised volume is 107.9 cm³ (54 cm³ per end).
  - CALIBRATION KNOB: the shell thickness, overhang and radius are parameters, tuned against the test.
- Tip applied: save a subset BREP of the needed solids only.
- Status: in progress (`mesh/u666/geo.log`).
- 18:08 GEO: fix for the stall. gmsh `occ.remove` is O(N²) on the 599-solid model: recursive removal stalled for more than 30 min, and non-recursive unbinding took 5 min for the faces alone. `scripts/u666_subset.py` now hides everything, shows only the needed solids and exports with `Geometry.OCCExportOnlyVisible=1`, in 49 s. The kept solids are 1 stator lamination, 1 rotor lamination, 18 magnets (segment 1), the housing parts (8), shaft, end caps and nut, seal, 36 wedges and 1 liner. Output: `mesh/u666/subset.brep` + `subset.json`. `u666_geo.py` loads only the subset.
- 19:20 GEO: regions built from the subset (subset 47 s, parts 5 min, fragment 10 min). Problems and fixes:
  - (1) The kept rotor lamination sat at z 39.8, so the extrusion ran past the stack. Fix: translate the profile to z -2.2.
  - (2) The inner end-space air was connected to the outside air. Section plots (filled, at 0/90/45° and z -65) show that the terminal box has a flat wall with 3 cable-gland bores of about 20 mm, open once the cables and glands are dropped. Fix: a 10 mm Al slab along that wall (z -90..-40) closes the bores. Screws stay as housing plugs (they fill their holes).
  - (3) The slot annulus ran to r 74.99, which filled the stator OD notches with winding. Fix: the slot region now ends at r 66 (slot bottom 65.5), and the notches stay air.
  - Cavity rule: pockets bounded only by housing (grooves, thread ends) are filled with housing. Pockets bounded only by rotor/magnets/endcaps/shaft become the `rpocket` zone (still air, k 0.03), and the rest is `inair`.
- 20:40 GEO: the leak remains after the bore plugs (fit clearances that are too small to locate). Switched to the old-pipeline internal-air envelope: inair = space no part claims inside 3 cylinders that end inside the walls. They are the front end space r 77.4 / z 61..96.5, the rear end space r 75.4 / z -36.7..-1.1, and the terminal box r 72.6 / z -91..-36, cut at the gland wall. Enclosed leftover air pieces also go to inair, except pockets bounded only by the rotor (rpocket) or only by the housing (filled).
  - Problem: the first try put envelope faces coincident with CAD/stack faces, and the OCC fragment returned overlapping solids (region volumes summed to the box + 1.6 L). Fix: odd radii and z values, plus a volume-closure check printed in geo.log.
- 20:40 GEO: CAD winding KE250510 measured on its own subset (`results/u666/geo_cadwinding.json`):
  - In-slot 227.6 cm³ (fills the slot, including liner and wedge space). It overlaps the liners by 14.1 cm³, the wedges by 6.5 cm³, and the stator by 0.16 cm³ (negligible).
  - End windings: front 255.8 cm³ (z 60.2..90.15, overhang 29.95 mm); rear about 256 cm³ (overhang about 30 mm, plus a 6.7 cm³ lead to the terminal box).
  - The CAD end blobs are about 4.7× the Motor-CAD end-winding volume (54 cm³ per end at fill 0.528), confirming that the body is only representative.
- 20:40 GEO: slot area. CAD slot to the bore = 106.5 mm²; above the slot opening (r 44) = 105.5 mm²; minus the CAD wedge (3.62 mm²) = 101.9 mm², against Motor-CAD winding + liner 96.67 mm² (+5.4 %). The meshed slot winding is 101.65 mm² per slot (221.58 cm³). In `u666_make_case.py`, slot rho, the copper fraction and k_axial are scaled by 85.54/101.65 (A_SLOT_MESH), so the copper mass and axial conductance match Motor-CAD.

- 20:43 MESH agent: inair-air leak closed (was 12991 mm2). Shared faces located from the brep (face adjacency):
  - (a) terminal-box envelope: 2 pieces (25.2 + 39.6 cm3) of the r 72.6 cylinder lie OUTSIDE the box walls (touch only housing + outside air, 9038 mm2 incl. the z -91.1 end faces) -> outside air.
  - (b) front shaft exit z 96.5-106.5: the seal was mapped to inair (3290 mm2 to air). Seal is now its own region `seal` (2.88 cm3, polymer: prep_base merges it into the wedge zone, k 0.2); a 0.1 cm3 seal piece touching only air (spring) -> air.
  - (c) shaft front centre bore r 5, z 62.8-96.5 (2.39 cm3), open to outside -> outside air (79 mm2).
  - (d) hexagonal through-hole (47 mm2) in the terminal-box cap at (-12.0, 32.9, z -91.1): plugged with a housing cylinder r 4.6 x 1 mm (+0.06 cm3 housing).
  - Rule in u666_geo.py: an internal-air piece that touches outside air but no other internal air is outside air (2 passes).
  - Also: rotor-pocket air (8 pieces, 48.6 cm3) is now `rpocket` (still air k 0.03, rule allows the open pocket ends); before it was lumped inair (k ~0.4, optimistic).
  - Result: inair-air contact 0.0 mm2, closure exact 360000 cm3. Regions cm3: inair 1403.7, rpocket 48.6, seal 2.9, housing 1108.9, air 356180 (+67 cm3), others unchanged.
  - Tried and reverted: envelope ends moved 0.5 mm into the stack (to remove the 0.15 mm slab beyond the rotor end) -> overlapping fragment (+1.6 L), as in GEO's first try.

## S5 Loss input and mapping
| Point | rpm | T Nm | DC Cu | AC Cu | Iron | Magnet | Windage | Friction | Total W |
|---|---|---|---|---|---|---|---|---|---|
| duty1 | 1782 | 37.33 | 1133 | 6.408 | 47.03 | 0.2857 | 4.256 | 9.928 | 1201 |
| duty2 | 2550 | 26.66 | 548.3 | 7.326 | 66.91 | 0.2163 | 8.56 | 19.97 | 651.3 |
| duty3 | 3637 | 20.4 | 324.4 | 9.881 | 94.92 | 0.4407 | 17.11 | 39.91 | 486.7 |
| duty4 | 9339 | 3.807 | 133.3 | 30.87 | 193.1 | 0.5651 | 107.6 | 251.0 | 716.4 |
| duty5 | 1612 | 12.68 | 132.2 | 0.8996 | 30.01 | 0.07383 | 3.5 | 8.165 | 174.8 |
- Mapping:
  - DC Cu goes to the winding, with q = q_ref·(1 + 0.00393·(T − T_ref)), T_ref = 100 °C (PENDING user confirmation). AC Cu goes to the winding as a constant.
  - Iron goes to the stator and rotor, 0.8/0.2 split (PLACEHOLDER, user split pending).
  - Magnet loss goes to the magnets. Windage goes to the internal end-space air (inair).
  - Friction goes to the bearings, 50/50 front/rear (placeholder).
- Open questions: duty4 friction of 251 W looks high (more than iron, more than 2× windage); is it measured, or does it include a seal or gearbox?
- Limits: winding 155 °C, magnets 100 °C. Targets: 5/15/30/45/45 min.

## S6 Contact resistances, boundary conditions and solver (from the old baseline; values to be re-checked for U666)
- See `handover/ENGINEERING_BASELINE.yaml`:
  - stator–housing shrink fit t 2e-5 m, k 0.026 (about 1300 W/m²K);
  - magnet–rotor glue t 1e-4, k 0.2;
  - air gap as an equivalent k from Taylor–Couette per point;
  - winding–stator now uses the liner R from S3.
- Outer skin: per-face h from the external-air CFD plus radiation, ε 0.1 (bare machined Al), ambient 40 °C. Natural convection, horizontal shaft, gravity -y.
- Internal end-space air: lumped inair region with k_inair = h_endspace × 0.01 m (old method). To be re-checked; it is a calibration knob.
- Energy check: an adiabatic test must close within ±1.5 % before any duty run.

## S7 Mesh (MESH agent, 2026-10-22/23)
- Solids mesh `u666_mesh.py --solids` (H 2.5, Delaunay 3D, 1 thread). gmsh failures on the dirty CAD, in order, and fixes:
  - 20:45 2D "1D mesh not a closed loop" on a 0.2 mm2 torus sliver at the terminal-box gasket rim (z -85). Compound retry did not help. Fix (geo): gasket (subset tag 74) shrunk 1.5 % in x/y about its centre (GASKET_SCALE; housing -0.44 cm3).
  - 21:53 2D hang on a housing B-spline lug face (1428, x -90 y 24 z -5): curvature sizing (10) makes its curves cross. Fix: MeshSizeFromCurvature 0 (env CURV). Face meshes at ~H.
  - 22:11 3D overlapping facets: the terminal-box envelope cylinder r 72.61 grazed a cone on the box outside. Fix (geo): the box envelope is cut by the housing and only the interior piece is kept (cut ~6 min).
  - 22:38 3D overlapping facets at the rotor OD: gap annulus r 42.68 vs lamination OD dips r 42.70..42.88. Fix (geo): annulus r 42.6 (pocket tops 42.35) FUSED with the lamination.
  - 23:07 3D "PLC Error: segment and facet intersect" (no location). Seen: 1D crossings of two circles 0.07 mm apart at the shaft/rotor rear end (shaft internal faces from lower-priority overlaps), 2-4 invalid triangles on fin and torus faces. Tried proximity sizing (Distance/Threshold balls at close CAD vertices, PROX 1.5): 1.74 M nodes, still PLC + 0.065 deg facet folds at the gasket (AngleToleranceFacetOverlap 0.01 set). PROX now off by default.
  - 00:17 new `scripts/u666_fuse.py`: fuses each region's pieces and re-glues with one fragment (~30 min) on `u666_geo_raw.brep`. Housing fuse fails in OCC ("Courbes non jointives"); one-by-one fusing lost 370 cm3 -> never fuse the housing. Endcaps fuse (cap + nut) left a dangling face -> skipped.
  - 01:47-02:35 shaft fused (u666_fuse) -> 2D ok, 3D still PLC. Invalid-triangle surfaces (fins every 66 surfaces, cap torus) re-meshed by mesh.py with MeshAdapt + a finer size: fixed, PLC remained. Per-region 3D test was invalid (a discrete msh gives 0 tets). HXT (ALG3D 10) also fails.
  - 02:35 gasket dropped -> the terminal box opens to the outside (11 000 mm2 leak): the gasket IS the seal. Reverted.
  - 09:17 gasket+cap+cover fused before the fragment (volume kept): leak 0, closure exact; 2D fails on an inverted torus (-0.0018 mm2) and cones (-1404 / -32 mm2) at x -55..-30 y -52..-35 z -86..-41. mesh.py now defeatures degenerate skin faces (worked for 1 face, shared faces unchanged) and fuses same-region pairs on a failure (worked once); the next inverted cone could not be defeatured.
  - 12:11 FALLBACK (assumption + calibration knob): cap 114 + gasket 74 replaced by extruded profiles (walls = cap section z -88 over z -90.5..-83.5, overlapping the cover = seal; lid = section z -91.5 over CAP_LID_Z0 -93.55..-90.5, thickened to keep 53.3 cm3; screw bosses dropped), fused with cover 64. Isolated test: 0 tiny faces, fuse 84 s. Chain geo -> mesh running; result pending (see handoff/u666_mesh_handoff.md).
- 12:33 cap-fallback chain (DEFEAT agent check): geo OK (inair-air 0 mm2, closure exact 360000 cm3), mesh --solids FAILED again: 3D "PLC Error: segment and facet intersect".
- 13:00-15:50 DEFEAT agent, per-part CAD defeature (user decision 12:15), `scripts/u666_defeature.py` (pre-pass subset.brep -> subset_df.brep, `u666_geo.py --df`):
  - Inventory: `results/u666/defeature_inventory.md` (fillets r < 1.95 mm with arc span <= 0.55 pi, cone chamfers < 2 mm, holes d < 3 mm). Housing 39/64: ~350 blends r 0.2-1.0, ~130 chamfers, 8 holes d 2.5 (64); shaft 53 faces; screws, endcaps small. Threads: none modelled in the CAD. Wedges and lip seal kept exact. ~870 B-spline faces of housing 39 not classifiable (fins/blends).
  - Result: OCC defeature is impractical on this CAD. Shaft 51/53 faces (dV +0.17 cm3); small housing parts 40/65/66/119 mostly fail (2/14, 2/14, 0/4, ~19/47); screws/endcaps mostly OK. Housing 39: 200 s for one 15-face call, then > 20 min hang on the next; cover 64: 408 s per 15-face call, one 284-face call > 30 min with no end.
  - Problems met: a failed defeature call can delete the input solid (fixed with a backup copy per call); bulk occ.remove is O(N^2) here (export now uses OCCExportOnlyVisible).
  - Main decision 15:46: stop the defeature, switch to snappyHexMesh multi-region from the gmsh 2D surfaces (strategy A). The --df geo path stays in the code, unused.
- 15:55 strategy A: `u666_mesh.py --solids --stl` (2D only, retries as before) -> `mesh/u666/stl/<region>.stl` + `skin.stl` + `volumes.json`; `scripts/u666_snappy.sh` -> `~/cfd/u666_snappy` (blockMesh H 2.5 mm, region surfaces = faceZone + cellZone (mode inside), skin = outside patch -> defaultFaces, mesh built in mm and scaled to m); `u666_prep_base.sh` now accepts the snappy case dir.
- 16:00-16:55 snappy (strategy A): the first run (levels up to 3, nCellsBetweenLevels 2) reached 8 M cells and 8/9 GB of WSL RAM, so it was killed. The coarsened run (levels (1 1), wedge/seal 2, 2.4 M cells) stalled > 25 min after "762458 free-standing zone faces": the closed per-region STLs overlap on every shared face, which fragments the zones (OF12 has one insidePoint per surface, so per-interface STLs are not workable with 28 housing / 18 magnet pieces). Dropped. `u666_snappy.sh` and the `--stl` export stay in the code, unused.
- 17:00 switch to the simple housing (S7b): `U666_HOUSING=simple` in `u666_geo.py` (CAD version saved as `scripts/u666_geo.py.bak_cad`).
  - housing = 8 solids of housing_simple.brep; screws, cap fallback and plugs skipped; no cavity envelopes (the simple housing is closed, so inair = the enclosed complement).
  - Fix 1: the CAD lip seal against the simple hub bore broke the fragment (body left uncut, +694 cm3 closure). The seal is now a plug primitive: disk r 21, z 100.5..106.5; housing and shaft claim first; seal 4.9 vs CAD 2.9 cm3 (KNOB). After this fix: closure exact, inair-air 0.
  - Fix 2: without envelopes the pocket air merged into inair (rpocket 6.1 vs 48.6 cm3), so an rpocket cylinder r 42.45 over the rotor z (lowest priority) was added.
  - The 3D mesh still fails with PLC (simple housing, closure exact, leak 0). CORRECTION: the per-region and cumulative DIAG passes in `u666_mesh.py` (Mesh.MeshOnlyVisible) produced 0 tets, so their 'ok' results are VOID and the PLC source is still unknown. Set DIAG=0 or fix the visibility (surfaces/curves must be visible too) before trusting it.
- Region volumes, simple housing (cm3): housing 1048.7 (CAD run 1109.8), inair 983 (CAD 1402.7, simple cover interior differs), seal 4.9; all others unchanged (stator 477.33, slot 221.58, endw 107.97, rotor 244.84, magnets 36.55, shaft 89.38, bearings 32.16, endcaps 36.77, wedge 9.52).
## S8 Base case and energy test — pending
## S9 External-air CFD (h map) — pending
## S10 Duty runs — pending
## S11 Calibration against the test — pending (needs the test data)

## S7b Simplified housing, backup (HSIMPLE agent, 2026-10-23)
- Purpose: fallback for the dirty housing CAD (B-spline fillets break gmsh). `scripts/u666_housing_simple.py` -> `mesh/u666/housing_simple.brep` + `.json` (5 s). Planes, cylinders and cones only; no fillets. CALIBRATION KNOB: dict `K` in the script (fin profile, tip/valley radius, skirt thickness, box thickness).
- Measured from `subset.brep` (subset tags 39 body, 40 front seat, 64 rear cover, 65 rear seat, 66 O-ring, 74 gasket, 114 terminal cap, 119 gland): face types/areas/bboxes + one y=0 section. The section is slow (225 s) because of B-splines.
- Findings: fins are 11 CIRCUMFERENTIAL rings (not axial strips), pitch 10 mm, centres z -12.8..87.2, valley r 79.4-79.6, tip r about 93-94 (lugs reach 100). Stator fit bore r 75.0 over z -6.3..60.2, shoulder at 60.2 (r 74.0 beyond, to z 91.2). Front end wall z 94.2..97.7, hub to z 126.7 (bore 16.9/19.8/25.5), 3 bosses r 12 at r 72.5 to z 117.7. Rear socket bore r 78.4 over z -25.8..-11.3. Bearing seat bores: front r 26.0 over z 77.56..97.5, rear r 17.5 over z -31.2..-20.5 (same as the bearing annuli in `u666_geo.py`). Rear cover: flange r 80.5 z -27.3..-39.5, floor z -36..-39.5, skirt r 66 to z -83.7 (thickness SOLVED = 7.56 mm to hit 269.6 cm3). Terminal box x -68.4..68.6, y -52.4..79.3, z -101..-83.8 (lid 2.0, wall 1.6 so volume = CAD 49.6 cm3).
- Comparison (CAD | simple | diff):
  - volume of the 8 parts: 1064.2 | 1042.6 cm3 | -2.0 % (body 714.3 | 693.9 -2.9 %, cover 269.6 | 269.6, box 49.6 | 49.0, front seat 18.6 | 19.0, rear seat 4.15 | 4.11, gasket 3.7 | 3.65, O-ring 2.97 | 2.1, gland 1.23 | 1.19).
  - fin band skin (z -6..94, r > 78; CAD from `stl/skin.stl`): 1616 | 1635 cm2 | +1.1 % (the fin tip r 92.5 is tuned down from the measured 93-94 to match the area; the same profile with tip 94 gave +9 %).
  - total outer skin (cavities filled): 2763 (skin.stl minus 26 cm2 shaft stub) | 2927 cm2 | +5.9 %. The excess is the terminal box: 273 cm2 vs 173 cm2 in skin.stl, which holds GEO's fallback cap and not the real cap. Without the box: +2.5 %.
  - fit/seat (exact by construction, read back from the BREP): bore r 75.00 z -6.3..60.2; seat r 26.00 z 77.56..97.5; seat r 17.50 z -31.2..-20.5; end wall 94.2/97.7.
- Mesh test: gmsh 2D + 3D, H 2.5, 1 thread, 8 solids after fragment: 0 errors, 429 k tets, 21 s (`scripts/_h_meshtest.py`, log `mesh/u666/_hs_mesh.log`).
- Assumptions: the rear cover is axisymmetric (the real one has flats and cable pockets; the skirt thickness absorbs the mass). Lugs, feet, the 3 boss holes and the screws are omitted. Fin tips are circular. The O-ring is a rectangular ring (r 76.6..78.4). The terminal box is a hollow box with an open interior.
- Swap-in (NOT done; `u666_geo.py` belongs to DEFEAT): in `u666_geo.py` replace `pick("housing","screws")` (line 167; also drop "housing" and "screws" from `keep` at line 122) with the 8 solids of `housing_simple.brep`, imported at the same place and in the same frame. Remove the cap/gasket/cover fallback at line 185 (tags 74, 114, 64) and the plug logic at line 195 (no screw holes are left). Check the cavity annuli at lines 226-232 against the new walls: cover inner r 72.4, spigot r 76.6, socket bore r 78.4. Proposed env flag: `U666_HOUSING=simple` (default `cad`) selects the swap.

## S7c Mesh, route B non-conformal (MESH2 agent, 2026-10-23 18:30-21:40)
- What failed: the conformal one-shot 3D (tetgen "PLC: segment and facet intersect", no location; HXT fails too).
  - Located with a surface-mesh check (`scripts/u666_surfcheck.py`: edge-triangle crossings on the 2D mesh).
  - Cause 1: shaft r 15.03 vs rotor bore r 14.96 (press fit). The fragment leaves 0.07 mm shaft shells whose end arcs cross in the 1D mesh (z -2.2).
  - Cause 2 (the one the PLC came from): rear bearing bore r 8.5 vs shaft r 8.47 at z -20.2. This leaves a 0.03 mm inair ring, and the 1.5 mm chords cut across the other circle (108 crossings).
- Dropped:
  - fusing shaft pieces in the full model breaks conformity (131 faces lose their partner);
  - cutting the rotor by the shaft in geo hangs the fragment (>90 min; env CUT_ROTOR_BY_SHAFT, off);
  - transfinite matched circles (the arcs have different spans).
- Fix / route: OpenFOAM CHT does not need conformal interfaces.
  - Each final region is meshed alone (`u666_mesh.py --solids --group G`). Thin same-region pieces (2V/A < 0.2 mm) are fused (shaft, endcaps, wedge, housing).
  - Patches `<G>_to_<nb>` come from the conformal brep adjacency. Fused faces that span two neighbours are split per triangle by the nearest partner triangle.
  - A 0.3 mm refinement box sits at the rear bearing bore.
  - Assembly: `scripts/u666_assemble_nc.sh` gives mappedWall with `method intersection` (the OF12 AMI).
- Result: 10 regions, 4.17 M cells in total. 7 of them pass checkMesh. inair, wedge and rotor fail on skewness only (85 / 200 / 5 faces, max 9.2 / 5.5 / 5.6).
- Interface areas: 23 pairs. 21 are within 1.3 %; endcaps-shaft is 3.7 % and endcaps-magnets 4.9 % (about 40 mm2 each, from the per-triangle split).
- Assumptions:
  - the 0.03 mm rear bearing-shaft air ring is kept as inair, so the shaft-bearing heat path goes through air there (KNOB: close it in geo by setting the bearing bore to the shaft radius);
  - the non-conformal AMI couples are assumed conservative; the energy test must confirm this.

## S8 - nc base case + energy test (BASE agent, 2026-10-23/24) - GATE NOT YET MET
- Case `~/cfd/u666_etest` from `~/cfd/u666_base_nc` via `u666_make_case.py` (dummy etest losses 128 W, adiabatic). Region names matched; no renaming needed.
- Schemes: laplacian/snGrad `Gauss linear limited corrected 0.33` (isotropic regions), `uncorrected` (anisotropic: stator, rotor, winding); nNonOrthCorr 1. Contact R unchanged (liner 1.67e-3, fit 2e-5/0.026, glue 1e-4/0.2, gap layers k_gap).
- Fixes needed (all in make_case / new lib):
  1. mappedWall `intersection` aborts "not geometrically similar": `matchTolerance 0.5` added to every mapped patch (also 0.5 only needed for endcaps-shaft, centre offset 1.9 mm).
  2. coupledTemperature gives NaN on uncovered nc faces (coverage 0, 5 pairs). New lib `scripts/u666_build_ctnc.sh` -> `libcoupledTemperatureNC` (copy; faces with sumKappaByDelta ~0 treated adiabatic). Type `coupledTemperatureNC`, `libs` in controlDict. Build once per machine.
  3. Zonal Cv jump (rpocket air Cv 1007 vs rotor 460) blew up rotor (2000 K in 1 outer iter). RPOCKET now Cv = rotor Cv, rho scaled (rho*Cv of air kept).
  4. Anisotropic winding (cylindrical, 1.12/185) DIVERGES in the outer coupling loop (T 1e6 within 20 outer its). `WIND_ISO=1` (k = 1.12 all directions) is stable. Laminations anisotropic are stable (N=60).
  5. Tolerant solver: GAMG DICGaussSeidel fine once 1-3 fixed.
- Result so far (WIND_ISO=1, 10 s, 60 outer its, NOT converged: "Not converged within 60 iterations"): stored 1.390 kJ vs injected 1.280 kJ = +8.6 %. Gate (+-1.5 %) not met; cause unknown (unconverged coupling vs real interface non-conservation). Interface coverage averages are 0.97-1.01 except endcaps pairs (0.82-0.97).
- Timing: setup (decompose+coupling) ~90 s; ~7 s per outer iteration (4 procs, 4.17 M cells). 10 s step with 60-100 outers = 7-12 min => ~45-70 s wall per simulated second. duty1 (300 s, dt 10) would be ~4-6 h even with winding fix; needs fewer outers (e.g. 10-20) or coarser region coupling.

## S8b - prism meshes + energy test (BASE2 agent, 2026-10-24) - GATE NOT YET MET (-8.7 %, cause located)
- Mesh: `u666_mesh.py --solids --group G` z-PRISM route (env EXTRUDE, default winding,stator,rotor,magnets,wedge): mid-z section of each zone volume -> per-(zone,z-band) union -> 2D fragment -> triangles x z-layers (DZ 2.5 mm; band ends closer than SNAPZ 0.5 mm merged, e.g. magnet/rotor 0.19 mm CAD steps). endw is an annular z-prism, so slot+endw stay one conformal winding mesh. Patch labels = nearest patch triangle of the old TET mesh (`mesh/u666/tet_bak/`, TETREF); CAD getClosestPoint/isInside mislabelled (untrimmed planes, holed cylinders). Patch areas vs CAD within 1 % (worst pair endcaps-magnets 5.2 %, unchanged tet side).
- Cells: winding 209 k, stator 143 k, rotor 286 k, magnets 22 k, wedge 74 k (prisms) + tet regions 686 k = 1.42 M (was 4.17 M). checkMesh: stator skew 5.1 (1728 faces), wedge aspect 2255, inair skew 9.2 (unchanged).
- Volumes: slot 220.6 (CAD 221.6) cm3, stator 478.2 (477.3), rotor 245.5 (244.8), rpocket 53.2, magnets 36.5, endw 108.0.
- Run: adiabatic duty1 losses (1201 W), dt 1 s, nOuter 3, anisotropic winding (WIND_ISO unset): STABLE, no divergence.
- Balance (stored - injected)/injected: dt1/N3: -2.6 % @5 s, -5.7 % @20 s, -8.7 % @60 s; dt1/N10: -1.9 % @20 s. Series: `results/u666/s8b/ts_dt1_N3_60s.csv`, `eb_dt1_N3_60s.json` (per-interface sums in iface_W).
- Diagnosis: interface pair sums are ~0 except wedge|winding (-9 W) and stator|wedge: with STATOR_ISO=28 the stator|wedge pair loses -88 W at 20 s (stator -73 W, wedge -15 W: both sides lose). With the anisotropic stator the same loss shows as a stator internal residual (-109 W @60 s; the anisotropic explicit-T split hides it from wallHeatFlux). Cause: sliver prisms in the wedge mesh, 2-5 um high, along r 43.53 (two CAD arcs 43.530/43.535: gap ring vs slot-opening pieces / tooth tips); kappa/delta there is huge and the AMI coupling is not conservative. Union per zone, fuzzy boolean (BOOLTOL 0.03) and 2D algorithms 1/5/6 did NOT remove them.
- rho*Cv: consistent (case_props rhocv = physicalProperties; rpocket keeps air rho*Cv with rotor Cv). Region order (winding first) made no difference.
- Timing: ~1.1 s per outer iteration (4 procs, 1.42 M), setup ~80 s. dt 1/N 3: 60 s simulated in 352 s wall (incl. setup) = ~4.5 s wall per s sim (~3.3 s excl. setup); N 10 = ~11 s/s.
- Assumptions: prism sections at mid-z of each volume (rpocket piece 469 is 6 % off a prism, rotor 345/rpocket 389 1 %); wedge SIZE changed to H*0.2.

## S8c - wedge tooth-tip fix + energy gate (BASE3 agent, 2026-10-24) - GATE MET (-1.14 % at 60 s)
- Cause (probe of the mid-z sections): the wedge ring piece was annulus 43.53..44.0 minus stator, i.e. a full circle at r 43.530 (rotor side) plus 36 tooth-tip arcs at r 43.535 (4.904 mm, tips at 10k +- 3.226838 deg). Under every tip that left a 5 um x 4.9 mm strip of wedge = the sliver prisms.
- Fix (`u666_mesh.py` prism route, env TIP="43.535,3.226838,10,43.53", TIP=0 = off): wedge section = CAD wedge + slot-opening sectors with the inner arc cut at the EXACT tip radius 43.535 (disk cut); flanks / r 44 arcs stay the conformal stator curves from geo. The strip was the only rotor-stator path, so the rotor arc (r 43.53) is now split at the 72 tip angles and the tip faces become a NEW pair rotor_to_stator / stator_to_rotor (10687.5 / 10688.4 mm2, 0.009 %); rotor_to_wedge / wedge_to_rotor 5873 / 5874 mm2. The rotor-tip and wedge-rotor couplings bridge the 5 um radial offset (43.530 vs 43.535) via mapped AMI, the same as before. Not merged into the slot.
- Also fixed: fragment of a single fused section (stator) returned an empty map -> skipped when there is only 1 face.
- ASSUMPTION: wedge volume 9.61 -> 9.52 cm3 (-0.9 %, the 5 um strips removed); seal unchanged 4.91 cm3. Rotor/stator gap contact now direct (no 5 um wedge k 0.2 layer in series; that layer had R ~ 2.5e-5 m2K/W, negligible).
- Remeshed wedge (97.1 k prisms, was 74.3 k), stator (148.1 k, sections now fused: 1 face), rotor (283.9 k). Old meshes in `mesh/u666/prism_s8b/`. Logs `mesh/u666/s8c_<G>.log`. Total 1.446 M cells.
- checkMesh: stator and wedge now Mesh OK (skew 5.1 and aspect 2255 gone); only inair skew 9.2 (unchanged, tet).
- Pair area mismatch: stator_to_wedge 6269 vs 6381 mm2 (1.8 %, labelling at the CAD-wedge / tooth corner r 44.5); worst overall still endcaps_to_magnets 5.2 % (unchanged).
- Energy test, adiabatic duty1 (1201 W), dt 1 s, nOuter 3, anisotropic winding + stator: -1.05 % @5 s, -1.11 % @20 s, -1.14 % @40-60 s (plateau). Series `results/u666/s8b/ts_s8c_dt1_N3_60s.csv`, `eb_s8c_dt1_N3_60s.json`; plot `results/u666/s8b/balance_s8c_dt1_N3.png` (S8b plot: `balance_s8b_dt1_N3.png`).
- Per-region rate residuals at 60 s: stator -0.7 W (was -109 W), rotor +0.6, winding -7.0 W, others ~0.
- Interface pair sums at 60 s: stator|wedge +0.03 W of 10.9 (0.3 %), rotor|stator 0.00 of 10.4, rotor|wedge 0.00 of 5.6, stator|winding -0.72 of 662 (0.11 %), housing|stator 0.05 of 190, housing|inair 0.08 of 79. FAIL the strict 1 %: wedge|winding -1.85 of 25 W (7 %), inair|winding -1.1 of 104 (1.06 %), and sub-watt pairs (endcaps|shaft, bearings|housing, magnets|rotor, inair|rotor, 0.3-0.6 W each). All winding pairs lose on the winding side -> likely the anisotropic-winding wallHeatFlux / explicit split (as the stator showed before), together with the -7 W winding residual. Total missing ~14 W = 1.2 % of the loss.
- Gate met with N 3 at dt 1, so the dt 0.5 / more-outer test was not needed.
- Timing: 60 s sim in 352 s wall incl. ~80 s setup = 5.9 s wall per s sim (4.5 excl. setup). Note: the S8b line "352 s = 4.5 s/s incl. setup" was mis-computed (it is 5.9).

## S9 - External-air CFD (h map) (AIR agent, 2026-10-24) - h MAP NOT YET PRODUCED (run in progress, U gate not yet passed)
- Domain: box x +-330, y -330..520 (y up), z -330..420 mm, around the SIMPLIFIED housing envelope (`scripts/u666_air_mesh.py`: housing parts + cavity fillers + fin-root fill r<80.2 (0.2 mm root slots) + shaft stub r10 to z 148.85). Mounting unknown -> ASSUMED suspended, no feet/plate (logged). Motor skin 0.2913 m2.
- Mesh: gmsh HXT, S_FIN 1.8 / S_SKIN 5 / S_FAR 60 mm -> 1.229 M tets (`mesh/u666/air_hxt.msh`), min SICN 0.139, nonorth max 79 deg, 253 faces > 70. Fin gap 2.8 mm (root) to 8.8 mm (tip) is only 1.5-5 cells wide: h on fin flanks is coarse. Slivers removed: 0.1 mm box-rim step (BOX z1 -83.7), 0.2 mm boss-base step (K['BOSS_DZ']=0, air script only; knob added to housing_simple.py, default unchanged); fills() axis radius 0.01 -> 0 (axis void).
- BCs: motor T fixed 343.15 K (assumed ~70 C skin, dT 30 K, laminar), walls of the closed box at 313.15 K ambient (40 C), g (0 -9.81 0), gravity -y, shaft z horizontal. Radiation is NOT in the CFD; make_case adds eps 0.1 (bare Al) separately.
- Solver changes vs old air_case.sh (steady SIMPLE failed: T<0, FPE; KNOWN_ISSUES 12): GAMG smoother GaussSeidel (DIC coarsest crashed), localEuler pseudo-transient (maxCo 3), upwind, nonOrth 2, limitTemperature 300..345 K, laplacian corrected 0.33. Cost 8-12 s/iteration on 4 procs.
- KEY FINDING: localEuler with maxDeltaT 5 s gives a non-physical flow (domain mean 10 m/s, U max 46-49 m/s, closed or open box; aircheck gate fails). maxDeltaT 0.02 s: U max 0.24 m/s, mean 0.054 at 1.2 s (physical). Current run MDT 0.1 (case ~/cfd/u666_air, tmux s9, chunks 300/600/..., gate in script).
- Prepared, untested: `scripts/u666_air_post.py` (h = |q|/(Tw-Ta) mapped to housing/shaft defaultFaces of the base case, area-weighted means fins/end walls/body, Churchill-Chu + Elenbaas check), format = `--h-file` json of u666_make_case.py.
- Open: no h values, no correlation check yet. Expect (to verify) h_conv 3-6 W/m2K. Fallback if the run cannot pass the gate: uniform H_NAT 5 W/m2K + eps 0.1 in make_case (already default).

## S-report - live HTML report (REPORT agent, 2026-10-24)
- `python scripts/u666_report.py` regenerates `Report/U666_report.html` (method S0-S11 from this log, geometry/mesh figures, per-duty blocks, feedback table). `--no-render` skips the WSL step.
- Render step `scripts/u666_report_render.sh` (WSL, `nice -n 19`, single thread, python3 vtk + matplotlib): `geo` (cached; foamToVTK of ~/cfd/u666_base_nc, cuts z = 30 mm and y = 0) and `duty <case> <out>` (curves, contours, GIFs <= 3 MB from postProcessing; names matched by regex in `scripts/u666_report_duty.py` SURF/REGKEY).
- Duty case default `~/cfd/u666_<duty>`; override in `results/u666/report/sources.json`. Optional hand notes: `results/u666/report/observations_<duty>.md`.
- Duty path tested only on synthetic data (plane + volFieldValue names are a guess until the chain handoff names them).

## S-report2 - multi-page site (REPORT2 agent, 2026-10-24)
- `.venv\Scripts\python -I scripts/u666_site.py [--no-render]` regenerates `Report/U666_site/` (11 pages, assets/ as files, light/dark, phone width). Geometry render via `u666_report_render.sh geo` (cached, nice 19). Duty curves, peak tables and time-to-limit are read from `\wsl.localhost\...\<case>\postProcessing/<region>/<fo>/<t>/*.dat` (tested on u666_e2); case = `results/u666/report/sources.json` else `u666_<duty>`. Pending: contours, mp4, 3D viewer, air figures, per-region mesh pictures (see handoff/u666_report_handoff.md). Old single pages (u666_report*.py) are obsolete.

## S9 (final) - External-air h map (AIR agent, 2026-10-24) - DONE
- Run: localEuler maxDeltaT 0.1, 450 iterations (stopped at 450 by endTime edit). U max 0.31 m/s (p99 0.26, mean 0.085) - gate (<=5) met. Motor heat Q: 57 W @100, 35.9 @200, 32.4 @300, 35.4 @325, 34.8 @350, 34.7 @375-400, 34.5 @425, 34.6 @450 -> flat to 0.3 % over the last 100 iterations; p_rgh residual ~3e-4. Converged; no extension needed.
- Post (`u666_air_post.py`, fixed): (1) base-case geometry is in m but class thresholds in mm -> fin class was empty; now converted. (2) housing/shaft faces farther than 3 mm from the air skin (not external skin: housing 317 cm2, shaft stub 37 cm2) get h = 0 (map dist max was 23-33 mm), but they still receive radiation eps 0.1 in make_case (small error, noted). Output `~/cfd/u666_air_h.json` (+ `_summary.json`).
- Mean convective h (area-weighted, zeros included): fins 2.76 (1766 cm2), body 4.48 (858 cm2), end walls 5.44 (758 cm2), shaft stub 3.20, air-skin mean 3.95 W/m2K, total 34.6 W at dT 30 K (T_wall 70 C assumed, ambient 40 C).
- Correlation check: Churchill-Chu horizontal cylinder D159 4.64, D185 4.56; Elenbaas fin channel 4.41 (tip gap) / 0.27 (root gap). CFD air-skin mean 3.95 is -15 % vs CC; fins 2.76 is -40 % vs CC (-37 % vs Elenbaas tip) i.e. inside the 50 % limit, slightly outside 30 %; zero-h faces dilute the fin mean. Coarse fin mesh (1.5-5 cells per gap) is the likely cause.
- Dependence: h computed at dT 30 K fixed, not at the duty skin temperature (natural convection h ~ dT^0.25).

## S10 - Duty chain setup (2026-10-24)
- `scripts/u666_duty_chain.sh` (tmux `duty`): for duty1..5 builds the case `~/cfd/u666_<duty>` from `~/cfd/u666_base_nc` with `u666_make_case.py ... --h-file ~/cfd/u666_air_h.json` (losses from loadpoints_u666.json, eps 0.1, ambient/initial 40 C), dt 1 s, nOuter 3, end 300/900/1800/2700/2700 s, np 4, sequential; a failed duty does not stop the chain. Log `~/cfd/duty_chain.log`.
- Outputs per case in `postProcessing/<region>/`: T_<region> (max), Tmin_, Tavg_, Tint_ every 5 s; T_slot / T_endw / Tavgz_* (winding zones), T_magnets, T_housing; Qout_housing / Qout_shaft, Qif_*; vtk cut planes `S_<plane>_<region>/<t>/<plane>.vtk` every 10 s (T, cell values): axial_y0 (all regions), radial_stack z 29.9 mm, radial_ew_front z 75, radial_ew_rear z -15.3. Full T fields every 30 s (writeInterval 30, all durations).
- make_case edits: surfaces (OF12 syntax: type cutPlane, planeType pointAndNormal, function-level interpolationScheme cell), Tmin, 5 s probes.
- Smoke test duty1 20 s: rc 0, all outputs written (170 s wall incl. 80 s setup). Chain started 09:51:47 local (04:21:45 WSL). Estimate ~13-14 h.
- 09:55 MAIN decision (S9): the 354 cm2 of housing/shaft outer faces more than 3 mm from the air skin (fin-root fill, terminal-box interior, front shaft bore) were h=0 (adiabatic). They are now set to h 2.5 W/m2K (enclosed-cavity natural convection; radiation eps 0.1 is unchanged). The original map is ~/cfd/u666_air_h.json.h0bak. This applies from duty2 onward; duty1 (5 min) used h=0 there, which has negligible effect on a 5 min transient. CALIBRATION KNOB. The fin h (2.76) is 40 % under the correlation (fin gap only 1.5-5 cells wide); also a knob.
