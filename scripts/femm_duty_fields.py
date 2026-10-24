"""Field figures/animations from results/femm_duty/raw_<duty>.npz (made by femm_duty_solve.py).
python femm_duty_fields.py flux duty1    rotating |B| + flux-line animation (one electrical period, shown twice)
python femm_duty_fields.py compare       iron-loss density maps, B waveforms + spectra, slot-leakage animation, field_stats.json
python femm_duty_fields.py snap duty2    static |B| snapshot (no animation) for the other points
"""
import json, math, os, shutil, subprocess, sys
from femm_duty_post import OUT, TQ, INK, INK2, GRID, save, np, plt, mtri   # also sets sys.path / cwd to the repo
import lab_map as L

KH, KE, ALPHA, BF = L.KH, L.KE, L.ALPHA, L.BF
KC = L.LOSS['iron_loss']['Kc_minor_loop']
RB, R_BORE = 71.1519, 53.5          # slot-bottom and bore radius, mm (backemf.slot_geometry)


def load(duty):
    z = dict(np.load(os.path.join(OUT, 'raw_%s.npz' % duty)))
    xy, tri, mat = z['xy'], z['tri'], z['mat']
    rot_node = np.hypot(xy[:, 0], xy[:, 1]) < float(z['r_age_in']) + 1e-6
    c = xy[tri].mean(1); r_e = np.hypot(c[:, 0], c[:, 1])
    rot_el = rot_node[tri].all(1)
    n = len(z['th']); NPC = 2 * n
    ang = np.arctan2(c[:, 1], c[:, 0])               # element field in its own polar axes (rotor mesh fixed in rotor axes)
    Br = z['Bx'] * np.cos(ang) + z['By'] * np.sin(ang); Bt = -z['Bx'] * np.sin(ang) + z['By'] * np.cos(ang)
    W = np.stack([Br, Bt], 1).astype(float)          # (n, 2, nel), half a period
    # second half (as iron_loss_age.py): stator B(x, th+36) = -B(x, th); rotor element p -> -(element at p turned +36 deg)
    from scipy.spatial import cKDTree
    ridx = np.flatnonzero(rot_el); a = math.radians(36.0)
    px = c[ridx, 0] * math.cos(a) - c[ridx, 1] * math.sin(a); py = c[ridx, 0] * math.sin(a) + c[ridx, 1] * math.cos(a)
    rsg = np.ones(len(px)); lo = py < 0; px[lo], py[lo] = -px[lo], -py[lo]; rsg[lo] = -1   # image below the half-model cut
    _, nn = cKDTree(c[ridx]).query(np.column_stack([px, py]))
    second = -W
    second[:, :, ridx] = -W[:, :, ridx[nn]] * rsg
    Wf = np.concatenate([W, second], 0)
    mass = z['area'] * 2 * 64e-3 * 0.97 * 7650       # x2 half model; stack 64 mm, stacking 0.97, 7650 kg/m3
    return dict(z=z, xy=xy, tri=tri, mat=mat, c=c, r_e=r_e, rot_node=rot_node, rot_el=rot_el, n=n, NPC=NPC, Wf=Wf,
                f=float(z['rpm']) * 5 / 60, mass=mass)


def iron_density(D):
    """lab_model v3 ('ml'): hysteresis Kh f Bpk^a (1 + Kc minor/Bpk) per component, eddy sum_n 2 pi^2 Ke (n f)^2 B_n^2, x1.6."""
    B, f, NPC = D['Wf'], D['f'], D['NPC']
    steel = D['mat'] == 3
    Bn = np.abs(np.fft.rfft(B, axis=0)) / NPC * 2
    nh = np.arange(Bn.shape[0])[:, None, None]
    E = (2 * math.pi ** 2 * KE * (nh[1:] * f) ** 2 * Bn[1:] ** 2).sum((0, 1))
    Bpk = np.abs(B - B.mean(0)).max(0)
    tv = np.abs(np.diff(np.concatenate([B, B[:1]], 0), axis=0)).sum(0)
    k = 1 + KC * np.maximum(tv - 4 * Bpk, 0) / 2 / np.maximum(Bpk, 1e-6)
    H = (KH * f * Bpk ** ALPHA * k).sum(0)
    return BF * (H + E) * steel, BF * H * steel


def regions(D):
    st = (D['mat'] == 3) & ~D['rot_el']; rt = (D['mat'] == 3) & D['rot_el']; r = D['r_e']
    return {'stator tooth tips (r < 56 mm)': st & (r < R_BORE + 2.5), 'stator tooth body': st & (r >= R_BORE + 2.5) & (r < RB),
            'stator yoke': st & (r >= RB), 'rotor pole face (r > 50 mm)': rt & (r > 50),
            'rotor pole body': rt & (r >= 20) & (r <= 50), 'rotor inner bridges/hub (r < 20 mm)': rt & (r < 20)}


def frame_xy(D, th):
    """Nodes with the rotor turned to its real angle (half-model rotor drawn at ROT_OFF) + the point-mirrored half."""
    xy = D['xy'].copy(); a = math.radians(th - float(D['z']['rot_off'])); m = D['rot_node']
    x, y = xy[m, 0].copy(), xy[m, 1].copy()
    xy[m, 0], xy[m, 1] = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return mtri.Triangulation(np.r_[xy[:, 0], -xy[:, 0]], np.r_[xy[:, 1], -xy[:, 1]], np.r_[D['tri'], D['tri'] + len(xy)])


def frame(D, k):
    """Frame k of the full period -> (solution index, sign of A, true rotor angle)."""
    n = D['n']; j = k % n
    return j, (1 if k < n else -1), float(D['z']['th'][j]) + (0 if k < n else 36.0)


def mp4(out, files, fps):
    subprocess.run([r'C:\Users\vibhe\Downloads\OUTPUT\CFD\.venv\Scripts\python.exe', '-I',
                    r'C:\Users\vibhe\Downloads\OUTPUT\CFD\scripts\frames2mp4.py', out, str(fps), '1', '0'] + files * 2, check=True)


def flux(duty, animate=True):
    D = load(duty); z = D['z']
    fr = os.path.join(OUT, 'frames_flux_%s' % duty); os.makedirs(fr, exist_ok=True)
    Bmag = np.hypot(z['Bx'], z['By'])
    Amax = float(np.abs(z['A']).max()); lev = np.linspace(-Amax, Amax, 41)
    te = np.linspace(0, 360, 361)
    I = [2 * (float(z['id']) * np.cos(np.radians(te) + p) - float(z['iq']) * np.sin(np.radians(te) + p)) for p in z['phi']]
    files = []
    for k in (range(D['NPC']) if animate else [0]):
        j, s, th = frame(D, k)
        tr = frame_xy(D, float(z['th'][j]))
        fig = plt.figure(figsize=(8.4, 7.4))
        ax = fig.add_axes([0.0, 0.0, 0.8, 0.88])
        pc = ax.tripcolor(tr, facecolors=np.r_[Bmag[j], Bmag[j]], cmap='turbo', vmin=0, vmax=2.0, rasterized=True)
        ax.tricontour(tr, s * np.r_[z['A'][j], -z['A'][j]], levels=lev, colors='k', linewidths=0.35)
        a0 = math.radians(th - 90)
        ax.plot(37 * math.cos(a0), 37 * math.sin(a0), 'o', ms=7, mfc='white', mec='k')   # marks one magnet
        ax.set_aspect('equal'); ax.axis('off'); ax.set_xlim(-81, 81); ax.set_ylim(-81, 81)
        cax = fig.add_axes([0.83, 0.12, 0.025, 0.45]); fig.colorbar(pc, cax=cax, label='|B| (T)')
        ia = fig.add_axes([0.80, 0.68, 0.18, 0.14])
        for ii, cc, nm in zip(I, ('#2a78d6', '#eb6834', '#1baf7a'), ('Ph1', 'Ph2', 'Ph3')):
            ia.plot(te, ii, color=cc, lw=1.2, label=nm)
        ia.axvline((5 * th) % 360, color='k', lw=1.2)
        ia.set_xlim(0, 360); ia.set_xticks([0, 180, 360]); ia.tick_params(labelsize=6)
        ia.set_title('phase current (A pk) vs deg el', fontsize=7); ia.legend(fontsize=5, loc='lower left', ncol=3, frameon=False)
        fig.text(0.02, 0.955, '%s  %d rpm, %.2f N.m, %.0f Hz;  id %.0f / iq %.0f A pk phase;  rotor %.1f deg mech = %.0f deg el' % (
            duty, z['rpm'], TQ[duty], D['f'], 2 * z['id'], 2 * z['iq'], th, 5 * th), fontsize=9.5)
        fig.text(0.02, 0.925, 'Design9795_1, FEMM 2D, magnets + winding 100 C, unskewed; black = flux lines; white dot = one magnet', fontsize=8, color=INK2)
        p = os.path.join(fr, 'f%03d.png' % k); fig.savefig(p, dpi=100, facecolor='white'); plt.close(fig); files.append(p)
    if animate:
        mp4(os.path.join(OUT, 'flux_%s.mp4' % duty), files, 12)
    shutil.copy(files[0], os.path.join(OUT, 'flux_%s_frame0.png' % duty))


def stats(duty):
    D = load(duty); z = D['z']
    wkg, hyst = iron_density(D); Wel = wkg * D['mass']
    reg = regions(D)
    cu = D['mat'] == 2
    Bm = np.hypot(D['Wf'][:, 0], D['Wf'][:, 1])
    cuB2 = float(np.mean((Bm[:, cu] ** 2 * z['area'][cu]).sum(1) / z['area'][cu].sum()))
    rho = L.RHO20 * (1 + L.ALPHA_CU * (L.T_WDG - 20)); w = 2 * math.pi * D['f']
    pac = L.AC_ADJ * L.N_COND * math.pi * 64e-3 * L.D_CU ** 4 * w ** 2 * 2 * cuB2 / (128 * rho)   # lab_model formula
    delta = math.sqrt(2 * rho / (w * 4e-7 * math.pi))
    st = (D['mat'] == 3) & ~D['rot_el']; rt = (D['mat'] == 3) & D['rot_el']
    Ipk = math.hypot(float(z['id']), float(z['iq']))
    return dict(rpm=int(z['rpm']), f_el_Hz=D['f'], id_phase_pk=2 * float(z['id']), iq_phase_pk=2 * float(z['iq']),
                I_line_rms=Ipk * 2 * math.sqrt(3) / math.sqrt(2), T_mean_unskewed=float(np.mean(z['T'])), T_ripple_pkpk_unskewed=float(np.ptp(z['T'])),
                stator_iron_W=float(Wel[st].sum()), rotor_iron_W=float(Wel[rt].sum()),
                hysteresis_share_pct=float(100 * (hyst * D['mass']).sum() / Wel.sum()),
                iron_by_region_W={k: float(Wel[m].sum()) for k, m in reg.items()},
                iron_density_by_region_W_per_kg={k: float(Wel[m].sum() / D['mass'][m].sum()) for k, m in reg.items()},
                B_peak_99pct_T={k: float(np.percentile(Bm.max(0)[m], 99)) for k, m in reg.items()},
                cu_B_rms_T=math.sqrt(cuB2), cu_ac_W_unskewed=pac, skin_depth_mm=1e3 * delta, wire_mm=1e3 * L.D_CU,
                wire_over_skin_depth=L.D_CU / delta), D, wkg


PROBES = {'tooth body': (62.8, 105.0, 0), 'tooth tip': (54.0, 116.0, 0), 'yoke (behind slot)': (75.6, 120.0, 0),
          'rotor pole face': (52.3, 54.0, 1), 'rotor inner bridge': (18.5, 36.0, 1)}


def probe_idx(D, r, a, rotor):
    m = (D['mat'] == 3) & (D['rot_el'] if rotor else ~D['rot_el'])
    k = np.flatnonzero(m); p = np.array([r * math.cos(math.radians(a)), r * math.sin(math.radians(a))])
    return k[np.argmin(np.hypot(*(D['c'][k] - p).T))]


def waveforms(S):
    out = {}
    fig, axs = plt.subplots(len(PROBES), 2, figsize=(12, 2.0 * len(PROBES)), gridspec_kw=dict(width_ratios=[1.6, 1]))
    for row, (name, (r, a, rotor)) in enumerate(PROBES.items()):
        for d, col, dx in (('duty1', '#2a78d6', -0.2), ('duty4', '#eb6834', 0.2)):
            D = S[d][1]; k = probe_idx(D, r, a, rotor)
            B = D['Wf'][:, :, k]; te = np.arange(D['NPC']) * 360 / D['NPC']
            axs[row, 0].plot(np.r_[te, 360], np.r_[B[:, 0], B[0, 0]], '-', color=col, lw=1.6, label='%s radial' % d)
            axs[row, 0].plot(np.r_[te, 360], np.r_[B[:, 1], B[0, 1]], ':', color=col, lw=1.6, label='%s tangential' % d)
            Bn = np.abs(np.fft.rfft(B, axis=0)) / D['NPC'] * 2; h = np.hypot(Bn[:, 0], Bn[:, 1])
            axs[row, 1].bar(np.arange(1, len(h)) + dx, h[1:], 0.4, color=col, label=d)
            out.setdefault(d, {})[name] = dict(B_peak=float(np.abs(B).max()), harmonics_T={int(o): float(h[o]) for o in range(1, min(len(h), 24)) if h[o] > 0.01})
        axs[row, 0].set_ylabel('%s\nB (T)' % name, fontsize=9); axs[row, 0].grid(color=GRID); axs[row, 0].set_xlim(0, 360)
        axs[row, 1].set_yscale('log'); axs[row, 1].set_ylim(3e-3, 3); axs[row, 1].set_xlim(0, 24); axs[row, 1].grid(color=GRID)
    axs[0, 0].legend(fontsize=7, ncol=2, loc='upper right'); axs[0, 1].legend(fontsize=7)
    axs[-1, 0].set_xlabel('electrical angle (deg)')
    axs[-1, 1].set_xlabel('harmonic order n (frequency n x 148 Hz duty1, n x 778 Hz duty4)')
    axs[0, 0].set_title('B over one electrical period (solid radial, dotted tangential)', fontsize=10, loc='left')
    axs[0, 1].set_title('|B_n| amplitude (T, log)', fontsize=10, loc='left')
    fig.tight_layout(); save(fig, 'waveforms_spectrum_duty1_vs_duty4.png')
    return out


def density_maps(S, res):
    from matplotlib.colors import LogNorm
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.6))
    for ax, d in zip(axs, ('duty1', 'duty4')):
        D, wkg = S[d][1], S[d][2]
        tr = frame_xy(D, 0.0)
        steel = np.r_[D['mat'], D['mat']] == 3
        tr.set_mask(~steel)
        pc = ax.tripcolor(tr, facecolors=np.maximum(np.r_[wkg, wkg], 0.5), cmap='inferno', norm=LogNorm(1, 400), rasterized=True)
        ax.set_facecolor('#d9d8d4'); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.set_xlim(-81, 81); ax.set_ylim(-81, 81)
        r = res[d]; g = r['iron_density_by_region_W_per_kg']
        ax.set_title('%s  %d rpm, %.0f Hz:  stator %.0f W, rotor %.0f W (hysteresis %.0f %%)\nW/kg: tips %.0f, teeth %.0f, yoke %.0f, rotor face %.0f, hub %.1f' % (
            d, r['rpm'], r['f_el_Hz'], r['stator_iron_W'], r['rotor_iron_W'], r['hysteresis_share_pct'], g['stator tooth tips (r < 56 mm)'],
            g['stator tooth body'], g['stator yoke'], g['rotor pole face (r > 50 mm)'], g['rotor inner bridges/hub (r < 20 mm)']), fontsize=9.5, loc='left')
    fig.colorbar(pc, ax=axs, shrink=0.7, label='iron loss density incl. build factor 1.6 (W/kg, log scale)')
    fig.suptitle('Where the iron loss sits: Motor-CAD Steinmetz (Kh 0.02533, alpha 2.07, Keddy 2.199e-6, minor loops) on the FEMM B(t) of every element',
                 x=0.02, ha='left', fontsize=10.5)
    save(fig, 'iron_density_duty1_vs_duty4.png')


def slot_anim(S, res):
    fr = os.path.join(OUT, 'frames_slot'); os.makedirs(fr, exist_ok=True); files = []
    for k in range(S['duty1'][1]['NPC']):
        fig, axs = plt.subplots(1, 2, figsize=(12, 5.4))
        fig.subplots_adjust(left=0.02, right=0.86, top=0.78, bottom=0.03, wspace=0.05)
        for ax, d in zip(axs, ('duty1', 'duty4')):
            D = S[d][1]; z = D['z']; j, s, th = frame(D, k)
            tr = frame_xy(D, float(z['th'][j])); mat2 = np.r_[D['mat'], D['mat']]
            Bm = np.hypot(z['Bx'][j], z['By'][j]); Bm2 = np.r_[Bm, Bm]
            ax.set_facecolor('white')
            t1 = frame_xy(D, float(z['th'][j])); t1.set_mask(mat2 != 2)
            pc = ax.tripcolor(t1, facecolors=Bm2, cmap='magma', vmin=0, vmax=0.25, rasterized=True)
            t2 = frame_xy(D, float(z['th'][j])); t2.set_mask(mat2 != 3)
            ax.tripcolor(t2, facecolors=np.full(len(mat2), 0.35), cmap='Greys', vmin=0, vmax=1, rasterized=True)
            ax.tricontour(tr, s * np.r_[z['A'][j], -z['A'][j]], levels=np.linspace(-0.04, 0.04, 121), colors='#1baf7a', linewidths=0.5)
            ax.set_aspect('equal'); ax.set_xlim(-24, 24); ax.set_ylim(50, 78); ax.axis('off')
            cu = D['mat'] == 2
            now = math.sqrt(float((Bm[cu] ** 2 * z['area'][cu]).sum() / z['area'][cu].sum()))
            r = res[d]
            ax.set_title('%s: %.0f Hz, %.0f A rms line\ncopper B_rms %.3f T (this instant %.3f T)\nskin depth %.1f mm vs wire %.2f mm;  AC loss %.0f W' % (
                d, r['f_el_Hz'], r['I_line_rms'], r['cu_B_rms_T'], now, r['skin_depth_mm'], r['wire_mm'], r['cu_ac_W_unskewed']), fontsize=9, loc='left')
        cax = fig.add_axes([0.88, 0.1, 0.02, 0.6]); fig.colorbar(pc, cax=cax, label='|B| in the conductors (T)')
        fig.text(0.02, 0.95, 'Slot leakage field at the wires (3 slots on the y axis), %.0f deg el.  P_AC ~ f^2 x B_rms^2 x d^4: duty4 has 0.2x the B^2 but 27x the f^2' % (5 * th % 360),
                 fontsize=9.5)
        fig.text(0.02, 0.92, 'grey = steel, green = flux lines; magnets + winding 100 C, unskewed', fontsize=8, color=INK2)
        p = os.path.join(fr, 'f%03d.png' % k); fig.savefig(p, dpi=100, facecolor='white'); plt.close(fig); files.append(p)
    mp4(os.path.join(OUT, 'slot_leakage_duty1_vs_duty4.mp4'), files, 12)
    shutil.copy(files[0], os.path.join(OUT, 'slot_leakage_frame0.png'))


def compare():
    S = {d: stats(d) for d in ('duty1', 'duty4')}
    res = {d: v[0] for d, v in S.items()}
    res['probes'] = waveforms(S)
    json.dump(res, open(os.path.join(OUT, 'field_stats.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))
    density_maps(S, res)
    slot_anim(S, res)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'flux':
        flux(sys.argv[2])
    elif cmd == 'snap':
        flux(sys.argv[2], animate=False); print(json.dumps(stats(sys.argv[2])[0], indent=1))
    else:
        compare()
