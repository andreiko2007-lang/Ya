"""Лабораторная работа №1 «Построение примитивов в системе КОМПАС 3D».

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_lr1.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR1_Vasilieva.dxf"

doc = ezdxf.new("R2010", setup=True)
doc.header["$INSUNITS"] = 4  # мм
doc.header["$LWDISPLAY"] = 1
msp = doc.modelspace()

# ---------------------------------------------------------------- стили
doc.styles.new("GOST", dxfattribs={"font": "GOST type A.ttf", "width": 1.0, "oblique": 15})
doc.linetypes.add("AXIS", pattern=[25.0, 20.0, -3.0, 2.0, -3.0], description="Осевая __ . __")
doc.linetypes.add("HID", pattern=[6.0, 4.0, -2.0], description="Штриховая -- -- --")

LAYERS = {
    "Основная": dict(color=7, lineweight=50, linetype="Continuous"),
    "Тонкая": dict(color=7, lineweight=25, linetype="Continuous"),
    "Осевая": dict(color=1, lineweight=25, linetype="AXIS"),
    "Штриховая": dict(color=5, lineweight=25, linetype="HID"),
    "Штриховка": dict(color=8, lineweight=25, linetype="Continuous"),
    "Размеры": dict(color=3, lineweight=25, linetype="Continuous"),
    "Обозначения": dict(color=3, lineweight=25, linetype="Continuous"),
    "Рамка": dict(color=7, lineweight=50, linetype="Continuous"),
    "Рамка_тонкая": dict(color=7, lineweight=25, linetype="Continuous"),
}
for name, a in LAYERS.items():
    doc.layers.add(name, color=a["color"], linetype=a["linetype"]).dxf.lineweight = a["lineweight"]

ds = doc.dimstyles.new("ГОСТ")
ds.dxf.dimtxsty = "GOST"
ds.dxf.dimtxt = 3.5
ds.dxf.dimasz = 3.0
ds.dxf.dimexe = 2.0
ds.dxf.dimexo = 0.0
ds.dxf.dimgap = 1.0
ds.dxf.dimtad = 1
ds.dxf.dimtih = 0
ds.dxf.dimtoh = 0
ds.dxf.dimdec = 1
ds.dxf.dimzin = 8
ds.dxf.dimdsep = ord(",")
ds.dxf.dimlwd = 25
ds.dxf.dimlwe = 25
ds.dxf.dimclrd = 3
ds.dxf.dimclre = 3
ds.dxf.dimclrt = 3
ds.dxf.dimtmove = 0
ds.dxf.dimatfit = 3

DIA = "%%c"
SQ = "□"


# ---------------------------------------------------------------- помощники
def mk(ox, oy, rot=0, mirror=False):
    """Функции рисования в локальной системе вида с началом (ox, oy),
    повёрнутой на rot градусов (кратно 90) против часовой стрелки;
    mirror=True — предварительно отразить относительно оси X."""
    ca, sa = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    m = -1 if mirror else 1

    def P(x, y):
        y *= m
        return (ox + x * ca - y * sa, oy + x * sa + y * ca)

    def A(a):
        """Угол направления из локальной системы в систему листа."""
        return (m * a + rot) % 360

    def nrot(a):
        """Направление текста/размера без перевёрнутых надписей."""
        a = A(a)
        return a - 180 if 90 < a <= 270 else a

    def line(x1, y1, x2, y2, layer="Основная"):
        msp.add_line(P(x1, y1), P(x2, y2), dxfattribs={"layer": layer})

    def poly(pts, layer="Основная", closed=False):
        msp.add_lwpolyline([P(*p) for p in pts], close=closed, dxfattribs={"layer": layer})

    def circle(x, y, r, layer="Основная"):
        msp.add_circle(P(x, y), r, dxfattribs={"layer": layer})

    def arc(x, y, r, a1, a2, layer="Основная"):
        if abs(a2 - a1) >= 360:                      # полная окружность
            msp.add_circle(P(x, y), r, dxfattribs={"layer": layer})
            return
        if mirror:
            a1, a2 = a2, a1
        msp.add_arc(P(x, y), r, A(a1), A(a2), dxfattribs={"layer": layer})

    def hatch(pts, angle=45, spacing=2.0):
        h = msp.add_hatch(dxfattribs={"layer": "Штриховка"})
        h.set_pattern_fill("ANSI31", scale=spacing / 3.175, angle=angle - 45)
        h.paths.add_polyline_path([P(*p) for p in pts], is_closed=True)

    def dim_lin(p1, p2, base, angle=0, text="<>"):
        d = msp.add_linear_dim(base=P(*base), p1=P(*p1), p2=P(*p2), angle=A(angle) % 180,
                               text=text, dimstyle="ГОСТ", dxfattribs={"layer": "Размеры"})
        d.render()

    def dim_dia(cx, cy, r, ang, text="<>", loc=None):
        kw = {"location": P(*loc)} if loc else {"angle": A(ang)}
        d = msp.add_diameter_dim(center=P(cx, cy), radius=r, text=text, **kw,
                                 dimstyle="ГОСТ", override={"dimtmove": 1, "dimtofl": 1},
                                 dxfattribs={"layer": "Размеры"})
        d.render()

    def dim_rad(cx, cy, r, ang, text="<>"):
        d = msp.add_radius_dim(center=P(cx, cy), radius=r, angle=A(ang), text=text,
                               dimstyle="ГОСТ", override={"dimtmove": 1},
                               dxfattribs={"layer": "Размеры"})
        d.render()

    def text(x, y, s, h=3.5, layer="Размеры", align=TextEntityAlignment.LEFT, rot=0, width=1.0):
        rot_t = rot
        t = msp.add_text(s, height=h, rotation=nrot(rot_t),
                         dxfattribs={"layer": layer, "style": "GOST", "width": width})
        t.set_placement(P(x, y), align=align)

    return P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text




# ================================================================ СОДЕРЖИМОЕ ЛИСТА (по образцу рис. 2.7)
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(0, 0)


def arrow(tx, ty, dx, dy):
    """Стрелка с остриём в (tx, ty), направленная вдоль (dx, dy)."""
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    bx, by = tx - 3 * dx, ty - 3 * dy
    h = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
    h.paths.add_polyline_path([P(tx, ty), P(bx - 0.5 * dy, by + 0.5 * dx),
                               P(bx + 0.5 * dy, by - 0.5 * dx)], is_closed=True)


def rad_shelf(cx, cy, r, ang, label, side, from_center=True, knee=6.0, shelf=14.0):
    """Радиус с выноской на полку: side = -1 полка влево, +1 вправо."""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    kx, ky = cx + (r + knee) * c, cy + (r + knee) * s
    ax, ay = cx + r * c, cy + r * s
    if from_center:                      # линия от центра, стрелка на дуге наружу
        line(cx, cy, kx, ky, "Размеры")
        arrow(ax, ay, c, s)
    else:                                # стрелка снаружи к дуге (к центру)
        line(cx + (r - 5) * c, cy + (r - 5) * s, kx, ky, "Размеры")
        arrow(ax, ay, -c, -s)
    ex = kx + side * shelf
    line(kx, ky, ex, ky, "Размеры")
    text((kx + ex) / 2, ky + 1, label, align=TextEntityAlignment.BOTTOM_CENTER)


def chamfer_dim(x1, x2, y_from1, y_from2, y_dim, label, shelf=16.0):
    """Размер фаски: выносные линии вверх/вниз, стрелки снаружи, надпись на полке справа."""
    line(x1, y_from1, x1, y_dim + (2 if y_dim > y_from1 else -2), "Размеры")
    line(x2, y_from2, x2, y_dim + (2 if y_dim > y_from2 else -2), "Размеры")
    line(x1 - 7, y_dim, x2 + shelf, y_dim, "Размеры")
    arrow(x1, y_dim, 1, 0)
    arrow(x2, y_dim, -1, 0)
    text(x2 + 2, y_dim + 1, label)


# --- 2. Отрезки AB, AC ⟂ AB, BM ∥ AC; скругление R10 в точке A, фаска 4×45° в точке B
AX, AY = 36.0, 258.0
BX = AX + 40.0                        # AB = 40
SEG = 26.0                            # длина AC и BM (по образцу)
RF, CHB = 10.0, 4.0
line(AX + RF, AY, BX - CHB, AY)
arc(AX + RF, AY - RF, RF, 90, 180)
line(AX, AY - RF, AX, AY - SEG)
line(BX - CHB, AY, BX, AY - CHB)
line(BX, AY - CHB, BX, AY - SEG)
text(AX + 1, AY + 5, "A", h=5, layer="Обозначения")
text(BX + 1.5, AY + 1, "B", h=5, layer="Обозначения")
text(AX - 6, AY - SEG, "C", h=5, layer="Обозначения")
text(BX + 3, AY - SEG, "M", h=5, layer="Обозначения")
rad_shelf(AX + RF, AY - RF, RF, 135, "R10", -1, from_center=False, knee=4.0, shelf=12.0)
chamfer_dim(BX - CHB, BX, AY, AY - CHB, AY + 13, "4×45°")

# --- 3. Концентрические окружности (средняя — осевой линией)
CX, CY = 181.0, 246.0
circle(CX, CY, 20.0)
circle(CX, CY, 15.0, "Осевая")
circle(CX, CY, 10.0)

# --- 5. Сопряжение: окружности R20 и R10 (межцентровое 30), касательная и скругление R5
OX, OY = 112.0, 248.0
R1, R2, D, R3 = 20.0, 10.0, 30.0, 5.0
phi = math.asin((R1 - R2) / D)
nx, ny = math.sin(phi), math.cos(phi)
t1 = (OX + R1 * nx, OY + R1 * ny)
t2 = (OX + D + R2 * nx, OY + R2 * ny)
line(*t1, *t2)
fx = ((R1 + R3) ** 2 - (R2 + R3) ** 2 + D ** 2) / (2 * D)
fy = -math.sqrt((R1 + R3) ** 2 - fx ** 2)
f1 = (fx * R1 / (R1 + R3), fy * R1 / (R1 + R3))
f2 = (D + (fx - D) * R2 / (R2 + R3), fy * R2 / (R2 + R3))
a_t = math.degrees(math.atan2(ny, nx))
arc(OX, OY, R1, a_t, math.degrees(math.atan2(f1[1], f1[0])))
arc(OX + D, OY, R2, math.degrees(math.atan2(f2[1], f2[0] - D)), a_t)
arc(OX + fx, OY + fy, R3,
    math.degrees(math.atan2(f2[1] - fy, f2[0] - fx)),
    math.degrees(math.atan2(f1[1] - fy, f1[0] - fx)))
line(OX - R1 - 4, OY, OX + D + R2 + 4, OY, "Осевая")
line(OX, OY - R1 - 4, OX, OY, "Осевая")
line(OX + D, OY - R2 - 2, OX + D, OY, "Осевая")
# размер 30 между центрами
YD = OY + R1 + 10
line(OX, OY, OX, YD + 2, "Размеры")
line(OX + D, OY, OX + D, YD + 2, "Размеры")
line(OX, YD, OX + D, YD, "Размеры")
arrow(OX, YD, -1, 0)
arrow(OX + D, YD, 1, 0)
text(OX + D / 2, YD + 1, "30", align=TextEntityAlignment.BOTTOM_CENTER)
rad_shelf(OX, OY, R1, 105, "R20", -1, knee=5.0, shelf=11.0)
rad_shelf(OX + D, OY, R2, 50, "R10", +1, knee=7.0, shelf=12.0)
# R5: линия через центр скругления, стрелка на дуге, надпись вдоль линии
a5 = 125.0
c5, s5 = math.cos(math.radians(a5)), math.sin(math.radians(a5))
gx, gy = OX + fx, OY + fy
line(gx + R3 * c5, gy + R3 * s5, gx - 13 * c5, gy - 13 * s5, "Размеры")
arrow(gx + R3 * c5, gy + R3 * s5, c5, s5)
text(gx - 8 * c5 + 1.2 * s5, gy - 8 * s5 - 1.2 * c5, "R5", rot=a5,
     align=TextEntityAlignment.BOTTOM_CENTER)

# --- 6. Типовая деталь (втулка) — начерчена в масштабе 2:1, размеры в натуральную величину
K = 2.0
MX, MY = 64.0, 150.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY)


def S(x, y):
    return (x * K, y * K)


def dl(p1, p2, base, angle=0, txt="<>"):
    d = msp.add_linear_dim(base=P(*base), p1=P(*p1), p2=P(*p2), angle=angle, text=txt,
                           dimstyle="ГОСТ", override={"dimlfac": 1 / K},
                           dxfattribs={"layer": "Размеры"})
    d.render()


L, T_FL = 40.0, 10.0
R_FL, R_B, R_IN, CH = 30.0, 25.0, 15.0, 2.5
# верхняя половина — вид (как на образце)
poly([S(0, 0), S(0, R_FL), S(T_FL, R_FL), S(T_FL, R_B), S(L, R_B), S(L, 0)])
line(*S(T_FL, R_B), *S(T_FL, 0))
# нижняя половина — разрез
sec = [S(0, -R_IN), S(L - CH, -R_IN), S(L, -(R_IN + CH)), S(L, -R_B), S(T_FL, -R_B),
       S(T_FL, -R_FL), S(0, -R_FL)]
poly(sec, closed=True)
hatch(sec)
line(*S(0, -R_IN), *S(0, 0))
line(*S(L - CH, -R_IN), *S(L - CH, 0))
line(-6, 0, L * K + 6, 0, "Осевая")
# размеры
dl(S(0, R_FL), S(0, -R_FL), (-18, 0), angle=90, txt=DIA + "60")
dl(S(L, R_B), S(L, -R_B), (L * K + 14, 0), angle=90, txt=DIA + "50")
dl(S(T_FL, -R_B), S(L, -R_B), (0, -R_FL * K - 12))        # 30
dl(S(0, -R_FL), S(L, -R_B), (0, -R_FL * K - 24))          # 40
# Ø30 — полуразмер снаружи слева
XD = -8.0
line(0, -R_IN * K, XD - 2, -R_IN * K, "Размеры")
line(XD, 2, XD, -R_IN * K, "Размеры")
arrow(XD, -R_IN * K, 0, -1)
text(XD - 1, -R_IN * K / 2, DIA + "30", rot=90, align=TextEntityAlignment.BOTTOM_CENTER)
# фаска 2,5×45° — выносные линии вниз, надпись на полке справа
chamfer_dim(S(L - CH, 0)[0], S(L, 0)[0], S(0, -R_IN)[1], S(0, -(R_IN + CH))[1], -R_FL * K - 4, "2,5×45°")
text(L * K / 2, R_FL * K + 6, "М 2:1", h=5, layer="Обозначения",
     align=TextEntityAlignment.MIDDLE_CENTER)

# ================================================================ РАМКА А4 И ОСНОВНАЯ НАДПИСЬ
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(0, 0)
poly([(0, 0), (210, 0), (210, 297), (0, 297)], "Рамка_тонкая", closed=True)
poly([(20, 5), (205, 5), (205, 292), (20, 292)], "Рамка", closed=True)

TX, TY = 205 - 185, 5  # левый нижний угол основной надписи (форма 1, ГОСТ 2.104)
B = "Рамка"
T = "Рамка_тонкая"
poly([(TX, TY), (TX, TY + 55), (205, TY + 55)], B)
# вертикали (графы по ГОСТ 2.104, форма 1)
for x, y1, y2, lay in [(7, 30, 55, B), (17, 0, 55, B), (40, 0, 55, B), (55, 0, 55, B),
                       (65, 0, 55, B), (135, 0, 40, B), (140, 20, 35, T), (145, 20, 35, T),
                       (150, 20, 40, B), (155, 15, 20, B), (167, 20, 40, B)]:
    line(TX + x, TY + y1, TX + x, TY + y2, lay)
# горизонтали левой части: 4 строки изменений, строка заголовков, 6 строк подписей
for i in range(1, 11):
    y = 5 * i
    lay = B if y in (30, 35) else T
    line(TX, TY + y, TX + 65, TY + y, lay)
# горизонтали правой части
for x1, y, x2 in [(65, 40, 185), (135, 35, 185), (135, 20, 185), (135, 15, 185),
                  (65, 15, 135)]:
    line(TX + x1, TY + y, TX + x2, TY + y, B)

def tb(x, y, s, h=3.5, align=TextEntityAlignment.LEFT, width=0.75):
    text(TX + x, TY + y, s, h=h, layer="Рамка_тонкая", align=align, width=width)

C = TextEntityAlignment.MIDDLE_CENTER

# только подписи граф — поля для заполнения оставлены пустыми
tb(3.5, 32.5, "Изм.", align=C); tb(12, 32.5, "Лист", align=C); tb(28.5, 32.5, "№ докум.", align=C)
tb(47.5, 32.5, "Подп.", align=C); tb(60, 32.5, "Дата", align=C)
tb(0.6, 26.2, "Разраб."); tb(0.6, 21.2, "Пров."); tb(0.6, 16.2, "Т.контр.")
tb(0.6, 6.2, "Н.контр."); tb(0.6, 1.2, "Утв.")
tb(142.5, 37.5, "Лит.", align=C); tb(158.5, 37.5, "Масса", align=C); tb(176, 37.5, "Масштаб", align=C)
tb(136, 16.2, "Лист"); tb(156, 16.2, "Листов")
tb(17.6, 26.2, "Васильева К. М.", width=0.66); tb(17.6, 21.2, "Кулькова В. В.", width=0.66)
tb(100, 27.5, "Лаб. раб. №1", h=10, align=C)
tb(136.5, 4.5, "ВФ МЭИ", h=6, width=0.7); tb(157, 4.5, "гр. ИВТ-2-26", h=4, width=0.7)
tb(176, 27.5, "1:1", h=5, align=C)
tb(180, 17.5, "1", h=3.5, align=C)

# дополнительные графы 19–23 и 24–25 на поле подшивки (ГОСТ 2.104)
CC = TextEntityAlignment.MIDDLE_CENTER
line(8, 5, 8, 150, B); line(13, 5, 13, 150, B); line(8, 5, 20, 5, B)
y = 5
for hgt, cap in [(25, "Инв. № подл."), (35, "Подп. и дата"), (25, "Взам. инв. №"),
                 (25, "Инв. № дубл."), (35, "Подп. и дата")]:
    line(8, y + hgt, 20, y + hgt, B)
    text(10.5, y + hgt / 2, cap, h=3.5, layer=T, align=CC, rot=90, width=0.75)
    y += hgt
line(8, 172, 8, 292, B); line(13, 172, 13, 292, B)
for yy in (172, 232, 292):
    line(8, yy, 20, yy, B)
text(10.5, 262, "Перв. примен.", h=3.5, layer=T, align=CC, rot=90, width=0.75)
text(10.5, 202, "Справ. №", h=3.5, layer=T, align=CC, rot=90, width=0.75)
# графа 26 (обозначение документа, повернутое) в левом верхнем углу
poly([(20, 278), (90, 278), (90, 292)], B)
# надписи под рамкой
text(96, 1, "Копировал", h=3.5, layer=T, width=0.8)
text(166, 1, "Формат  А4", h=3.5, layer=T, width=0.8)

doc.saveas(OUT)
print("saved", OUT)
