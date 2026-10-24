"""Figures for the 'Electromagnetic load points' section (Design9795_1 copper, 52 V, 100 C).
python femm_duty_post.py losses        loss segregation bar chart (from losses_9795.json, no FEMM)
python femm_duty_post.py dq            d-q operating points on the voltage / current limits (lab_model, no FEMM)
python femm_duty_post.py fields duty1  flux / iron-density / slot-leakage frames + waveforms from raw_duty1.npz
"""
import json, math, os, sys
REPO = r'C:\Users\vibhe\Downloads\OUTPUT\ferrite_repo\repo\Design9795_1'
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ['MAG_T'] = '100'
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.tri as mtri

OUT = r'C:\Users\vibhe\Downloads\OUTPUT\CFD\results\femm_duty'
LOSSES = json.load(open(r'C:\Users\vibhe\Downloads\OUTPUT\CFD\results\losses_9795.json'))
DUTIES = ['duty1', 'duty2', 'duty3', 'duty4', 'duty5']
RPM = dict(duty1=1782, duty2=2550, duty3=3637, duty4=9339, duty5=1612)
TQ = dict(duty1=37.0, duty2=26.3, duty3=20.0, duty4=3.24, duty5=12.43)
CATS = [('cu_dc', 'Cu DC'), ('cu_ac', 'Cu AC'), ('stator', 'Stator iron'), ('rotor', 'Rotor iron'), ('bearings', 'Bearings'), ('windage', 'Windage')]
COL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#6250d6']    # dataviz reference palette, fixed order
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
                     'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': 'white'})


def save(fig, name):
    p = os.path.join(OUT, name); fig.savefig(p, dpi=130, facecolor='white'); plt.close(fig); print('wrote', p)
    return p


# ------------------------------------------------------------------ 1. loss segregation
def losses():
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = np.arange(len(DUTIES))
    for i, d in enumerate(DUTIES):
        b = 0
        for (k, lab), c in zip(CATS, COL):
            v = LOSSES[d]['femm_lab'][k]
            ax.bar(i, v, 0.6, bottom=b, color=c, edgecolor='white', linewidth=2, label=lab if i == 0 else None)
            if v > 25:
                ax.text(i, b + v / 2, '%.0f' % v, ha='center', va='center', fontsize=8, color='white' if k in ('cu_dc', 'rotor', 'windage') else INK)
            b += v
        mc = LOSSES[d]['mcad_map']['total']
        ax.plot([i - 0.38, i + 0.38], [mc, mc], color=INK, lw=2)
        ax.text(i, max(b, mc) + 12, 'FEMM %.0f W\nMotor-CAD %.0f W' % (b, mc), ha='center', va='bottom', fontsize=8, color=INK)
    ax.plot([], [], color=INK, lw=2, label='Motor-CAD total')
    ax.set_xticks(x, ['%s\n%d rpm, %.2f N.m' % (d, RPM[d], TQ[d]) for d in DUTIES])
    ax.set_ylabel('Loss (W)'); ax.set_ylim(0, 860); ax.yaxis.grid(color=GRID); ax.set_axisbelow(True)
    ax.set_title('Design9795_1 loss segregation at the duty points (FEMM-Lab, 52 V, winding and magnets 100 C)', fontsize=11, loc='left')
    ax.legend(ncol=7, fontsize=8, frameon=False, loc='upper right', bbox_to_anchor=(1, 1.0))
    fig.tight_layout(); save(fig, 'loss_segregation.png')


# ------------------------------------------------------------------ 3c. d-q limits
def dq():
    import lab_map as L, lab_model as LM
    mdl = LM.Model(loss='v3', slices=(-2, 0, 2), torque='flux')
    ip = np.linspace(-L.I_PATH_PK, 0, 181); iq = np.linspace(0, L.I_PATH_PK, 181)
    D, Q = np.meshgrid(ip, iq)
    out = {}
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, d in zip(axs, ('duty1', 'duty4')):
        n = RPM[d]
        R = mdl.evaluate(n, D.ravel(), Q.ravel())
        V = R['Voltage_Phase_Peak'].reshape(D.shape); T = R['Shaft_Torque'].reshape(D.shape)
        inside = np.hypot(D, Q) <= L.I_PATH_PK
        Vm = np.where(inside, V, np.nan); Tm = np.where(inside, T, np.nan)
        cs = ax.contourf(2 * D, 2 * Q, Vm, levels=np.arange(0, 105, 7), cmap='Blues', alpha=0.55, extend='max')
        ax.contour(2 * D, 2 * Q, Vm, levels=[L.V_MAX], colors=['#e34948'], linewidths=2)
        tc = ax.contour(2 * D, 2 * Q, Tm, levels=[5, 10, 20, 30, 40], colors=INK2, linewidths=0.8, linestyles='--')
        ax.clabel(tc, fmt='%g N.m', fontsize=7)
        ax.contour(2 * D, 2 * Q, Tm, levels=[TQ[d]], colors=INK, linewidths=1.6)
        a = np.linspace(0, math.pi / 2, 100)
        ax.plot(-2 * L.I_PATH_PK * np.sin(a), 2 * L.I_PATH_PK * np.cos(a), color='#6250d6', lw=2)
        op = LOSSES['operating'][d]['femm_lab']
        ax.plot(op['id_phase_pk'], op['iq_phase_pk'], 'o', ms=10, color='#eb6834', mec='white', mew=2, zorder=5)
        # voltage at the same torque with id = 0 (no field weakening): the flux the magnets alone would induce
        r0 = mdl.operate(n, [TQ[d]], G=(np.zeros(400), np.linspace(0, L.I_PATH_PK, 400)))[0]
        rop = mdl.evaluate(n, np.array([op['id_phase_pk'] / 2]), np.array([op['iq_phase_pk'] / 2]))
        rid0 = mdl.evaluate(n, np.array([0.0]), np.array([op['iq_phase_pk'] / 2]))
        psi_m = float(mdl.evaluate(n, np.array([0.0]), np.array([0.0]))['Flux_Linkage_D'][0])
        I = math.hypot(op['id_phase_pk'], op['iq_phase_pk'])
        out[d] = dict(rpm=n, f_el=n * 5 / 60, V_op=float(rop['Voltage_Phase_Peak'][0]), V_max=L.V_MAX,
                      V_same_iq_id0=float(rid0['Voltage_Phase_Peak'][0]),
                      id0_reachable=r0 is not None, V_id0_at_torque=None if r0 is None else r0['Voltage_Phase_Peak'],
                      psi_m_mWb=psi_m, psi_d_mWb=float(rop['Flux_Linkage_D'][0]), psi_q_mWb=float(rop['Flux_Linkage_Q'][0]),
                      fw_fraction_id_over_I=-op['id_phase_pk'] / I, gamma_deg=math.degrees(math.atan2(-op['id_phase_pk'], op['iq_phase_pk'])),
                      psi_d_reduction_pct=100 * (1 - float(rop['Flux_Linkage_D'][0]) / psi_m), pf=float(rop['Power_Factor'][0]))
        ax.annotate('%s  id %.0f, iq %.0f A pk\n|V| %.1f of %.1f V; with id = 0: %.0f V' % (d, op['id_phase_pk'], op['iq_phase_pk'], out[d]['V_op'], L.V_MAX, out[d]['V_same_iq_id0']),
                    (op['id_phase_pk'], op['iq_phase_pk']), (0.03, 0.04), textcoords='axes fraction', fontsize=8.5,
                    arrowprops=dict(arrowstyle='->', color=INK2), bbox=dict(fc='white', ec=GRID))
        ax.set(xlabel='i_d phase peak (A)', ylabel='i_q phase peak (A)', aspect='equal')
        ax.set_title('%s: %d rpm (%.0f Hz), %.2f N.m' % (d, n, n * 5 / 60, TQ[d]), loc='left', fontsize=10)
    axs[0].plot([], [], color='#e34948', lw=2, label='voltage limit 49.4 V pk (52 V, MI 0.95)')
    axs[0].plot([], [], color='#6250d6', lw=2, label='current limit 360 A rms line')
    axs[0].plot([], [], color=INK, lw=1.6, label='required torque')
    axs[0].legend(fontsize=7.5, loc='upper left', frameon=True)
    fig.colorbar(cs, ax=axs, shrink=0.8, label='phase voltage peak at this speed (V)')
    fig.suptitle('Why duty4 field-weakens: d-q plane with the voltage ellipse at each speed (FEMM d-q map, skew 3 slices)', x=0.02, ha='left', fontsize=11)
    save(fig, 'dq_limits.png')
    json.dump(out, open(os.path.join(OUT, 'dq_limits.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    globals()[sys.argv[1]](*sys.argv[2:])
