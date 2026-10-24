"""Motor variant "65": 65 mm stator, 66 mm rotor (0.5 mm overhang each side), phase-cable terminals INSIDE the housing.
Terminal bars from the busbar end on M8 press-in studs inside the rear end space; the cable lugs sit on the bars and point
radially out, each cable leaves straight through an M20 IP68 gland in a boss on the housing wall (no external cap).
    python build_stator65.py; python build_motor65.py; python check_motor65.py; python sw_build_motor65.py
Global frame = stator frame: z = shaft axis, +z = rear (busbar side), -z = drive end.
"""
import json, math, os
import numpy as np
import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir

D = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(D, "geom_sp.json")))
SP = json.load(open(os.path.join(D, "stator65_placements.json")))
V, Z = cq.Vector, cq.Vector(0, 0, 1)
O = cq.Vector(0, 0, 0)

# ---------------------------------------------------------------- main dimensions (mm)
STACK_R = 66.0                      # rotor stack: stator 65 + 0.5 mm overhang each side
RR, RS = 53.0, 15.0                 # rotor OD/2, bore/2 (FEMM ROTOR)
END_T, END_R = 2.0, 52.0            # rotor end plates (Al): cover the magnets (rom 51), 2 mm under the coil inner r 54.09
B_RO, B_RI, B_W = 26.0, 15.0, 15.0  # bearings 52 / 30 / 15 (user)
ZB_F = (-54.5, -39.5)               # front (locating) bearing
ZB_R = (38.5, 53.5)                 # rear (floating) bearing, wave spring behind
Z_COLLAR = (-39.5, -35.0)           # shaft collar between front bearing and rotor end plate
Z_SPACER = (35.0, 38.5)             # sleeve between rotor end plate and rear bearing
SEAL = (15.0, 23.5, 7.0)            # radial shaft seal 30 x 47 x 7
Z_SEAL = (-63.1, -56.1)
Z_CLIP_F, Z_CLIP_R = (-56.1, -54.5), (53.5, 55.1)   # DIN 471-30 grooves
Z_SHAFT_END = 56.5
R_HOUSE_IN_REAR = 82.0              # housing inner radius over the end windings / busbar
Z_WALL_F = (-52.2, -47.2)           # front end wall (65 mm coil wire reaches z -44.97)
Z_BOSS_F = -37.5                    # front bearing boss top
R_SHOULDER = 76.0
R_OUT, FIN_R, FIN_T = 86.0, 94.0, 2.5
Z_STK = 32.5                        # stator stack half length
ZP_TOP = 53.5                       # busbar plane top (65 mm stator)
BAR_T, BAR_W = 3.0, 10.0
zb0, zb1 = ZP_TOP + 4.0, ZP_TOP + 7.0     # bars 4 mm above the plates: the lug barrel (OD 13) stays 2 mm clear of them
R_STUD = 59.0                       # M8 press-in studs inside the housing, lugs radial out
STUD_ANG = {"L1": 12.0, "L2": 72.0, "L3": 50.5}  # studs fanned out so the L2 bar passes between the L1 and L3 lug palms
BAR_PATH = {"L1": [(57.951, 16.0), (R_STUD, 12.0)], "L3": [(57.951, 46.5), (R_STUD, 50.5)],
            "L2": [(75.476, 31.0), (42.0, 31.0), (42.0, 57.0), (R_STUD, 72.0)]}   # L2: radial in at 31 deg, round inside every lug palm (r 42), out to its stud
R_GLAND, Z_GLAND = 92.0, zb1 + 1.75       # gland seat on the wall bosses, cable axis = lug palm centre
ENC_ANG = 92.0                      # M16 encoder gland
Z_SPIGOT, Z_REAR, COVER_T = 70.5, 75.5, 3.0   # spigot 1.75 mm over the lug barrels (top z 68.75); housing rear face; cover plate
DENS = {"Al": 2.70e-3, "Cu": 8.96e-3, "steel": 7.85e-3, "lam": 7.65e-3, "ferrite": 4.9e-3, "PA66GF30": 1.36e-3,
        "NBR": 1.3e-3, "FR4": 1.85e-3, "NdFeB": 7.5e-3, "brass": 8.5e-3, "PEEK": 1.32e-3}

parts, inst = {}, []


def save(name, shape, mat, color):
    assert len(shape.Solids()) >= 1 and shape.isValid(), name
    cq.exporters.export(cq.Workplane().add(shape), os.path.join(D, name + ".step"))
    parts[name] = {"mat": mat, "color": color, "vol": shape.Volume(), "mass_g": shape.Volume() * DENS[mat], "solids": len(shape.Solids())}
    return shape


def place(name, R=None, t=(0, 0, 0)):
    R = np.eye(3) if R is None else np.asarray(R, float)
    inst.append({"part": name, "R": R.tolist(), "t": [float(x) for x in t]})


def Rz(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def cyl(r, z0, z1, x=0, y=0):
    return cq.Solid.makeCylinder(r, z1 - z0, V(x, y, z0))


def ring(r0, r1, z0, z1):
    s = cyl(r1, z0, z1)
    return s.cut(cyl(r0, z0, z1)) if r0 > 0 else s


def revolve(pts):                   # closed (r, z) polygon -> solid of revolution about z
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def to_sector(s):                   # local (u, v, z) -> global
    return s.rotate(O, Z, TERM_ANG)


# ================================================================ rotor (exact FEMM / spoke_rotor_explorer geometry)
ROT = dict(pole_number=10, rotor_diameter=106, shaft_diameter=30, magnet_inset=2, magnet_depth=28, magnet_opening=10,
           magnet_X=18, magnet_Y=8.5, magnet_Z=6, magnet_glue_gap=0.1, Bridge_thickness=2, bridge_offset=3.5)


def rotor_geometry(p):              # verbatim port of femm_em/femm_motor.py rotor_geometry (pole on +y)
    t, rs, rr = p['Bridge_thickness'] / 2, p['shaft_diameter'] / 2, p['rotor_diameter'] / 2
    rom = rr - p['magnet_inset']; rim = rom - p['magnet_depth']; ho = p['magnet_opening'] / 2
    a = math.radians(180 / p['pole_number']); T, Cs = math.tan(a), math.cos(a)
    P = (-(rim * T - t / Cs), rim); Q = (-p['magnet_Y'], rim + p['magnet_X']); R = (-p['magnet_Z'], rom)
    Dd = (-ho, rom); C = (-ho, math.sqrt(rr * rr - ho * ho))
    yg = rs + p['bridge_offset']; Gg = (-(yg * T - t / Cs), yg)
    gap, ctr = p['magnet_glue_gap'], (0, (rim + rom) / 2)

    def off(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        if (ctr[0] - (a[0] + b[0]) / 2) * nx + (ctr[1] - (a[1] + b[1]) / 2) * ny < 0: nx, ny = -nx, -ny
        return (a[0] + nx * gap, a[1] + ny * gap), (b[0] + nx * gap, b[1] + ny * gap)

    def X(l1, l2):
        (a, b), (c, d) = l1, l2; r = (b[0] - a[0], b[1] - a[1]); q = (d[0] - c[0], d[1] - c[1])
        k = ((c[0] - a[0]) * q[1] - (c[1] - a[1]) * q[0]) / (r[0] * q[1] - r[1] * q[0])
        return (a[0] + r[0] * k, a[1] + r[1] * k)

    PQ, QR = off(P, Q), off(Q, R)
    Pm, Qm, Rm = X(PQ, ((0, rim), (1, rim))), X(PQ, QR), X(QR, ((0, rom), (1, rom)))
    return dict(P=P, Q=Q, R=R, D=Dd, C=C, G=Gg, Pm=Pm, Qm=Qm, Rm=Rm, rs=rs, rr=rr, rim=rim, rom=rom)


g = rotor_geometry(ROT)
mir = lambda p: (-p[0], p[1])
rG = math.hypot(*g["G"])
z0r, z1r = -STACK_R / 2, STACK_R / 2
cav = (cq.Workplane("XY").workplane(offset=z0r)
       .moveTo(g["C"][0], RR + 1).lineTo(*g["D"]).lineTo(*g["R"]).lineTo(*g["Q"]).lineTo(*g["P"]).lineTo(*g["G"])
       .threePointArc((0, rG), mir(g["G"])).lineTo(*mir(g["P"])).lineTo(*mir(g["Q"])).lineTo(*mir(g["R"]))
       .lineTo(*mir(g["D"])).lineTo(mir(g["C"])[0], RR + 1).close().extrude(STACK_R).val())
KEY_ANG = 0.0                       # keyway on a web (pockets sit at 18 + 36k deg), away from the pocket floors (r 19.15)
lam = ring(RS, RR, z0r, z1r)
for k in range(10):
    lam = lam.cut(cav.rotate(O, Z, 36.0 * k))             # pole axis at 90 + 36k deg, magnets placed the same way
hub_slot = box(RS - 1, RS + 3.3, -4, 4, z0r - 1, z1r + 1).rotate(O, Z, KEY_ANG)
lam = lam.cut(hub_slot)
save("rotor_lamination_stack", lam, "lam", (0.35, 0.37, 0.40))
place("rotor_lamination_stack")
mag2d = [g["Pm"], g["Qm"], g["Rm"], mir(g["Rm"]), mir(g["Qm"]), mir(g["Pm"])]
ML = STACK_R / 2 - 0.1                                   # two blocks per pole, 0.1 gaps
mag = cq.Workplane("XY").polyline(mag2d).close().extrude(ML).val()          # z 0..ML, pole axis +y
save("magnet_ferrite", mag, "ferrite", (0.15, 0.15, 0.17))
for k in range(10):
    for zz in (z0r + 0.05, 0.05):
        place("magnet_ferrite", Rz(36.0 * k), (0, 0, zz))
endp = ring(RS, END_R, 0, END_T).cut(box(RS - 1, RS + 3.3, -4, 4, -1, END_T + 1).rotate(O, Z, KEY_ANG))
save("rotor_end_plate", endp, "Al", (0.75, 0.77, 0.80))
place("rotor_end_plate", None, (0, 0, z1r))
place("rotor_end_plate", None, (0, 0, z0r - END_T))

# ================================================================ shaft, key, spacer, bearings, seal, circlips
OUT_L, OUT_R = 45.0, 12.5
z_end_f = Z_SEAL[0] - OUT_L
shaft = revolve([(0, z_end_f), (OUT_R - 1, z_end_f), (OUT_R, z_end_f + 1), (OUT_R, Z_SEAL[0]), (15, Z_SEAL[0]),
                 (15, Z_CLIP_F[0]), (14.3, Z_CLIP_F[0]), (14.3, Z_CLIP_F[1]), (15, Z_CLIP_F[1]),
                 (15, Z_COLLAR[0]), (17, Z_COLLAR[0]), (17, Z_COLLAR[1]), (15, Z_COLLAR[1]),
                 (15, Z_CLIP_R[0]), (14.3, Z_CLIP_R[0]), (14.3, Z_CLIP_R[1]), (15, Z_CLIP_R[1]), (15, Z_SHAFT_END - 1), (14, Z_SHAFT_END), (0, Z_SHAFT_END)])
shaft = shaft.cut(cyl(7, -45, Z_SHAFT_END + 1))      # hollow: blind bore 14 from the rear (-116 g; 45 N.m -> 9 MPa); holds the encoder magnet holder
shaft = shaft.cut(box(11, 16, -4, 4, -28.5, 28.5).rotate(O, Z, KEY_ANG))                # rotor keyway 8 x 4
shaft = shaft.cut(box(OUT_R - 4, OUT_R + 1, -4, 4, z_end_f + 5, z_end_f + 33))      # output keyway 8 x 4, 28 long
save("shaft", shaft, "steel", (0.62, 0.64, 0.68))
place("shaft")
key = box(11, 18, -4, 4, -28, 28).rotate(O, Z, KEY_ANG)
save("key_8x7x56", key, "steel", (0.55, 0.55, 0.55))
place("key_8x7x56")
save("key_8x7x28", box(OUT_R - 4, OUT_R + 3, -4, 4, z_end_f + 5.5, z_end_f + 32.5), "steel", (0.55, 0.55, 0.55))
place("key_8x7x28")
save("spacer_sleeve", ring(15, 18, *Z_SPACER), "steel", (0.6, 0.6, 0.6))
place("spacer_sleeve")
nb, rb = 10, 3.75
brg = ring(B_RI, 18.6, 0, B_W).fuse(ring(22.9, B_RO, 0, B_W))
for k in range(nb):
    a = 2 * math.pi * k / nb
    brg = brg.fuse(cq.Solid.makeSphere(rb, V(20.75 * math.cos(a), 20.75 * math.sin(a), B_W / 2)))
save("bearing_52x30x15", brg.clean(), "steel", (0.78, 0.78, 0.80))
place("bearing_52x30x15", None, (0, 0, ZB_F[0]))
place("bearing_52x30x15", None, (0, 0, ZB_R[0]))
seal = revolve([(SEAL[0], 0), (SEAL[1], 0), (SEAL[1], SEAL[2]), (SEAL[0] + 2.5, SEAL[2]), (SEAL[0] + 2.5, 2.0), (SEAL[0], 1.0)])
save("shaft_seal_30x47x7", seal, "NBR", (0.1, 0.1, 0.1))
place("shaft_seal_30x47x7", None, (0, 0, Z_SEAL[0]))
save("circlip_DIN471_30", ring(14.35, 17.8, 0, 1.5), "steel", (0.2, 0.2, 0.2))
place("circlip_DIN471_30", None, (0, 0, Z_CLIP_F[0] + 0.05))
place("circlip_DIN471_30", None, (0, 0, Z_CLIP_R[0] + 0.05))
save("circlip_DIN472_52", ring(23.6, 27.5, 0, 1.75), "steel", (0.2, 0.2, 0.2))
place("circlip_DIN472_52", None, (0, 0, ZB_F[1] + 0.0))
save("wave_spring_52", ring(22.5, 25.5, 0, 0.5), "steel", (0.3, 0.3, 0.35))
place("wave_spring_52", None, (0, 0, ZB_R[1]))

# ================================================================ encoder: diametric magnet on the shaft end, PCB on the cover
save("encoder_magnet_holder", cyl(6.95, 51.7, 56.5).fuse(cyl(10, 56.5, 59.5)).cut(cyl(4, 57.5, 59.6)), "PEEK", (0.85, 0.75, 0.55))
place("encoder_magnet_holder")
save("encoder_magnet_8x2", cyl(4, 57.5, 59.5), "NdFeB", (0.6, 0.6, 0.65))
place("encoder_magnet_8x2")
pcb = cyl(21.5, 61.0, 62.6).fuse(box(-2.5, 2.5, -2.5, 2.5, 60.1, 61.0))
save("encoder_pcb", pcb, "FR4", (0.05, 0.45, 0.2))
place("encoder_pcb")

# ================================================================ terminal bars: busbar foot -> M8 press-in stud inside the housing
tp = {t["net"]: t for t in SP["terminals"]}
pol = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
for net, t in tp.items():
    pts = [pol(r, a) for r, a in BAR_PATH[net]]
    (xf, yf), (xs, ys) = pts[0], pts[-1]
    s = None
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):             # straight strips + round joints = stamped bar outline
        L, ang = math.hypot(x1 - x0, y1 - y0), math.degrees(math.atan2(y1 - y0, x1 - x0))
        seg = box(0, L, -BAR_W / 2, BAR_W / 2, zb0, zb1).rotate(O, Z, ang).translate(V(x0, y0, 0))
        s = seg if s is None else s.fuse(seg)
    for (x, y) in pts[1:-1]:                                          # round joints at the bends only (foot end square)
        s = s.fuse(cyl(BAR_W / 2, zb0, zb1, x, y))
    s = s.fuse(cyl(BAR_W / 2 + 1.5, zb0, zb1, xs, ys))                  # round stud pad 13 wide
    s = s.fuse(box(-1.5, 1.5, -BAR_W / 2, BAR_W / 2, ZP_TOP, zb1).rotate(O, Z, t["a"]).translate(V(xf, yf, 0)))  # riser welded on the plate
    s = s.cut(cyl(4.0, zb0 - 1, zb1 + 1, xs, ys)).clean()           # press-in stud hole
    save("terminal_bar_" + net, s, "Cu", (0.80, 0.45, 0.20))
    place("terminal_bar_" + net)

# ================================================================ housing (Al, one piece with the drive-end shield)
prof = [(23.5, Z_SEAL[0]), (30, Z_SEAL[0]), (30, Z_WALL_F[0]), (R_OUT, Z_WALL_F[0]), (R_OUT, Z_REAR - 8), (90, Z_REAR - 8), (90, Z_REAR),
        (R_HOUSE_IN_REAR, Z_REAR), (R_HOUSE_IN_REAR, Z_STK), (80, Z_STK), (80, -Z_STK), (R_SHOULDER, -Z_STK),
        (R_SHOULDER, Z_WALL_F[1]), (31, Z_WALL_F[1]), (31, Z_BOSS_F), (B_RO, Z_BOSS_F), (B_RO, ZB_F[0]), (SEAL[1], ZB_F[0])]
house = revolve(prof)
for k in range(10):                                            # circumferential fins
    zc = -43.0 + 8.0 * k
    house = house.fuse(ring(R_OUT - 0.5, FIN_R, zc - FIN_T / 2, zc + FIN_T / 2))
for k in range(4):                                             # 4 x M8 mounting bosses on the drive-end face
    a = math.radians(45 + 90 * k)
    house = house.fuse(cyl(9, -59, Z_WALL_F[0] + 0.5, 65 * math.cos(a), 65 * math.sin(a)))
GLANDS = [(STUD_ANG[n], 10.0) for n in ("L1", "L2", "L3")] + [(ENC_ANG, 8.0)]   # (angle, hole radius)
for a, rh in GLANDS:                                           # flat gland seats on the wall, trimmed to the rear face
    house = house.fuse(cq.Solid.makeCylinder(13.0, R_GLAND - 80, V(80, 0, Z_GLAND), V(1, 0, 0)).cut(box(70, 100, -20, 20, Z_REAR, Z_REAR + 20)).rotate(O, Z, a))
house = house.cut(ring(0, R_HOUSE_IN_REAR, Z_STK, Z_REAR + 0.01))
for a, rh in GLANDS:
    house = house.cut(cq.Solid.makeCylinder(rh, 20, V(75, 0, Z_GLAND), V(1, 0, 0)).rotate(O, Z, a))
house = house.cut(ring(0, 27.6, ZB_F[1], ZB_F[1] + 1.75).cut(ring(0, B_RO - 0.01, ZB_F[1], ZB_F[1] + 1.75)))  # DIN 472 groove
for k in range(4):
    a = math.radians(45 + 90 * k)
    house = house.cut(cyl(3.4, -59.5, Z_WALL_F[1] - 1.0, 65 * math.cos(a), 65 * math.sin(a)))   # M8 tapping holes, 1 mm wall left
SCREW_ANGS = [125, 185, 245, 305, 350]                         # cover screws, away from the gland bosses (16..92 deg)
for a in SCREW_ANGS:
    x, y = 86 * math.cos(math.radians(a)), 86 * math.sin(math.radians(a))
    house = house.cut(cyl(2.1, Z_REAR - 8, Z_REAR + 0.1, x, y))
house = house.clean()
save("housing", house, "Al", (0.70, 0.74, 0.78))
place("housing")

# ================================================================ rear cover (Al): spigot + O-ring, rear bearing boss, encoder inside
cover = ring(0, 90, Z_REAR, Z_REAR + COVER_T).fuse(ring(76.5, R_HOUSE_IN_REAR - 0.02, Z_SPIGOT, Z_REAR))
cover = cover.fuse(ring(B_RO, 31, ZB_R[0], Z_REAR)).fuse(ring(22, B_RO, ZB_R[1] + 0.5, ZB_R[1] + 2.5))
cover = cover.cut(ring(80.1, 83, Z_SPIGOT + 0.7, Z_SPIGOT + 3.9))     # O-ring groove, 2.5 cord
for a in SCREW_ANGS:
    x, y = 86 * math.cos(math.radians(a)), 86 * math.sin(math.radians(a))
    cover = cover.cut(cyl(2.75, Z_REAR - 1, Z_REAR + COVER_T + 1, x, y))
for k in range(3):                                             # PCB standoffs
    a = math.radians(120 * k + 30)
    cover = cover.fuse(cyl(2, 62.6, Z_REAR + 0.01, 18 * math.cos(a), 18 * math.sin(a)))
cover = cover.clean()
save("rear_cover", cover, "Al", (0.70, 0.74, 0.78))
place("rear_cover")
oring = cq.Solid(BRepPrimAPI_MakeTorus(gp_Ax2(gp_Pnt(0, 0, Z_SPIGOT + 2.3), gp_Dir(0, 0, 1)), 81.15, 1.25).Shape())
save("oring_cover_2.5", oring, "NBR", (0.1, 0.1, 0.1))
place("oring_cover_2.5")

# ---------------------------------------------------------------- hardware on the terminals (built at the origin, placed)
hexa = lambda af, h: cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(h).val()
save("stud_M8_press_in", cyl(4, 0, 13.1), "steel", (0.4, 0.4, 0.42))     # self-clinching, flush with the bar underside
save("nut_M8_thin", hexa(13, 4).cut(cyl(4, -1, 5)), "steel", (0.4, 0.4, 0.42))
save("washer_M8", ring(4.3, 8, 0, 1.6), "steel", (0.6, 0.6, 0.6))
lug = cq.Workplane("XY").center(1.5, 0).slot2D(20, 17).extrude(3.5).val().cut(cyl(4.25, -1, 5)) \
    .fuse(cq.Solid.makeCylinder(6.5, 13, V(9, 0, 1.75), V(1, 0, 0)))                       # palm round the hole, crimp barrel +x 9..22
lug = lug.cut(cq.Solid.makeCylinder(4.2, 14, V(11, 0, 1.75), V(1, 0, 0))).clean()
save("cable_lug_35mm2_M8", lug, "Cu", (0.85, 0.65, 0.35))
cable = cq.Solid.makeCylinder(6.0, 40, V(0, 0, 0), V(1, 0, 0))
save("cable_35mm2_stub", cable, "NBR", (0.05, 0.05, 0.05))
gl20 = cq.Solid.makeCylinder(9.75, 6, V(-6, 0, 0), V(1, 0, 0)).fuse(
    cq.Workplane("YZ").polygon(6, 24 / math.cos(math.pi / 6)).extrude(6).val()).fuse(
    cq.Solid.makeCylinder(11, 16, V(6, 0, 0), V(1, 0, 0)))
gl20 = gl20.cut(cq.Solid.makeCylinder(6.05, 40, V(-8, 0, 0), V(1, 0, 0))).clean()          # thread inward (-x), hex + dome outward
save("cable_gland_M20_IP68", gl20, "PA66GF30", (0.1, 0.1, 0.1))
gl16 = cq.Solid.makeCylinder(7.75, 4, V(-4, 0, 0), V(1, 0, 0)).fuse(
    cq.Workplane("YZ").polygon(6, 20 / math.cos(math.pi / 6)).extrude(5).val()).fuse(
    cq.Solid.makeCylinder(9, 12, V(5, 0, 0), V(1, 0, 0))).cut(cq.Solid.makeCylinder(3.5, 30, V(-8, 0, 0), V(1, 0, 0))).clean()
save("cable_gland_M16_IP68", gl16, "PA66GF30", (0.1, 0.1, 0.1))
at = lambda r, a, z: [r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z]
for net, a in STUD_ANG.items():
    place("stud_M8_press_in", Rz(a), at(R_STUD, a, zb0))
    place("cable_lug_35mm2_M8", Rz(a), at(R_STUD, a, zb1))          # palm on the bar, barrel radial out to the gland
    place("washer_M8", Rz(a), at(R_STUD, a, zb1 + 3.5))
    place("nut_M8_thin", Rz(a), at(R_STUD, a, zb1 + 5.1))
    place("cable_35mm2_stub", Rz(a), at(R_STUD + 22.0, a, Z_GLAND))
    place("cable_gland_M20_IP68", Rz(a), at(R_GLAND, a, Z_GLAND))
place("cable_gland_M16_IP68", Rz(ENC_ANG), at(R_GLAND, ENC_ANG, Z_GLAND))

# ================================================================ stator 65 mm (stretched variant-B parts)
for t in range(1, 13):
    for k in ("tooth_65", "bobbin_A_65", "bobbin_B_65", "04_coil_65"):
        place(k, Rz(30.0 * (t - 1) - 90.0))
for n in ("L1", "L2", "L3"):
    place("busbar_%s_65" % n)
for j in SP["straps"]:
    place("link_strap_65", Rz(j["mid"]))

json.dump({"parts": parts, "instances": inst, "dims": {
    "rotor_stack": STACK_R, "stator_stack": 65.0, "housing_front_face": Z_WALL_F[0], "hub_face": Z_SEAL[0],
    "rear_face": Z_REAR + COVER_T, "shaft_end_front": z_end_f, "bar_z": [zb0, zb1], "plane_top": ZP_TOP,
    "fin_r": FIN_R, "gland_r": R_GLAND}}, open(os.path.join(D, "instances.json"), "w"), indent=1)
tot = {}
for i in inst:
    p = parts.get(i["part"])
    if p:
        tot[p["mat"]] = tot.get(p["mat"], 0) + p["mass_g"]
for n, p in parts.items():
    print("%-26s %-9s %9.1f g  solids %d" % (n, p["mat"], p["mass_g"], p["solids"]))
print("new-part mass by material (all instances):", {k: round(v) for k, v in tot.items()})
print("instances:", len(inst))
