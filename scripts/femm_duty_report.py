"""femm_duty.md + femm_duty.json: per duty point the dominant loss, its physical cause, CFD consequence and EM levers.
Inputs: losses_9795.json (table), femm_duty/dq_limits.json, femm_duty/field_stats.json.  python femm_duty_report.py"""
import json, math, os

R = r'C:\Users\vibhe\Downloads\OUTPUT\CFD\results'
OUT = os.path.join(R, 'femm_duty')
LS = json.load(open(os.path.join(R, 'losses_9795.json')))
DQ = json.load(open(os.path.join(OUT, 'dq_limits.json')))
FS = json.load(open(os.path.join(OUT, 'field_stats.json'))) if os.path.exists(os.path.join(OUT, 'field_stats.json')) else {}
RPM = dict(duty1=1782, duty2=2550, duty3=3637, duty4=9339, duty5=1612)
TQ = dict(duty1=37.0, duty2=26.3, duty3=20.0, duty4=3.24, duty5=12.43)
NAMES = dict(cu_dc='Cu DC', cu_ac='Cu AC', stator='stator iron', rotor='rotor iron', bearings='bearings', windage='windage')
RHO100 = 1.724e-8 * (1 + 0.003862 * 80); D_WIRE = 2.9464


def skin(f):
    return 1e3 * math.sqrt(2 * RHO100 / (2 * math.pi * f * 4e-7 * math.pi))


def fs(d, *k):
    v = FS.get(d)
    for kk in k:
        v = None if v is None else v.get(kk)
    return v


def why(d, L, op, f, dl):
    I = op['I_line']; fw = -op['id_phase_pk'] / math.hypot(op['id_phase_pk'], op['iq_phase_pk'])
    sk = skin(f)
    if d == 'duty4':
        tips = fs(d, 'B_peak_99pct_T', 'stator tooth tips (r < 56 mm)')
        return (f"Top speed, {f:.0f} Hz, at the voltage limit ({op['V_ph_pk']:.1f} of 49.4 V pk): holding 3.24 N.m needs id {op['id_phase_pk']:.0f} A pk "
                f"({100 * fw:.0f} % of the current is field-weakening d-axis current; with id = 0 the back-EMF would need {DQ['duty4']['V_same_iq_id0']:.0f} V). "
                f"So {I:.0f} A rms line flows for only 3.24 N.m (pf {DQ['duty4']['pf']:.2f}), and its slot leakage field at 778 Hz gives Cu AC {L['cu_ac']:.0f} W, "
                f"more than the DC copper ({L['cu_dc']:.0f} W): skin depth {sk:.1f} mm is now about the wire diameter {D_WIRE:.2f} mm (d/delta {D_WIRE / sk:.2f}). "
                f"Iron ({L['stator']:.0f} + {L['rotor']:.0f} W) is high because loss/kg scales with f (hysteresis) and f^2 (eddy) even though the d-axis current cuts the "
                f"main flux by {DQ['duty4']['psi_d_reduction_pct']:.0f} %" + (f"; tooth-tip B still peaks at {tips:.2f} T" if tips else '') +
                f". Bearings + windage ({L['bearings'] + L['windage']:.0f} W) are 27 % of the total.")
    if d == 'duty1':
        tb = fs(d, 'B_peak_99pct_T', 'stator tooth body')
        return (f"Low speed, high torque: {I:.0f} A rms line for 37 N.m at {f:.0f} Hz with plenty of voltage margin ({op['V_ph_pk']:.1f} of 49.4 V). "
                f"The id of {op['id_phase_pk']:.0f} A pk is MTPA (reluctance torque of the spoke rotor), not field weakening. Copper loss goes with I^2: "
                f"Cu DC {L['cu_dc']:.0f} W is {100 * L['cu_dc'] / L['total']:.0f} % of the total. Cu AC stays {L['cu_ac']:.0f} W because f is low "
                f"(skin depth {sk:.1f} mm vs wire {D_WIRE:.2f} mm, d/delta {D_WIRE / sk:.2f}), even though the slot field is the highest of all points. "
                f"Iron is {L['stator'] + L['rotor']:.0f} W" + (f" (tooth B up to {tb:.2f} T)" if tb else '') + " at only 148 Hz.")
    if d == 'duty5':
        return (f"Light load at low speed ({I:.0f} A rms, {f:.0f} Hz): every term is small. Cu DC {L['cu_dc']:.0f} W still dominates; iron {L['stator'] + L['rotor']:.0f} W "
                f"is mostly magnet-field hysteresis at {f:.0f} Hz; Cu AC {L['cu_ac']:.0f} W (d/delta {D_WIRE / sk:.2f}).")
    return (f"{I:.0f} A rms line at {f:.0f} Hz ({op['V_ph_pk']:.1f} of 49.4 V, id {op['id_phase_pk']:.0f} A pk, mostly MTPA). Cu DC {L['cu_dc']:.0f} W falls with I^2 "
            f"as torque drops while iron rises with frequency ({L['stator'] + L['rotor']:.0f} W); Cu AC {L['cu_ac']:.0f} W grows with f^2 (d/delta {D_WIRE / sk:.2f}).")


CFD = dict(
    duty1='Heat is in the winding (580 W DC + 30 W AC, slot and end-winding): hottest spot is the coil / end winding; stator iron 63 W and rotor 18 W are minor.',
    duty2='Winding still dominant (317 W) but stator iron (84 W) is significant: heat split winding > stator teeth/yoke.',
    duty3='Winding 205 W, stator iron 115 W, mechanical 46 W: heat more evenly split; teeth and yoke start to matter for the housing path.',
    duty4='Heat moves out of the copper DC term: AC copper (149 W) sits in the slot (worst near the slot opening, where leakage B is highest), stator iron 154 W in teeth/tips and yoke, rotor iron 31 W plus bearings 109 W and windage 47 W heat the rotor, shaft and bearings with poor cooling paths.',
    duty5='Low total (123 W); winding first, stator iron second. Thermally benign.')
LEVERS = dict(
    duty1='Copper area / lower resistance (fill factor, shorter end turns), magnet grade or temperature (hotter ferrite = less Br = more current), MTPA is already least-current.',
    duty2='As duty1; thinner lamination or a lower-loss grade starts to pay off.',
    duty3='Voltage margin is nearly used (47.6 V): battery sag pushes toward field weakening and more current.',
    duty4='Cu AC: stranded/litz or smaller parallel strands (loss ~ d^4 per strand), keep conductors away from the slot opening, deeper or closed slot tips; iron: 0.2-0.27 mm lamination or better grade cuts eddy (~ t^2); voltage: higher DC link or less battery sag (48 V costs +38 W, 44 V +81 W, nearly all copper); control: loss-minimising instead of MTPA trades a little copper for iron.',
    duty5='No action needed on the EM side.')


def main():
    out = {}
    md = ['# Electromagnetic load points: loss segregation and causes', '',
          'Design9795_1 copper (12-slot / 10-pole spoke ferrite, delta, 52 V, MI 0.95, winding and magnets 100 C). '
          'Loss values: FEMM-Lab (lab_model v3, 3 skew slices) from `losses_9795.json`; Motor-CAD total for comparison. '
          'Field figures: FEMM 2D, unskewed centre slice, 24 rotor positions per electrical period (3 deg mech).', '',
          '![loss segregation](loss_segregation.png)', '',
          '| point | rpm | N.m | f_el Hz | I line A rms | id/iq A pk | V pk (max 49.4) | Cu DC | Cu AC | stator Fe | rotor Fe | bearings | windage | total | Motor-CAD | dominant |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for d in RPM:
        L = LS[d]['femm_lab']; op = LS['operating'][d]['femm_lab']; f = RPM[d] * 5 / 60
        parts = {k: L[k] for k in NAMES}
        grp = {'copper (DC+AC)': L['cu_dc'] + L['cu_ac'], 'iron (stator+rotor)': L['stator'] + L['rotor'], 'mechanical': L['bearings'] + L['windage']}
        g = max(grp, key=grp.get); dom = max(parts, key=parts.get)
        out[d] = dict(rpm=RPM[d], torque_Nm=TQ[d], f_el_Hz=f, operating=op, losses_W=parts, total_W=L['total'], mcad_total_W=LS[d]['mcad_map']['total'],
                      dominant='%s %.0f W (largest single term: %s %.0f W)' % (g, grp[g], NAMES[dom], parts[dom]), dominant_group=g, dominant_term=NAMES[dom], skin_depth_mm=skin(f), wire_over_skin=D_WIRE / skin(f),
                      field_weakening_fraction=-op['id_phase_pk'] / math.hypot(op['id_phase_pk'], op['iq_phase_pk']),
                      reason=why(d, L, op, f, DQ.get(d)), cfd_consequence=CFD[d], em_levers=LEVERS[d])
        if d in FS:
            out[d]['fields_unskewed'] = FS[d]
        md.append(f"| {d} | {RPM[d]} | {TQ[d]} | {f:.0f} | {op['I_line']:.0f} | {op['id_phase_pk']:.0f}/{op['iq_phase_pk']:.0f} | {op['V_ph_pk']:.1f} | "
                  + ' | '.join('%.0f' % parts[k] for k in NAMES) + f" | **{L['total']:.0f}** | {LS[d]['mcad_map']['total']:.0f} | {g} {grp[g]:.0f} W |")
    md += ['']
    for d in RPM:
        o = out[d]
        md += [f'## {d}: {o["rpm"]} rpm, {o["torque_Nm"]} N.m, dominant {o["dominant_group"]}', '', o['reason'], '',
               f'**CFD consequence.** {o["cfd_consequence"]}', '', f'**EM levers.** {o["em_levers"]}', '']
    md += ['## Figures and animations', '',
           '- `flux_duty1.mp4`, `flux_duty4.mp4`: |B| (0-2 T) and flux lines over one electrical period, rotor turning, phase-current time marker.',
           '- `dq_limits.png`: d-q plane with the voltage ellipse at each speed and the current limit. duty1 is current/torque driven; duty4 sits on the voltage ellipse.',
           '- `iron_density_duty1_vs_duty4.png`: iron loss density (W/kg) per element from the full-cycle B waveforms with the Motor-CAD Steinmetz model.',
           '- `slot_leakage_duty1_vs_duty4.mp4`: slot leakage B at the wires over the cycle (AC copper loss ~ f^2 B^2).',
           '- `waveforms_spectrum_duty1_vs_duty4.png`: tooth, tip, yoke and rotor B waveforms with their harmonic spectra.', '']
    if FS:
        md += ['## Check: unskewed field post-processing vs the loss table', '', '| point | stator Fe | rotor Fe | Cu AC | table stator / rotor / AC |', '|---|---|---|---|---|']
        for d in ('duty1', 'duty4'):
            L = LS[d]['femm_lab']; s = FS[d]
            md.append(f"| {d} | {s['stator_iron_W']:.0f} | {s['rotor_iron_W']:.0f} | {s['cu_ac_W_unskewed']:.0f} | {L['stator']:.0f} / {L['rotor']:.0f} / {L['cu_ac']:.0f} |")
        md += ['', 'The table uses 3 skew slices and an interpolated d-q map; the figures use the centre slice only, so small differences are expected.', '']
    open(os.path.join(OUT, 'femm_duty.md'), 'w').write('\n'.join(md))
    json.dump(out, open(os.path.join(OUT, 'femm_duty.json'), 'w'), indent=1)
    print('\n'.join(md))


if __name__ == '__main__':
    main()
