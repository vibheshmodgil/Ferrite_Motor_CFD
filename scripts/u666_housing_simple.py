"""U666 backup simplified housing -> mesh/u666/housing_simple.brep (+ .json). Planes/cylinders/cones only.
Run: .venv/Scripts/python -I scripts/u666_housing_simple.py [--check]   (axis = z, mm)
Measured from mesh/u666/subset.brep (see results/u666/steps_log.md S7b). CALIBRATION KNOBS are in the K dict."""
import gmsh, json, math, sys
K = dict(
    FIN_C0=-12.8, FIN_PITCH=10.0, FIN_N=11, R_VALLEY=79.6, R_TIP=92.5,
    FIN_HW=[(79.0, 4.9), (79.6, 4.9), (80.2, 3.6), (86.4, 1.7), (88.0, 1.5), (91.5, 1.0), (92.5, 0.6)],  # (r, half width) fin profile
    R_FIT=75.0, Z_FIT=(-6.3, 60.2),                 # stator fit bore (exact)
    SEAT_F=(26.0, 31.3, 77.56, 97.5), SEAT_R=(17.5, 20.7, -31.2, -20.5),   # r_in, r_out, z0, z1 (bearing seat bores exact)
    Z_WALL_F=(94.2, 97.7),                          # front end wall inner/outer face (exact)
    COVER_VOL=269.64,                               # cm3 target, skirt thickness solved
    BOX=(-68.4, 68.6, -52.4, 79.3, -101.0, -83.8), BOX_T=(2.0, 1.6), BOSS_DZ=0.2,   # x0,x1,y0,y1,z0,z1 ; lid, wall thickness
)
o = gmsh.model.occ
def rev(pts):                      # polygon (r,z) -> solid of revolution about z
    P = [o.addPoint(r, 0, z) for r, z in pts]
    L = [o.addLine(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    s = o.addPlaneSurface([o.addCurveLoop(L)])
    return [t for d, t in o.revolve([(2, s)], 0, 0, 0, 0, 0, 1, 2 * math.pi) if d == 3][0]
def cover_pts(t):
    return [(72.4, -12.5), (76.6, -12.5), (76.6, -27.3), (80.5, -27.3), (80.5, -39.5), (66.0, -39.5), (66.0, -83.7),
            (66.0 - t, -83.7), (66.0 - t, -39.5), (20.7, -39.5), (20.7, -20.6), (25.0, -20.6), (25.0, -36.0), (72.4, -36.0)]
def build():
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); gmsh.model.add("hs")
    Zf0, Zf1 = K['Z_WALL_F']; rf = K['R_FIT']; z0, z1 = K['Z_FIT']; sf = K['SEAT_F']
    body = rev([(79.3, -27.3), (81.5, -27.3), (81.5, -17.0), (79.6, -16.4), (79.6, 89.5), (75.5, 95.0), (75.0, Zf1),
                (31.3, Zf1), (31.3, 118.5), (29.5, 119.5), (29.5, 126.7), (25.5, 126.7), (25.5, 106.5), (19.8, 106.5),
                (19.8, 100.5), (16.9, 100.5), (16.9, 97.5), (31.3, 97.5), (31.3, Zf0), (71.0, Zf0), (74.0, 91.2),
                (74.0, z1), (rf, z1), (rf, z0), (76.8, -11.3), (78.4, -11.3), (78.4, -25.8)])
    fins = []
    for k in range(K['FIN_N']):
        c = K['FIN_C0'] + k * K['FIN_PITCH']
        pts = [(r, c - w) for r, w in K['FIN_HW']] + [(r, c + w) for r, w in reversed(K['FIN_HW'])]
        fins.append(rev(pts))
    bosses = []                    # 3 screw bosses r12 on r 72.5 at 7.4/127.4/247.4 deg (CAD plane centres)
    for a in (7.4, 127.4, 247.4):
        x, y = 72.5 * math.cos(math.radians(a)), 72.5 * math.sin(math.radians(a))
        bosses.append(o.addCylinder(x, y, Zf1 - K['BOSS_DZ'], 0, 0, 117.7 - Zf1 + K['BOSS_DZ'], 12.0))
    o.synchronize()
    h, _ = o.fuse([(3, body)], [(3, t) for t in fins + bosses]); o.synchronize()
    parts = {'housing_body': [t for d, t in h]}
    seat = lambda p: rev([(p[0], p[2]), (p[1], p[2]), (p[1], p[3]), (p[0], p[3])])
    parts['seat_front'] = [seat(K['SEAT_F'])]; parts['seat_rear'] = [seat(K['SEAT_R'])]
    parts['oring'] = [rev([(76.6, -20.7), (78.4, -20.7), (78.4, -18.3), (76.6, -18.3)])]
    # rear cover: solve skirt thickness for the CAD volume
    t = 4.0
    for _ in range(4):
        c = rev(cover_pts(t)); o.synchronize(); v = o.getMass(3, c) / 1e3
        c2 = rev(cover_pts(t + 0.5)); o.synchronize(); v2 = o.getMass(3, c2) / 1e3
        o.remove([(3, c), (3, c2)], recursive=True)
        t = max(0.8, t + 0.5 * (K['COVER_VOL'] - v) / (v2 - v))
    K['SKIRT_T'] = round(t, 2); parts['rear_cover'] = [rev(cover_pts(K['SKIRT_T']))]
    x0, x1, y0, y1, bz0, bz1 = K['BOX']; lid, w = K['BOX_T']
    o.synchronize()
    bo = o.addBox(x0, y0, bz0, x1 - x0, y1 - y0, bz1 - bz0); bi = o.addBox(x0 + w, y0 + w, bz0 + lid, x1 - x0 - 2 * w, y1 - y0 - 2 * w, bz1 - bz0 - lid + 1)
    parts['terminal_box'] = [t for d, t in o.cut([(3, bo)], [(3, bi)])[0]]
    g0, g1, g2, g3 = -64.5, 67.1, -50.8, 74.0
    go = o.addBox(g0, g2, -86.7, g1 - g0, g3 - g2, 2.9); gi = o.addBox(g0 + 2.5, g2 + 2.5, -87, g1 - g0 - 5, g3 - g2 - 5, 4)
    parts['gasket'] = [t for d, t in o.cut([(3, go)], [(3, gi)])[0]]
    cg = o.addCylinder(-12.0, 32.9, -98.7, 0, 0, 13.0, 9.0); ci = o.addCylinder(-12.0, 32.9, -99, 0, 0, 14, 7.2)
    parts['gland'] = [t for d, t in o.cut([(3, cg)], [(3, ci)])[0]]
    o.synchronize()
    return parts
def fills():                       # sealed-cavity fillers, only used to measure the outer skin
    return [rev([(0.0, -36.0), (72.4, -36.0), (72.4, -12.5), (76.6, -12.5), (76.6, -27.3), (78.4, -27.3), (78.4, -11.3), (76.8, -11.3), (75.0, -6.3), (75.0, 60.2),
                 (74.0, 60.2), (74.0, 91.2), (71.0, 94.2), (31.3, 94.2), (31.3, 97.5), (16.9, 97.5), (16.9, 126.7), (0.0, 126.7)]),
            o.addBox(K['BOX'][0] + K['BOX_T'][1], K['BOX'][2] + K['BOX_T'][1], K['BOX'][4] + K['BOX_T'][0], K['BOX'][1] - K['BOX'][0] - 2 * K['BOX_T'][1], K['BOX'][3] - K['BOX'][2] - 2 * K['BOX_T'][1], -83.7 - K['BOX'][4] - K['BOX_T'][0]),
            rev([(0.0, -83.7), (66.0 - K['SKIRT_T'], -83.7), (66.0 - K['SKIRT_T'], -39.5), (0.0, -39.5)])]
if __name__ == '__main__':
    parts = build()
    allv = [t for v in parts.values() for t in v]
    for n, v in parts.items(): print(n, [round(o.getMass(3, t) / 1e3, 2) for t in v])
    gmsh.write('mesh/u666/housing_simple.brep')
    json.dump({'parts': {n: [i for i in v] for n, v in parts.items()}, 'knobs': K,
               'vol_cm3': {n: [o.getMass(3, t) / 1e3 for t in v] for n, v in parts.items()}}, open('mesh/u666/housing_simple.json', 'w'), indent=1)
    print('volume total cm3', sum(o.getMass(3, t) for t in allv) / 1e3, 'skirt t', K['SKIRT_T'])
    if '--check' in sys.argv:
        F = fills(); o.synchronize()
        u, _ = o.fuse([(3, t) for t in allv], [(3, t) for t in F]); o.synchronize()
        A = 0; Af = 0; bins = {}; dd = {}
        for d, f in gmsh.model.getBoundary(u, oriented=False):
            a = o.getMass(2, f); zc = o.getCenterOfMass(2, f)[2]
            if -6 <= zc < 94 and '--dbg' in sys.argv: tp = gmsh.model.getType(2, f); dd[tp] = dd.get(tp, 0) + a / 100
            for lo, hi in ((-110, -84), (-84, -27), (-27, -6), (-6, 94), (94, 127)):
                if lo <= zc < hi: bins[lo] = bins.get(lo, 0) + a / 100
            bb = gmsh.model.getBoundingBox(2, f); A += a
            if a > 1500 and '--dbg' in sys.argv: print(f, gmsh.model.getType(2, f), round(a/100,1), [round(x,1) for x in bb])
            if -6 <= bb[2] and bb[5] <= 94 and max(abs(bb[0]), abs(bb[3]), abs(bb[1]), abs(bb[4])) > 78 and (bb[3] - bb[0]) > 100: Af += a
        print(dd); print('bins', {k: round(v, 1) for k, v in sorted(bins.items())}); print('skin cm2', A / 100, 'fin band cm2', Af / 100, 'fused vol', sum(o.getMass(*e) for e in u) / 1e3)
    gmsh.finalize()
