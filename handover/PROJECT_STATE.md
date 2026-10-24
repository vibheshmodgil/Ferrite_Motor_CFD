# Project state (updated 2026-10-21 ~14:00 UTC)

**Phase:** the old-CAD (motor_65) study is closed. The next phase is the NEW motor CAD; the user will supply it.
**Running jobs:** none (tmux list empty; fin queue ended at 09:27 UTC).

## Completed milestones
- [x] Losses for duty1–5 from Design9795_1 (`loadpoints.json`, `results/losses_9795.*`)
- [x] FEMM per-point loss segregation and field animations (`results/femm_duty/`)
- [x] Energy-leak fix plus adiabatic test (`results/energy_test.json`)
- [x] Baseline duty1–5 at ε 0.7 (`results/duty1..5`)
- [x] Detailed geometry: mesh, energy test -0.9 %, det duty1 and duty4 (`results/detailed/`, `results/detailed_vs_baseline.*`)
- [x] Internal-air CFD for duty1 and duty4 (`results/inair_duty1`, `results/inair_duty4`; duty4 approximate)
- [x] duty4 baseline rerun at ε 0.1 (`results/duty4_eps01`, also `results/fins/baseline_eps0.1`)
- [x] Fin analytical screen (`results/fins/screen.md/json`)
- [x] End-winding front/rear analysis (`results/endwinding_asym.md`)
- [x] Report: `Report/Design9795_Duty_Thermal_CFD_Report.html` (single file, 15.8 MB) and `Report/Design9795_site/` (10 pages plus viewer3d)

## Not completed / open
- [ ] **Fin variant CFD (ring H16 p11.5)**. The external-air CFD went non-physical, so there is no result. Its meshes
      exist (`mesh/*ring_h16_p11.5*`, `~/cfd/base_fin_ring_h16_p11.5`, `~/cfd/air_ring_h16_p11.5`). The user has moved
      fin variants to the new CAD.
- [ ] The final report rebuild for the fins page was never run. It is blocked only by the missing fin result. Command:
      `.venv/Scripts/python -I scripts/make_report_duty.py` and again with `--site`.
- [ ] Mesh-independence study: never done.
- [ ] Measured bearing loss: the model uses Motor-CAD scaling.
- [ ] Old v7 cases in `~/cfd` (continuous, peak_torque, cruise, max_speed, peak_power, inair_continuous, ~6.7 GB):
      deletion was approved by the user but blocked by the permission classifier, so the user must run it.

## Last known-good checkpoints
- Base cases: `~/cfd/base_solids` (old CAD, baseline) and `~/cfd/base_detailed` (old CAD, merged copper).
- Last successful command chain: `fin_baseline_eps0.1_duty4` run plus post at 09:01 UTC → `results/duty4_eps01`, balance -0.81 %.

## Run registry (old CAD)
| case (~/cfd) | model | ε | end s | dt | balance % | results |
|---|---|---|---|---|---|---|
| duty1 | baseline | 0.7 | 477 (fields to 420) | 3 | -0.46 | results/duty1 |
| det_duty1 | detailed | 0.7 | 477 (fields deleted after post) | 3 | -0.8…+0.3 | results/detailed/duty1 |
| duty2 | baseline | 0.7 | 1350 | 10 | -0.76 | results/duty2 |
| duty3 | baseline | 0.7 | 2700 | 20 | -0.68 | results/duty3 |
| duty4 | baseline | 0.7 | 2700 | 60 | -1.16 | results/duty4 |
| det_duty4 | detailed | 0.7 | 2700 | 60 | -1.7…-2.1 ⚠ | results/detailed/duty4 |
| fin_baseline_eps0.1_duty4 | baseline | 0.1 (envelope) | 1680 | 60 | -0.81 | results/duty4_eps01 |
| duty5 | baseline | 0.7 | 4050 (fields to 4020) | 60 | -0.67 | results/duty5 |
| inair_duty1 / inair_duty4 | internal-air CFD | – | – | – | wall-q closes ~2 W of 24 W (duty4) | results/inair_* |

## Decisions (user, with dates)
- 2026-10-20: use the Design9795_1 copper design only; detailed comparison before duty2/3/5 (later approved to run all).
- 2026-10-21:
  - Charts cut at winding 180 °C; mark the m100 and w155 events.
  - The report must be a multi-page site with tabs plus a 3D viewer.
  - Detailed results are primary wherever they exist.
  - Housing is bare machined Al (ε ≈ 0.1), natural convection only, horizontal shaft.
  - Max OD 205 mm (glands may protrude). Fins tapered 4 mm base / 2.5 mm tip.
  - Detailed reruns cancelled; detailed modelling to be redone on the new CAD.
- Token economy: compact replies, agent reports of 5 lines or fewer, background waits instead of polling, one heavy job at a time.

## Approvals the user still needs to give
- None blocking. On the new CAD, confirm the material call-outs, emissivity/finish, the fin envelope, and whether to
  reuse the Design9795_1 losses unchanged (does the new CAD change stack length or slots?).
