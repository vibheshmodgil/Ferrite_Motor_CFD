"""FEMM fields over one electrical period at the duty load points of Design9795_1 (copper, 100 C, unskewed centre slice).

Reuses the repo model: backemf.build/set_angle (half model + air-gap element => fixed mesh), lab_map currents/signs.
Half electrical period is solved (B(x, th+36 mech) = -B(x, th)); the other half follows by anti-periodicity.
python femm_duty_solve.py duty1 [nstep]   -> results/femm_duty/raw_duty1.npz
"""
import json, math, os, sys, time
os.environ['AGE'] = '1'; os.environ['SYM'] = '1'; os.environ['MAG_T'] = '100'
REPO = r'C:\Users\vibhe\Downloads\OUTPUT\ferrite_repo\repo\Design9795_1'
sys.path.insert(0, REPO); os.chdir(REPO)
import numpy as np, psutil
import backemf as M
import lab_map as L
import femm

OUT = r'C:\Users\vibhe\Downloads\OUTPUT\CFD\results\femm_duty'
LOSSES = json.load(open(r'C:\Users\vibhe\Downloads\OUTPUT\CFD\results\losses_9795.json'))
RPM = dict(duty1=1782, duty2=2550, duty3=3637, duty4=9339, duty5=1612)


def read_ans(fn):
    s = open(fn).read().split('\n')
    l0 = next(i for i, l in enumerate(s) if l.startswith('[NumBlockLabels]'))
    labs = [l.split() for l in s[l0 + 1:l0 + 1 + int(s[l0].split('=')[1])]]
    k = s.index('[Solution]'); n = int(s[k + 1])
    nodes = np.array([[float(v) for v in l.split()[:3]] for l in s[k + 2:k + 2 + n]])
    ne = int(s[k + 2 + n])
    el = np.array([[int(v) for v in l.split()[:4]] for l in s[k + 3 + n:k + 3 + n + ne]])
    x, y, A = nodes[:, 0] / 1e3, nodes[:, 1] / 1e3, nodes[:, 2]
    i, j, kk = el[:, 0], el[:, 1], el[:, 2]
    b = np.stack([y[j] - y[kk], y[kk] - y[i], y[i] - y[j]], 1); c = np.stack([x[kk] - x[j], x[i] - x[kk], x[j] - x[i]], 1)
    a2 = x[i] * b[:, 0] + x[j] * b[:, 1] + x[kk] * b[:, 2]
    Ae = np.stack([A[i], A[j], A[kk]], 1)
    mat = np.array([int(labs[l][2]) for l in el[:, 3]])        # 1 Air 2 Cu 3 M235 4 SCM420 5 Magnet
    return dict(xy=nodes[:, :2], A=A, tri=el[:, :3], mat=mat, area=np.abs(a2) / 2,
                Bx=(c * Ae).sum(1) / a2, By=-(b * Ae).sum(1) / a2)


def main(duty, nstep):
    op = LOSSES['operating'][duty]['femm_lab']
    i_d, i_q = op['id_phase_pk'] / 2, op['iq_phase_pk'] / 2          # path peak A (lab_map convention)
    th_list = [k * 36.0 / nstep for k in range(nstep)]                  # half electrical period
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, 'work', 'm_%s.fem' % duty); os.makedirs(os.path.dirname(fn), exist_ok=True)
    before = {p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() == 'femm.exe'}
    femm.openfemm(1)
    # pyfemm starts femm.exe through COM (not a child): the new femm.exe is ours; fkn.exe inherits its priority
    for p in psutil.process_iter(['name']):
        if (p.info['name'] or '').lower() == 'femm.exe' and p.pid not in before:
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS); print('own femm pid', p.pid, flush=True)
    M.build(fn, True)
    geo, A, Bx, By, T, psi = None, [], [], [], [], []
    t0 = time.time()
    for th in th_list:
        M.set_angle(th)
        ip = L.phase_currents(th, i_d, i_q)
        for ph, teeth in M.PHASE_TEETH.items():
            for t in teeth:
                femm.mi_modifycircprop('T%d' % t, 1, L.SIGN[ph][t] * ip[ph])
        femm.mi_analyze(1); femm.mi_loadsolution()
        pc = M.coil_psi(); T.append(M.torque()); femm.mo_close()
        psi.append([sum(L.SIGN[ph][t] * pc[t - 1] for t in teeth) / M.PATHS for ph, teeth in M.PHASE_TEETH.items()])
        f = read_ans(fn.replace('.fem', '.ans'))
        if geo is None:
            geo = f
        assert len(f['Bx']) == len(geo['Bx']), 'mesh changed'
        A.append(f['A']); Bx.append(f['Bx']); By.append(f['By'])
        print(time.strftime('%H:%M:%S'), duty, 'th %.2f T %.2f (%.0f s/solve)' % (th, T[-1], (time.time() - t0) / len(T)), flush=True)
    femm.closefemm()
    np.savez_compressed(os.path.join(OUT, 'raw_%s.npz' % duty), xy=geo['xy'], tri=geo['tri'], mat=geo['mat'], area=geo['area'],
                        A=np.array(A, np.float32), Bx=np.array(Bx, np.float32), By=np.array(By, np.float32), th=np.array(th_list),
                        T=np.array(T), psi=np.array(psi), id=i_d, iq=i_q, rpm=RPM[duty], rot_off=M.ROT_OFF,
                        r_age_in=M.R_AGE_IN, r_age_out=M.R_AGE_OUT, phi=np.array([L.PHI[p] for p in ('Ph1', 'Ph2', 'Ph3')]))
    print(duty, 'done %.1f min, mean T %.2f N.m' % ((time.time() - t0) / 60, np.mean(T)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 24)
