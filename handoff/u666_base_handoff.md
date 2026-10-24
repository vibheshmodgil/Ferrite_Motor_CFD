# U666 base case (2026-10-24): h map DONE, duty chain RUNNING (started 09:51 local, ~13-14 h)
Details: results/u666/steps_log.md S8c (energy gate -1.14 %), S9 (h map), S10 (chain).

## State
- Base `~/cfd/u666_base_nc` (1.446 M cells). Air h map `~/cfd/u666_air_h.json` (+ `_summary.json`): fins 2.76, body 4.48, end walls 5.44, shaft 3.20 W/m2K (convective; eps 0.1 added in make_case). U max 0.31 m/s.
- Chain: tmux `duty` runs `scripts/u666_duty_chain.sh` (duty1..5, 5/15/30/45/45 min, dt 1 s, nOuter 3, 4.5 s wall per s sim). Do not start another heavy job meanwhile.

## Monitor (WSL Ubuntu-24.04, user cfd)
- Progress: `cat ~/cfd/duty_chain.log` (START/END per duty, rc); `grep "^Time =" ~/cfd/u666_duty<i>/log.run | tail -1`.
- Never `pkill -f foamMultiRun`. To stop the chain: `tmux kill-session -t duty` then kill the mpirun (pid).
- Failed duty: log says FAILED and the chain continues with the next one; rerun one by hand with the `run` function logic in the script.

## Outputs (per case ~/cfd/u666_duty<i>/)
- `postProcessing/<region>/T_<region>` (max), `Tmin_`, `Tavg_`, `Tint_` (5 s); winding zones `T_slot`, `T_endw`, `Tavgz_*`; `T_magnets`, `T_housing`; `Qout_housing`, `Qout_shaft` (heat to ambient), `Qif_*`. File: `<dir>/0/volFieldValue.dat` (or wallHeatFlux.dat).
- Cut planes (vtk, cell T, every 10 s): `postProcessing/<region>/S_<plane>_<region>/<t>/<plane>.vtk`, planes axial_y0, radial_stack (z 29.9 mm), radial_ew_front (z 75), radial_ew_rear (z -15.3). Combine regions in ParaView.
- Full-field T written every 30 s (time dirs, per region, processorN until reconstructed): for 3D animation use `reconstructPar -allRegions` per case.
- Limits: winding 155 C, magnets 100 C.

## Caveats
- h map made at dT 30 K (T_wall 70 C); fins -40 % vs Churchill-Chu (inside 50 % gate); faces >3 mm from the air skin (housing 317 cm2) have h = 0 but still radiate.
- Placeholders: iron split 0.8/0.2, T_REF 100 C, mounting suspended (no feet).
- Energy gate residual -1.1 % (winding interface pairs lose ~14 W); see S8c.

## WSL gotchas
- Export `MSYS_NO_PATHCONV=1`; use script files for WSL commands (no inline $ vars). Foreground waits max ~590 s per tool call.
- Check `tmux ls` first after a WSL restart. Windows python = `py`/Python310, not `python3`.
- Harmless "Duplicate entry ... turbulentTemperatureCoupledBaffleMixed" stack prints at start of foamMultiRun.
