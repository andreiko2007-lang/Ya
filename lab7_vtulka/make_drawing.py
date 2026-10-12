"""Чертёж шлицевой втулки, ЛР №7, вариант 19 (ГОСТ 1139-80, средняя серия).

Строит один и тот же набор примитивов в два формата:
  * vtulka_v19.pdf / .png — для просмотра и печати (формат А4 вертикальный, масштаб 1:2);
  * vtulka_v19.dxf        — для открытия в КОМПАС-3D / AutoCAD (масштаб 1:1, мм).

Запуск:  python3 make_drawing.py
Зависимости: matplotlib, ezdxf, shapely.
"""
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Polygon as MplPolygon
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from shapely.geometry import Point, Polygon, LineString
from shapely import affinity

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- исходные данные
VAR = 19
Z, d, D, b, c, r = 8, 42.0, 48.0, 8.0, 0.4, 0.3   # табл. 2.1, вариант 19
L = 1.6 * D            # длина втулки            76,8
D_FL = 2.0 * D         # диаметр фланца          96
D_HUB = 1.5 * D        # диаметр ступицы         72
T_FL = 0.25 * D        # толщина фланца          12
CH = 1.0               # фаска на входе в отверстие 1x45°
DENSITY = 7.85e-3      # г/мм^3, сталь 08

# ---------------------------------------------------------------- примитивы
S_MAIN, S_THIN, S_CUT = 0.7, 0.25, 1.0   # толщины линий, мм
HATCH_STEP = 2.0
FONT = FontProperties(family="DejaVu Sans", style="italic")
CAP = 0.729                              # высота прописной буквы / кегль (DejaVu Sans)


def text_width(s, h):
    """Ширина надписи (мм) при высоте прописных букв h."""
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=h / CAP, prop=FONT).get_extents().x1


class Sheet:
    def __init__(self):
        self.items = []

    def pl(self, pts, lt="thin", closed=False):
        self.items.append(("pl", [tuple(p) for p in pts], lt, closed))

    def line(self, p, q, lt="thin"):
        self.pl([p, q], lt)

    def circle(self, cxy, rad, lt="main"):
        self.items.append(("circle", tuple(cxy), rad, lt))

    def fill(self, pts):
        self.items.append(("fill", [tuple(p) for p in pts]))

    def text(self, p, s, h=3.5, ang=0.0, ha="left", va="bottom", fit=None):
        """fit — максимальная ширина, мм: длинная надпись сжимается по ширине."""
        wf = 1.0
        if fit is not None:
            wf = min(1.0, fit / text_width(s, h))
        self.items.append(("text", tuple(p), s, h, ang, ha, va, wf))

    # --- составные элементы
    def arrow(self, tip, direction, length=3.5, width=1.0):
        ux, uy = unit(direction)
        nx, ny = -uy, ux
        bx, by = tip[0] - ux * length, tip[1] - uy * length
        self.fill([tip, (bx + nx * width / 2, by + ny * width / 2),
                   (bx - nx * width / 2, by - ny * width / 2)])

    def hatch(self, geom, angle=45.0, step=HATCH_STEP):
        minx, miny, maxx, maxy = geom.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        R = math.hypot(maxx - minx, maxy - miny)
        a = math.radians(angle)
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        # привязка штриховки к общей сетке, чтобы линии в соседних
        # областях одной детали совпадали
        k0 = math.floor(((cx * nx + cy * ny) - R) / step)
        k1 = math.ceil(((cx * nx + cy * ny) + R) / step)
        for k in range(k0, k1 + 1):
            off = k * step
            px, py = nx * off, ny * off
            t = (cx - px) * ux + (cy - py) * uy
            seg = LineString([(px + ux * (t - R), py + uy * (t - R)),
                              (px + ux * (t + R), py + uy * (t + R))])
            for part in iter_lines(seg.intersection(geom)):
                self.pl(list(part.coords), "thin")

    def dim_linear(self, a, b_, n, off, text, ext_from=None, text_shift=0.0):
        """Линейный размер между a и b_; n — единичная нормаль в сторону размерной линии."""
        ux, uy = unit((b_[0] - a[0], b_[1] - a[1]))
        pa = (a[0] + n[0] * off, a[1] + n[1] * off)
        pb = (b_[0] + n[0] * off, b_[1] + n[1] * off)
        for p, q in ((a, pa), (b_, pb)):
            start = (p[0] + n[0] * 0.0, p[1] + n[1] * 0.0)
            self.line(start, (q[0] + n[0] * 2, q[1] + n[1] * 2))
        self.line(pa, pb)
        self.arrow(pa, (-ux, -uy))
        self.arrow(pb, (ux, uy))
        ang = math.degrees(math.atan2(uy, ux))
        if ang > 90.0001 or ang <= -90.0001:
            ang += 180
        ang = (ang + 180) % 360 - 180
        ra = math.radians(ang)
        tx, ty = -math.sin(ra), math.cos(ra)   # «верх» текста
        mx = (pa[0] + pb[0]) / 2 + math.cos(ra) * text_shift + tx * 1.0
        my = (pa[1] + pb[1]) / 2 + math.sin(ra) * text_shift + ty * 1.0
        self.text((mx, my), text, ang=ang, ha="center", va="bottom")

    def leader(self, tip, knee, shelf_len, text, to_right=True, arrow=True, h=3.5):
        self.line(tip, knee)
        if arrow:
            self.arrow(tip, (tip[0] - knee[0], tip[1] - knee[1]))
        shelf_len = max(shelf_len, text_width(text, h) + 2.5)
        end = (knee[0] + (shelf_len if to_right else -shelf_len), knee[1])
        self.line(knee, end)
        x0 = min(knee[0], end[0])
        self.text((x0 + 1.0, knee[1] + 1.0), text, h=h)


def unit(v):
    l = math.hypot(*v)
    return v[0] / l, v[1] / l


def iter_lines(g):
    if g.is_empty:
        return
    if g.geom_type == "LineString":
        yield g
    elif hasattr(g, "geoms"):
        for x in g.geoms:
            yield from iter_lines(x)


def circle_pts(cxy, rad, n=360):
    return [(cxy[0] + rad * math.cos(2 * math.pi * i / n),
             cxy[1] + rad * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---------------------------------------------------------------- профиль шлицевого отверстия
def spline_hole(z=Z, d=d, D=D, b=b, c=c, r=r, phase=90.0):
    """Замкнутый контур отверстия ступицы (пазы по D, выступы по d)."""
    Rd, RD, hb = d / 2, D / 2, b / 2
    # фаска c на кромке паза у диаметра d
    u_ch_wall = math.sqrt(Rd ** 2 - hb ** 2) + c
    v_ch_arc = hb + c
    # скругление r в углу паза у диаметра D
    vc = hb - r
    uc = math.sqrt((RD - r) ** 2 - vc ** 2)
    pts = []

    def P(phi, v, u):
        cph, sph = math.cos(phi), math.sin(phi)
        return (u * cph - v * sph, u * sph + v * cph)

    step = 2 * math.pi / z
    for k in range(z):
        phi = math.radians(phase) + k * step
        # фаска (сторона -v)
        pts.append(P(phi, -v_ch_arc, math.sqrt(Rd ** 2 - v_ch_arc ** 2)))
        pts.append(P(phi, -hb, u_ch_wall))
        # стенка и скругление
        pts.append(P(phi, -hb, uc))
        a_end = math.atan2(uc, -vc)          # направление на точку касания с окружностью D
        for i in range(1, 6):
            a = math.pi + (a_end - math.pi) * i / 6
            pts.append(P(phi, -vc + r * math.cos(a), uc + r * math.sin(a)))
        # дно паза по D
        g0 = math.atan2(-vc * RD / (RD - r), uc * RD / (RD - r))
        for i in range(0, 13):
            g = g0 + (-2 * g0) * i / 12
            pts.append(P(phi, RD * math.sin(g), RD * math.cos(g)))
        for i in range(1, 6):
            a = (math.pi - a_end) + (0 - (math.pi - a_end)) * i / 6
            pts.append(P(phi, vc + r * math.cos(a), uc + r * math.sin(a)))
        pts.append(P(phi, hb, uc))
        pts.append(P(phi, hb, u_ch_wall))
        pts.append(P(phi, v_ch_arc, math.sqrt(Rd ** 2 - v_ch_arc ** 2)))
        # выступ ступицы по d до следующего паза
        a0 = phi + math.asin(v_ch_arc / Rd)
        a1 = phi + step - math.asin(v_ch_arc / Rd)
        for i in range(1, 24):
            a = a0 + (a1 - a0) * i / 24
            pts.append((Rd * math.cos(a), Rd * math.sin(a)))
    return pts


HOLE = spline_hole()
HOLE_POLY = Polygon(HOLE)

# ---------------------------------------------------------------- лист
sh = Sheet()
W, H = 210.0, 297.0            # формат А4 (вертикальный, ГОСТ 2.301)
S = 0.5                        # масштаб главного вида и разреза 1:2

# рамка и дополнительные графы (ГОСТ 2.104)
sh.pl([(0, 0), (W, 0), (W, H), (0, H)], "thin", closed=True)
sh.pl([(20, 5), (W - 5, 5), (W - 5, H - 5), (20, H - 5)], "main", closed=True)
sh.text((W - 5 - 25, 1.2), "Формат А4", h=2.5, ha="right")
sh.text((W - 5 - 110, 1.2), "Копировал", h=2.5, ha="left")
# графа 26 — обозначение документа, повёрнутое на 180°
sh.pl([(20, H - 5), (90, H - 5), (90, H - 19), (20, H - 19)], "main", closed=True)
# боковые графы 19–23 (снизу) и графы 31–32 (сверху)
for y0, y1, labels in ((5, 150, ((25, "Инв. № подл."), (35, "Подп. и дата"), (25, "Взам. инв. №"),
                                  (25, "Инв. № дубл."), (35, "Подп. и дата"))),
                       (172, 292, ((60, "Справ. №"), (60, "Перв. примен.")))):
    sh.pl([(8, y0), (8, y1), (20, y1)], "main")
    sh.line((13, y0), (13, y1), "main")
    sh.line((8, y0), (20, y0), "main")
    y = y0
    for hgt, lab in labels:
        sh.line((8, y + hgt), (20, y + hgt), "main")
        sh.text((12, y + hgt / 2), lab, h=2.5, ang=90, ha="center", fit=hgt - 3)
        y += hgt

# ---- главный вид: фронтальный разрез (плоскость симметрии), 1:2
X0, Y0 = 60.0, 210.0


def M(x, y):
    """Точка детали (мм) -> точка листа."""
    return (X0 + S * x, Y0 + S * y)


Rd, RD, Rh, Rf = d / 2, D / 2, D_HUB / 2, D_FL / 2
for s in (1, -1):
    # наружный контур и торцы
    sh.pl([M(0, s * (Rd + CH)), M(0, s * Rf), M(T_FL, s * Rf), M(T_FL, s * Rh),
           M(L, s * Rh), M(L, s * (Rd + CH))], "main")
    # поверхность по D (граница штриховки) и по d (зубья не рассекаются, ГОСТ 2.409)
    sh.line(M(0, s * RD), M(L, s * RD), "main")
    sh.pl([M(0, s * (Rd + CH)), M(CH, s * Rd), M(L - CH, s * Rd), M(L, s * (Rd + CH))], "main")
    sh.hatch(Polygon([M(0, s * RD), M(0, s * Rf), M(T_FL, s * Rf), M(T_FL, s * Rh),
                      M(L, s * Rh), M(L, s * RD)]))
sh.line((X0 - 5, Y0), (M(L, 0)[0] + 5, Y0), "center")

# размеры главного вида (отступы — в мм листа, числа — натуральные размеры)
sh.dim_linear(M(0, -Rf), M(0, Rf), (-1, 0), 10, "⌀96")
sh.dim_linear(M(L, -Rh), M(L, Rh), (1, 0), 10, "⌀72")
# толщина фланца 12 — короткий размер, стрелки снаружи
y12 = M(0, Rf)[1] + 8
xa, xb = M(0, 0)[0], M(T_FL, 0)[0]
sh.line(M(0, Rf), (xa, y12 + 2))
sh.line(M(T_FL, Rf), (xb, y12 + 2))
sh.line((xa - 6, y12), (xb + 6, y12))
sh.arrow((xa, y12), (1, 0))
sh.arrow((xb, y12), (-1, 0))
sh.text(((xa + xb) / 2, y12 + 1), "12", ha="center")
# длина 76,8 — над размером 12
y_dim = y12 + 10
xe = M(L, 0)[0]
sh.line((xa, y12 + 2), (xa, y_dim + 2))
sh.line(M(L, Rh), (xe, y_dim + 2))
sh.line((xa, y_dim), (xe, y_dim))
sh.arrow((xa, y_dim), (-1, 0))
sh.arrow((xe, y_dim), (1, 0))
sh.text(((xa + xe) / 2, y_dim + 1), "76,8", ha="center")
# обозначение шлицевого профиля (выноска вниз)
sh.leader(M(15, -Rd), (M(40, 0)[0], M(0, -Rf)[1] - 22), 36, "d-8×42H7×48H12×8D9")

# след секущей плоскости А-А
xc = M(72.0, 0)[0]
for s in (1, -1):
    y_in = Y0 + s * (S * Rh + 3)
    y_out = Y0 + s * (S * Rh + 14)
    sh.line((xc, y_in), (xc, y_out), "cut")
    ya = Y0 + s * (S * Rh + 12)
    sh.line((xc, ya), (xc - 9, ya), "thin")
    sh.arrow((xc - 9, ya), (-1, 0), length=4.0, width=1.4)
    sh.text((xc - 4.5, ya + (1.5 if s > 0 else -6.5)), "А", h=5, ha="center")

# ---- разрез А-А, 1:2
CX, CY = 162.0, Y0


def A(p):
    return (CX + S * p[0], CY + S * p[1])


sh.text((CX, CY + S * Rf + 8), "А–А", h=5, ha="center")
sh.circle((CX, CY), S * Rf, "main")      # фланец за секущей плоскостью
sh.circle((CX, CY), S * Rh, "main")
sh.pl([A(p) for p in HOLE], "main", closed=True)
hole_A = affinity.affine_transform(HOLE_POLY, [S, 0, 0, S, CX, CY])
ring = Point(CX, CY).buffer(S * Rh, 256).difference(hole_A)
sh.hatch(ring)
sh.line((CX - S * Rf - 4, CY), (CX + S * Rf + 4, CY), "center")
sh.line((CX, CY - S * Rf - 4), (CX, CY + S * Rf + 4), "center")


def dia_dim(angle_deg, rad, rout, text, to_right):
    """rad — радиус детали (мм), rout — вынос полки в мм листа от центра."""
    a = math.radians(angle_deg)
    u = (math.cos(a), math.sin(a))
    p1 = (CX - u[0] * S * rad, CY - u[1] * S * rad)
    p2 = (CX + u[0] * S * rad, CY + u[1] * S * rad)
    p3 = (CX + u[0] * rout, CY + u[1] * rout)
    sh.line(p1, p3)
    sh.arrow(p1, (-u[0], -u[1]), length=2.5, width=0.8)
    sh.arrow(p2, u, length=2.5, width=0.8)
    shelf = text_width(text, 3.5) + 2.5
    end = (p3[0] + (shelf if to_right else -shelf), p3[1])
    sh.line(p3, end)
    sh.text((min(p3[0], end[0]) + 1, p3[1] + 1), text)


dia_dim(45.0, RD, S * Rf + 10, "⌀48", True)
dia_dim(202.5, Rd, S * Rf + 12, "⌀42", False)

# обозначение выносного элемента Б
PB = (0.0, (Rd + RD) / 2)
RB = 6.0                                  # радиус зоны элемента, мм детали
sh.circle(A(PB), S * RB, "thin")
kb = (A(PB)[0] - S * RB * 0.5, A(PB)[1] + S * RB * 0.866)
kn = (kb[0] - 12, kb[1] + 20)
sh.line(kb, kn)
sh.line(kn, (kn[0] - 8, kn[1]))
sh.text((kn[0] - 4, kn[1] + 1), "Б", h=5, ha="center")

# ---- выносной элемент Б (4:1)
K = 4.0
C3 = (82.0, 104.0)


def Bx(p):
    return (C3[0] + K * (p[0] - PB[0]), C3[1] + K * (p[1] - PB[1]))


sh.text((C3[0], C3[1] + K * RB + 6), "Б (4 : 1)", h=5, ha="center")
wavy = Polygon([(C3[0] + (K * RB + 0.5 * math.sin(12 * t)) * math.cos(t),
                 C3[1] + (K * RB + 0.5 * math.sin(12 * t)) * math.sin(t))
                for t in [2 * math.pi * i / 720 for i in range(720)]])
sh.pl(list(wavy.exterior.coords), "thin", closed=True)
hole_B = affinity.affine_transform(HOLE_POLY, [K, 0, 0, K, C3[0] - K * PB[0], C3[1] - K * PB[1]])
for seg in iter_lines(LineString(list(hole_B.exterior.coords)).intersection(wavy)):
    sh.pl(list(seg.coords), "main")
sh.hatch(wavy.difference(hole_B))
sh.line((C3[0], C3[1] - K * RB - 3), (C3[0], C3[1] + K * RB + 3), "center")
# размер b = 8 (внутри отверстия)
yb_corner = math.sqrt(Rd ** 2 - (b / 2) ** 2)
pL, pR = Bx((-b / 2, yb_corner + c)), Bx((b / 2, yb_corner + c))
yb = C3[1] - 13
sh.line(pL, (pL[0], yb - 2))
sh.line(pR, (pR[0], yb - 2))
sh.line((pL[0], yb), (pR[0], yb))
sh.arrow((pL[0], yb), (-1, 0))
sh.arrow((pR[0], yb), (1, 0))
sh.text((C3[0] + 4, yb + 1), "8", ha="center")
# R0,3 в углу паза у D (левый угол, выноска влево)
vc = b / 2 - r
uc = math.sqrt((RD - r) ** 2 - vc ** 2)
fil = Bx((-(vc + r * 0.707), uc + r * 0.707))
sh.leader(fil, (C3[0] - 28, C3[1] + 26), 12, "R0,3", to_right=False)
# фаска c у d (левая кромка, выноска влево)
chp = Bx((-(b / 2 + c / 2), yb_corner + c / 2))
sh.leader(chp, (C3[0] - 26, C3[1] - 22), 12, "0,4×45°", to_right=False)

# ---- технические требования
mass = (Point(0, 0).buffer(Rf, 512).difference(HOLE_POLY).area * T_FL
        + Point(0, 0).buffer(Rh, 512).difference(HOLE_POLY).area * (L - T_FL)) * DENSITY
tt = [
    "1. Соединение шлицевое",
    "    прямобочное, средняя серия,",
    "    ГОСТ 1139-80.",
    "2. Центрирование по",
    "    внутреннему диаметру d.",
    "3. Фаски на входе в шлицевое",
    "    отверстие 1×45°, 2 места.",
    "4. Неуказанные предельные",
    "    отклонения размеров:",
    "    H14, h14, ±IT14/2.",
    "5. Острые кромки притупить.",
]
for i, s in enumerate(tt):
    sh.text((122, 146 - i * 6), s, h=3.5, fit=W - 5 - 124)

# ---- основная надпись (ГОСТ 2.104, форма 1), 185 x 55
TX, TY = W - 5 - 185, 5


def T(x, y):
    return (TX + x, TY + y)


sh.pl([T(0, 0), T(185, 0), T(185, 55), T(0, 55)], "main", closed=True)
for x in (7, 17, 40, 55, 65):
    sh.line(T(x, 55), T(x, 0) if x in (17, 40, 55, 65) else T(x, 30), "main")
sh.line(T(7, 30), T(7, 55), "main")
for y in (5, 10, 15, 20, 25, 30, 35, 40, 45, 50):
    lt = "main" if y in (30, 35) else "thin"
    sh.line(T(0, y), T(65, y), lt)
sh.line(T(65, 40), T(185, 40), "main")
sh.line(T(65, 15), T(185, 15), "main")
sh.line(T(135, 40), T(135, 0), "main")
sh.line(T(135, 35), T(185, 35), "main")
sh.line(T(135, 20), T(185, 20), "main")
sh.line(T(150, 40), T(150, 20), "main")
sh.line(T(167, 40), T(167, 20), "main")
sh.line(T(140, 35), T(140, 20), "thin")
sh.line(T(145, 35), T(145, 20), "thin")
sh.line(T(155, 20), T(155, 15), "main")
for x, w, s in ((3.5, 7, "Изм."), (12, 10, "Лист"), (28.5, 23, "№ докум."),
                (47.5, 15, "Подп."), (60, 10, "Дата")):
    sh.text(T(x, 31.2), s, h=2.5, ha="center", fit=w - 2.4)
for i, s in enumerate(("Разраб.", "Пров.", "Т.контр.", "", "Н.контр.", "Утв.")):
    if s:
        sh.text(T(1.0, 26.2 - 5 * i), s, h=2.5, fit=14.4)
for i, s in enumerate(("Шлейко И. Ю.", "Кулькова В. В.")):
    sh.text(T(18.0, 26.2 - 5 * i), s, h=2.5, fit=21.0)
sh.text(T(142.5, 36.2), "Лит.", h=2.5, ha="center", fit=12.5)
sh.text(T(158.5, 36.2), "Масса", h=2.5, ha="center", fit=14.5)
sh.text(T(176, 36.2), "Масштаб", h=2.5, ha="center", fit=15.0)
sh.text(T(136.5, 16.2), "Лист", h=2.5, fit=18)
sh.text(T(157, 16.2), "Листов", h=2.5, fit=27)

# ---------------------------------------------------------------- вывод: PDF / PNG
plt.rcParams["lines.scale_dashes"] = False
MM2PT = 72 / 25.4
LW = {"main": S_MAIN, "thin": S_THIN, "center": S_THIN, "cut": S_CUT}
DASH = {"center": (0, (12 * MM2PT, 1.5 * MM2PT, 0.6 * MM2PT, 1.5 * MM2PT))}


def render_mpl(path_pdf, path_png):
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    for it in sh.items:
        kind = it[0]
        if kind == "pl":
            pts, lt, closed = it[1], it[2], it[3]
            if closed:
                pts = pts + [pts[0]]
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color="black", lw=LW[lt] * MM2PT,
                    linestyle=DASH.get(lt, "solid"), solid_capstyle="butt",
                    solid_joinstyle="miter")
        elif kind == "circle":
            pts = circle_pts(it[1], it[2]) + [circle_pts(it[1], it[2])[0]]
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color="black", lw=LW[it[3]] * MM2PT)
        elif kind == "fill":
            ax.add_patch(MplPolygon(it[1], closed=True, color="black", lw=0))
        elif kind == "text":
            _, p, s, h, ang, ha, va, wf = it
            if not s:
                continue
            path = TextPath((0, 0), s, size=h / CAP, prop=FONT)
            w = path.get_extents().x1 * wf
            dx = {"left": 0.0, "center": -w / 2, "right": -w}[ha]
            tr = (Affine2D().scale(wf, 1).translate(dx, 0).rotate_deg(ang)
                  .translate(*p) + ax.transData)
            ax.add_patch(PathPatch(path, transform=tr, color="black", lw=0))
    fig.savefig(path_pdf)
    fig.savefig(path_png, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- вывод: DXF
def render_dxf(path):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$LTSCALE"] = 1.0
    doc.linetypes.add("GOST_AXIS", pattern=[15.6, 12.0, -1.5, 0.6, -1.5],
                      description="Осевая ___ . ___ . ___")
    doc.styles.add("GOST", font="isocpeur.ttf")
    layers = {
        "main": ("Основная", "CONTINUOUS", 70),
        "thin": ("Тонкая", "CONTINUOUS", 25),
        "center": ("Осевая", "GOST_AXIS", 25),
        "cut": ("Разомкнутая", "CONTINUOUS", 100),
    }
    for name, lt, lw in layers.values():
        doc.layers.add(name, linetype=lt, lineweight=lw)
    doc.layers.add("Текст", lineweight=25)
    msp = doc.modelspace()
    align = {("left", "bottom"): TextEntityAlignment.BOTTOM_LEFT,
             ("center", "bottom"): TextEntityAlignment.BOTTOM_CENTER,
             ("right", "bottom"): TextEntityAlignment.BOTTOM_RIGHT,
             ("center", "center"): TextEntityAlignment.MIDDLE_CENTER}
    for it in sh.items:
        kind = it[0]
        if kind == "pl":
            pts, lt, closed = it[1], it[2], it[3]
            if len(pts) == 2 and not closed:
                msp.add_line(pts[0], pts[1], dxfattribs={"layer": layers[lt][0]})
            else:
                msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layers[lt][0]})
        elif kind == "circle":
            msp.add_circle(it[1], it[2], dxfattribs={"layer": layers[it[3]][0]})
        elif kind == "fill":
            hatch = msp.add_hatch(color=7, dxfattribs={"layer": "Тонкая"})
            hatch.paths.add_polyline_path(it[1], is_closed=True)
        elif kind == "text":
            _, p, s, h, ang, ha, va, wf = it
            if not s:
                continue
            t = msp.add_text(s, height=h, rotation=ang,
                             dxfattribs={"layer": "Текст", "style": "GOST", "oblique": 15,
                                         "width": round(wf, 3)})
            t.set_placement(p, align=align[(ha, va)])
    doc.saveas(path)


if __name__ == "__main__":
    render_mpl(OUT / "vtulka_v19.pdf", OUT / "vtulka_v19.png")
    render_dxf(OUT / "vtulka_v19.dxf")
    print(f"Масса ≈ {mass:.0f} г")
