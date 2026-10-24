# Ferrite_Motor_CFD - conjugate thermal CFD of two motors

Two pipelines share this repo:

1. **Ferrite motor** (Design9795_1 copper / "Motor65", older pipeline): 5 vehicle duty points, baseline + detailed-winding models.
2. **U666 benchmark motor** (scripts/`u666_*`): Creo CAD, 36-slot NdFeB machine with test data, newer non-conformal multi-region route.

Both: gmsh (Windows, OCC) builds the mesh, OpenFOAM 12 (WSL) runs multi-region solid CHT with `foamMultiRun`, an external natural-convection air CFD supplies the housing h map, Python scripts post-process and write HTML reports. Limits: winding 155 C, magnets 100 C, ambient 40 C, horizontal shaft (axis z, gravity -y).

## 1. Environment

| Part | Setup |
|---|---|
| Windows 11, 4+ cores, 16 GB RAM, >=20 GB free | Python venv: `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt` (gmsh 4.15.2 OCC, numpy, scipy, meshio, matplotlib, scikit-fem ...) |
| WSL2 Ubuntu-24.04, user `cfd` | OpenFOAM 12 in `/opt/openfoam12` (`source /opt/openfoam12/etc/bashrc`), `python3` with numpy/scipy/vtk (U666 report render), `rsync`, `tmux`, `ffmpeg` |
| Repo location | Scripts hardcode `C:\Users\vibhe\Downloads\OUTPUT\CFD` (= `/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD` in WSL). Clone there, or `sed` the path in `scripts/`. |
| FEMM 4.2 + pyfemm | Only to regenerate losses (`scripts/femm_duty_*.py`, Windows Python 3.10 outside the venv) |

Call WSL from Git Bash as `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u cfd -- bash ...` (default distro may be docker-desktop). Cases live in WSL `~/cfd/<case>`.
Run long jobs detached (`tmux new -d -s X '...'`); only ONE heavy job at a time (never gmsh and OpenFOAM together). Disable Windows sleep.

## 2. Folder map

| Path | Content |
|---|---|
| `scripts/` | all pipeline code (ferrite: `build_mesh*.py make_case.py run_case.sh air_case.sh map_h.py post.py make_report_duty.py ...`; U666: `u666_*`) |
| `cases/` | OpenFOAM case SETUP only (system/, constant/ minus polyMesh): `u666_base_nc u666_duty1 u666_air base_solids base_detailed duty1 det_duty1 air inair_duty1`, `ctnc` (custom BC lib build dir), `wsl_scripts/` (helpers that lived only in `~/cfd`), `u666_air_h.json`, `h_cfd*.json` (h maps) |
| `cad_ferrite/motor_65/` | ferrite motor STEP/SLDPRT parts (28 MB) |
| `U666 CAD/` | U666 Creo STEP `ge250440_step.stp` (599 solids; import takes ~18 min) |
| `mesh/` | BREP caches (`motor_detailed.brep`, `mesh/u666/u666.brep`, `subset*.brep`, `u666_geo*.brep`), region json, logs. Meshes excluded. |
| `results/` | results, figures, mp4, summaries; `results/u666/steps_log.md` = full U666 method log (S0-S11) |
| `Report/` | HTML reports and multi-page sites (`Design9795_site/`, `U666_site/`, `U666_method.html`) |
| `handover/`, `handoff/` | project state, `ENGINEERING_BASELINE.yaml`, `KNOWN_ISSUES.md`, `U666_NOTE.md`, agent handoff notes. **Read `handover/PROJECT_STATE.md` and `U666_NOTE.md` first.** |
| `loadpoints.json`, `loadpoints_u666.json`, `u666_loadpoints.json` | loss inputs (ferrite duty1-5; U666 duty1-5; U666 energy-test dummy losses) |

Loss source for ferrite: `github.com/mishravipul361-blip/Ferrite-motor-design` branch `spoke-v2-aluminium-and-design9795` (Design9795_1: `lab_100C.json`, `motorcad_losses.json`), via `scripts/loadpoints_9795.py`. Not included.

## 3. Inputs and how to change them

- **Losses**: `loadpoints.json` (ferrite; regenerate with `python scripts/loadpoints_9795.py`, check with `scripts/loss_check.py`), `loadpoints_u666.json` (U666: DC Cu at T_ref, AC Cu, iron, magnet, windage, friction per duty). Edit values and rerun `make_case`.
- **Materials**: `handover/ENGINEERING_BASELINE.yaml` (reference) and the material blocks in `scripts/make_case.py` / `scripts/u666_make_case.py`.
- **Winding properties (U666)**: `python scripts/u666_winding_props.py` -> `results/u666/winding_props.json` (Kf 0.555, k_T 1.12, k_ax 217, liner 0.25 mm as contact R 1.67e-3).
- **h map**: external air CFD -> `--h-file` json (`u666_air_h.json`, `h_cfd.json`). Fallback: uniform H_NAT 5 W/m2K.

### Calibration knobs
| Knob | Where | Default |
|---|---|---|
| `IRON_STATOR_FRAC` iron loss stator/rotor split | env, `u666_make_case.py` | 0.8 |
| `BRG_FRONT_FRAC` friction front/rear bearing | env, same | 0.5 |
| `T_REF_C` Cu DC reference temperature | env, same | 100 |
| `EMISSIVITY` (bare machined Al) | env, make_case / chain | 0.1 (old default 0.7 was wrong) |
| `ADIABATIC=1 JOULE_TC=0` energy test; `WIND_ISO=1` isotropic winding fallback | env | off |
| End-winding shell (about 5 mm at r 55.5, ~30 mm overhang) | `u666_geo.py` | calibration knob |
| Contact R, `k_gap`, `k_inair`, `h_endspace` | load-point json / make_case | see steps_log S6 |
| Housing simplification dict `K` | `scripts/u666_housing_simple.py` | vol -2 %, fin area +1 % |
| Prism route `DZ` (2.5), `EXTRUDE`, `TIP` | env, `u666_mesh.py` | see steps_log S8c |

## 4. U666 chain (exact commands)

Run from the repo root.

```
# 0  (once) STEP -> BREP cache: already in mesh/u666/u666.brep (18 min if regenerated; steps_log S1)
# 1  thermal subset
.venv/Scripts/python -I scripts/u666_subset.py            # -> mesh/u666/subset.brep (49 s)
# 2  region set; the real housing CAD does not mesh -> simplified housing
.venv/Scripts/python -I scripts/u666_housing_simple.py    # -> mesh/u666/housing_simple.brep
export U666_HOUSING=simple                                # (cmd: set U666_HOUSING=simple)
.venv/Scripts/python -I scripts/u666_geo.py               # -> mesh/u666/u666_geo.brep/.json (6-25 min)
# 3  mesh each region alone, prism route (solids)
for g in housing inair stator winding wedge rotor magnets endcaps shaft bearings; do
  .venv/Scripts/python -I scripts/u666_mesh.py --solids --group $g    # -> mesh/u666/u666_g_$g.msh
done
# 4  assemble the non-conformal multi-region base case (WSL)
bash scripts/u666_build_ctnc.sh          # builds libcoupledTemperatureNC (source generated by the script; cases/ctnc is a copy)
bash scripts/u666_assemble_nc.sh         # -> ~/cfd/u666_base_nc ; then checkMesh -region <r>
# 5  adiabatic energy test, gate +-1.5 % (was -1.14 % at 60 s)
BASE=~/cfd/u666_base_nc bash scripts/u666_energy_test.sh
# 6  external natural-convection air (h map)
.venv/Scripts/python -I scripts/u666_air_mesh.py          # -> mesh/u666/u666_air_s.msh
bash scripts/u666_air_case.sh mesh/u666/u666_air_s.msh    # ~/cfd/u666_air ; gate U max <= 5 m/s: bash scripts/u666_aircheck.sh
python3 scripts/u666_air_post.py ~/cfd/u666_air <time> ~/cfd/u666_base_nc ~/cfd/u666_air_h.json
# 7  duty chain duty1..5 (300/900/1800/2700/2700 s, dt 1, nOuter 3, 4 MPI ranks), detached
tmux new -d -s duty 'bash scripts/u666_duty_chain.sh'     # SMOKE=1 for a 20 s check; H=<h json>
# 8  report
.venv/Scripts/python -I scripts/u666_site.py              # -> Report/U666_site/
.venv/Scripts/python -I scripts/u666_method_report.py     # -> Report/U666_method.html
```
Single case by hand: `python3 scripts/u666_make_case.py ~/cfd/u666_base_nc ~/cfd/u666_duty1 duty1 --h-file ~/cfd/u666_air_h.json`, then `decomposePar -allRegions; mpirun -np 4 foamMultiRun -parallel`.
Status at handover: steps 1-5 done (gate met), step 6 h map not yet passing the U gate (`results/u666/steps_log.md` S9), duty runs and test calibration pending (test data not yet supplied). Placeholders for open inputs are listed in `handover/U666_NOTE.md`.

## 5. Ferrite motor chain

```
# CAD: cad_ferrite/motor_65 (set env CAD=<path>; scripts default to C:\...\OUTPUT\OUTPUT\cad\motor_65)
.venv/Scripts/python -I scripts/loadpoints_9795.py                 # loss inputs -> loadpoints.json
.venv/Scripts/python -I scripts/build_mesh.py                      # mesh/motor_solids.msh + air.msh (--solids-only: no air)
.venv/Scripts/python -I scripts/build_mesh_detailed.py             # mesh/motor_detailed.msh (real coils/resin)
# WSL
bash scripts/prep_base.sh mesh/motor_solids.msh ~/cfd/base_solids
MERGE_CU=1 bash scripts/prep_base.sh mesh/motor_detailed.msh ~/cfd/base_detailed
bash scripts/air_case.sh mesh/air.msh ; bash scripts/aircheck.sh   # external air -> ~/cfd/air
#   h map: foamPostProcess -func writeCellCentres, then python3 scripts/map_h.py ~/cfd/air <t> ~/cfd/base_solids ~/cfd/h_cfd.json
bash scripts/energy_test.sh <name>                                 # adiabatic test (baseline -0.4..-0.8 %)
HFILE=~/cfd/h_cfd.json bash scripts/run_case.sh duty1              # duty2..5 likewise; env PREFIX/SUFFIX/BASE/NP/WRITE
bash scripts/duty_runs.sh ; bash scripts/pipeline.sh               # old orchestration scripts (read before use)
.venv/Scripts/python -I scripts/post.py results/duty1              # time-to-limit
bash scripts/export3d.sh solid <case> <t>                          # 3D VTK for the viewer
.venv/Scripts/python -I scripts/make_report_duty.py                # -> Report/Design9795_*  (add --site for the site)
```
`cases/` holds templates: `make_case.py <base> <case> <loadpoint>` regenerates a case from a base; `cases/duty1`, `det_duty1` show the output. Open items (`handover/PROJECT_STATE.md`): fin-variant air CFD went non-physical (KNOWN_ISSUES 12); mesh-independence study not done.

## 6. Excluded files and how to regenerate

| Excluded | Why | Regenerate |
|---|---|---|
| `.venv/`, `__pycache__/`, `.claude`, symlink `S`, `U666 CAD.zip` (copy of the STEP) | environment / duplicates | `pip install -r requirements.txt` |
| `mesh/*.msh` (motor_solids, motor_detailed, air, ring_h16 variants; ~1.2 GB) | size | gmsh scripts, sections 4/5 |
| `mesh/u666/*.msh` (u666_g_*, u666_air_s, air_hxt, tet_bak, prism_s8b) | size | `u666_mesh.py --solids --group G`, `u666_air_mesh.py` |
| `mesh/u666/stl/*.stl` (550 MB) | snappy route, abandoned | `u666_mesh.py --solids --stl` |
| `results/**/*.vtk` (1.9 GB 3D fields) | size | `scripts/export3d.sh` on rerun cases (report sites embed what they need) |
| OpenFOAM `polyMesh/`, time dirs, `processor*`, `postProcessing` | solver output | `prep_base.sh`, `u666_assemble_nc.sh`, run scripts |
| `ferrite_repo` (loss design source) | separate repo | clone, see section 2 |

No kept file is over 95 MB (largest 48 MB); no Git LFS. A secrets scan found nothing.

## 7. Known pitfalls
Full table: `handover/KNOWN_ISSUES.md`. Most important:
- foamMultiRun region coupling lost ~49 % of heat with 1-2 outer correctors; use outerCorrectorResidualControl and nOuter >= 3, and pass the adiabatic energy test first.
- Merge coil/strap/busbar into one `copper` region (`MERGE_CU=1`) for the detailed ferrite model.
- Never fuse the U666 housing (OCC fails). Real housing CAD defeature/snappy all failed: use `U666_HOUSING=simple`. If a PLC error returns, cut the endcaps by the shaft before the fragment.
- Stack and rotor are ONE lamination profile extruded; do not fuse laminations.
- Use Delaunay 3D from the saved BREP (HXT gives "duplicate volume" on the ferrite mesh); gmsh single thread.
- Air CFD: steady SIMPLE diverges; use localEuler with small maxDeltaT (0.02-0.1 s) and the aircheck gate (U max <= 5 m/s).
- Writes and endTime must be multiples of dt (else empty slices). Keep `objects ();` on monitors; watch disk (C: filled once; WSL error `getpwnam failed`).
- Emissivity 0.7 on bare Al was wrong, use 0.1. Agent background shells get reaped under RAM pressure: use tmux or Start-Process.
- `pkill -f` can kill its own shell; use tmux kill-session.
- Keep line endings LF (`.gitattributes` disables conversion); CRLF breaks the WSL shell scripts.

## 8. Hardware and timings (4-core laptop, 15.8 GB RAM, WSL VM 9.9 GB)
STEP import 18 min (use the BREP cache); `u666_subset` 49 s; `u666_geo` 6-25 min; U666 base 1.45 M cells, duty sim ~5.9 s wall per simulated second on 4 ranks (duty chain roughly 5 h); air CFD 8-12 s/iteration (1.2 M tets); ferrite duty1 477 s sim, duty5 4050 s sim at dt 3-60 s.
