"""Лабораторная работа №2, вариант 17 — чертёж втулки с квадратным фланцем.

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_v17.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR2_variant17.dxf"

doc = ezdxf.new("R2010", setup=True)
doc.header["$INSUNITS"] = 4  # мм
doc.header["$LWDISPLAY"] = 1
msp = doc.modelspace()

# ---------------------------------------------------------------- стили
doc.styles.new("GOST", dxfattribs={"font": "GOST type A.ttf", "width": 0.8, "oblique": 15})
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

    def text(x, y, s, h=3.5, layer="Размеры", align=TextEntityAlignment.LEFT, rot=0, width=0.8):
        rot_t = rot
        t = msp.add_text(s, height=h, rotation=nrot(rot_t),
                         dxfattribs={"layer": layer, "style": "GOST", "width": width})
        t.set_placement(P(x, y), align=align)

    return P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text




# ================================================================ ГЕОМЕТРИЯ ДЕТАЛИ
# Размеры по заданию (вариант 17)
L = 60.0           # общая длина
X_FL = 45.0        # начало фланца (толщина фланца 15)
R_BODY = 25.0      # Ø50
CH_BODY = 2.0      # фаска 2×45° на торце
FL_H = 40.0        # фланец □80
FL_R = 10.0        # R10
R_BORE = 7.0       # Ø14
CH_BORE = 2.0      # фаска 2×45° отверстия Ø14
R_REC = 15.0       # расточка Ø30 во фланце
CH_REC = 1.5       # фаска 1,5×45°
M6_PCD_R = 32.5    # М6, 4 отв. на Ø65
M6_R = 3.0
M6_RMIN = 2.459
M6_CH = 1.5        # фаска 1,5×45°
H10_R = 5.0        # Ø10, 4 отв. глубиной 15
H10_PCD_R = 17.5   # окружность центров Ø35 (на исходном чертеже не указана, снята с разреза)
H10_DEPTH = 15.0
CONE = H10_R / math.tan(math.radians(59))

# ================================================================ ГЛАВНЫЙ ВИД
# ось детали вертикальна: торец с отверстиями Ø10 внизу, фланец вверху; вид слева от оси, разрез справа
MX, MY = 112.0, 192.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY, 90)

# --- верхняя половина: вид
poly([(0, 0), (0, R_BODY - CH_BODY), (CH_BODY, R_BODY), (X_FL, R_BODY), (X_FL, FL_H),
      (L, FL_H), (L, 0)])
line(CH_BODY, 0, CH_BODY, R_BODY)                            # кромка фаски

# --- нижняя половина: разрез (отверстия Ø10 и М6 условно совмещены с секущей плоскостью)
yh = -H10_PCD_R
ym = -M6_PCD_R
M6_HCM = M6_R + M6_CH - M6_RMIN
main = [(0, -(R_BORE + CH_BORE)), (0, yh + H10_R), (H10_DEPTH, yh + H10_R),
        (H10_DEPTH + CONE, yh), (H10_DEPTH, yh - H10_R), (0, yh - H10_R),
        (0, -(R_BODY - CH_BODY)), (CH_BODY, -R_BODY), (X_FL, -R_BODY),
        (X_FL, ym + M6_RMIN), (L - M6_HCM, ym + M6_RMIN), (L, ym + M6_R + M6_CH),
        (L, -(R_REC + CH_REC)), (L - CH_REC, -R_REC), (X_FL, -R_REC),
        (X_FL, -(R_BORE + CH_BORE)), (X_FL - CH_BORE, -R_BORE), (CH_BORE, -R_BORE)]
low = [(X_FL, ym - M6_RMIN), (L - M6_HCM, ym - M6_RMIN), (L, ym - M6_R - M6_CH),
       (L, -FL_H), (X_FL, -FL_H)]
poly(main, closed=True)
poly(low, closed=True)
hatch(main)
hatch(low)
# линии видимого контура за секущей плоскостью
line(0, -(R_BORE + CH_BORE), 0, 0)
line(CH_BORE, -R_BORE, CH_BORE, 0)
line(X_FL - CH_BORE, -R_BORE, X_FL - CH_BORE, 0)
line(X_FL, -R_REC, X_FL, 0)
line(L - CH_REC, -R_REC, L - CH_REC, 0)
line(L, -(R_REC + CH_REC), L, 0)
# отверстие Ø10: кромка на торце и переход в конус
line(0, yh + H10_R, 0, yh - H10_R)
line(H10_DEPTH, yh + H10_R, H10_DEPTH, yh - H10_R)
# резьбовое отверстие М6 (сквозное)
line(X_FL, ym + M6_R, X_FL, ym - M6_R)                        # выход на торец фланца
line(L - M6_HCM, ym + M6_RMIN, L - M6_HCM, ym - M6_RMIN)       # кромка фаски
line(L, ym + M6_R + M6_CH, L, ym - M6_R - M6_CH)               # кромка на торце
line(X_FL, ym + M6_R, L - M6_CH, ym + M6_R, "Тонкая")          # наружный Ø резьбы
line(X_FL, ym - M6_R, L - M6_CH, ym - M6_R, "Тонкая")
line(X_FL, ym + M6_RMIN, X_FL, ym + M6_R)                      # ступенька до наружного Ø
# осевые
line(-5, 0, L + 5, 0, "Осевая")
line(-4, yh, H10_DEPTH + CONE + 3, yh, "Осевая")
line(X_FL - 4, ym, L + 4, ym, "Осевая")
line(X_FL - 4, M6_PCD_R, L + 4, M6_PCD_R, "Осевая")

# --- размеры главного вида
dim_lin((0, R_BODY - CH_BODY), (L, FL_H), (0, FL_H + 16))                     # 60
dim_lin((X_FL, FL_H), (L, FL_H), (0, FL_H + 8))                               # 15
dim_lin((0, R_BODY - CH_BODY), (CH_BODY, R_BODY), (-12, R_BODY + 8),
        text="2×45°")
dim_lin((CH_BODY, R_BODY), (CH_BODY, -R_BODY), (-17, 0), angle=90, text=DIA + "50")
dim_lin((0, yh + H10_R), (0, yh - H10_R), (-8, 0), angle=90, text=DIA + "10")
text(-11.5, yh - 9, "4 отв.", rot=270, align=TextEntityAlignment.LEFT)
dim_lin((0, -(R_BODY - CH_BODY)), (H10_DEPTH, yh - H10_R), (0, -FL_H - 8))     # 15
dim_lin((X_FL - CH_BORE, -R_BORE), (X_FL, -(R_BORE + CH_BORE)), (X_FL - 14, -FL_H - 8),
        text="2×45°")
dim_lin((L - M6_CH, ym - M6_R), (L, ym - M6_R - M6_CH), (L + 10, -FL_H - 16),
        text="1,5×45°")
text(L - 13, -FL_H - 21.5, "5 фасок", align=TextEntityAlignment.LEFT)
# Ø14 — полуразмер внутри разреза: размерная линия заходит за ось, стрелка на стенке отверстия
XD = 30.0
line(XD, 6, XD, -R_BORE, "Размеры")
h = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
h.paths.add_polyline_path([P(XD, -R_BORE), P(XD - 0.5, -R_BORE + 3), P(XD + 0.5, -R_BORE + 3)],
                          is_closed=True)
text(XD + 1, 1, DIA + "14", rot=90, align=TextEntityAlignment.BOTTOM_CENTER)

# ================================================================ ВИД СВЕРХУ
# вид сверху (на фланец) — по ГОСТ 2.305 располагается под главным видом
SX, SY = 112.0, 116.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(SX, SY, 90)
# квадрат 80 со скруглениями R10
a, r = FL_H, FL_R
line(-a + r, a, a - r, a)
line(-a + r, -a, a - r, -a)
line(a, -a + r, a, a - r)
line(-a, -a + r, -a, a - r)
arc(a - r, a - r, r, 0, 90)
arc(-a + r, a - r, r, 90, 180)
arc(-a + r, -a + r, r, 180, 270)
arc(a - r, -a + r, r, 270, 360)
circle(0, 0, R_REC)
circle(0, 0, R_REC + CH_REC)
circle(0, 0, R_BORE)
circle(0, 0, R_BORE + CH_BORE)
circle(0, 0, R_BODY, "Штриховая")                             # Ø50 за фланцем
# окружность центров разбита на две дуги так, чтобы штрих осевой линии начинался у стрелок размера
arc(0, 0, M6_PCD_R, -125, 55, "Осевая")                       # окружность центров Ø65
arc(0, 0, M6_PCD_R, 55, 235, "Осевая")
d45 = H10_PCD_R / math.sqrt(2)
for sx, sy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    cx, cy = sx * M6_PCD_R, sy * M6_PCD_R
    circle(cx, cy, M6_RMIN)
    arc(cx, cy, M6_R, 100, 350, "Тонкая")
    line(cx - 6, cy, cx + 6, cy, "Осевая")
    line(cx, cy - 6, cx, cy + 6, "Осевая")
for sx in (1, -1):
    for sy in (1, -1):
        cx, cy = sx * d45, sy * d45
        circle(cx, cy, H10_R, "Штриховая")
        line(cx - 7, cy, cx + 7, cy, "Осевая")
        line(cx, cy - 7, cx, cy + 7, "Осевая")
arc(0, 0, H10_PCD_R, 143, 323, "Осевая")                      # окружность центров Ø35
arc(0, 0, H10_PCD_R, -37, 143, "Осевая")
line(-FL_H - 4, 0, FL_H + 4, 0, "Осевая")
line(0, -FL_H - 4, 0, FL_H + 4, "Осевая")

# --- размеры вида сверху
dim_lin((-FL_H, FL_H - FL_R), (-FL_H, -(FL_H - FL_R)), (-FL_H - 8, 0), angle=90,
        text=SQ + "80")
dim_rad(FL_H - FL_R, -(FL_H - FL_R), FL_R, 315, text="R10")
def dia_full(r, ang, label, ext=15.0):
    """Диаметр с размерной линией через центр и двумя стрелками, надпись на продолжении."""
    c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    line(-r * c, -r * sn, (r + ext) * c, (r + ext) * sn, "Размеры")
    for k in (1, -1):
        tx, ty = k * r * c, k * r * sn
        bx, by = k * (r - 3) * c, k * (r - 3) * sn
        h = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
        h.paths.add_polyline_path([P(tx, ty), P(bx - 0.5 * sn, by + 0.5 * c),
                                   P(bx + 0.5 * sn, by - 0.5 * c)], is_closed=True)
    m = r + ext / 2
    text(m * c - 1 * sn, m * sn + 1 * c, label, rot=ang,
         align=TextEntityAlignment.BOTTOM_CENTER)


dia_full(M6_PCD_R, -120, DIA + "65")
dia_full(R_REC, 110, DIA + "30", ext=40)
dia_full(H10_PCD_R, 148, DIA + "35", ext=30)
dim_dia(M6_PCD_R, 0, M6_R, 0, text="M6 4 отв.", loc=(44, 30))

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

def tb(x, y, s, h=2.5, align=TextEntityAlignment.LEFT):
    text(TX + x, TY + y, s, h=h, layer="Рамка_тонкая", align=align, width=0.65)

C = TextEntityAlignment.MIDDLE_CENTER

# только подписи граф — поля для заполнения оставлены пустыми
tb(3.5, 32.5, "Изм.", align=C); tb(12, 32.5, "Лист", align=C); tb(28.5, 32.5, "№ докум.", align=C)
tb(47.5, 32.5, "Подп.", align=C); tb(60, 32.5, "Дата", align=C)
tb(0.6, 26.2, "Разраб."); tb(0.6, 21.2, "Пров."); tb(0.6, 16.2, "Т.контр.")
tb(0.6, 6.2, "Н.контр."); tb(0.6, 1.2, "Утв.")
tb(142.5, 37.5, "Лит.", align=C); tb(158.5, 37.5, "Масса", align=C); tb(176, 37.5, "Масштаб", align=C)
tb(136, 16.2, "Лист"); tb(156, 16.2, "Листов")
tb(17.6, 26.2, "Шапкин В. С."); tb(17.6, 21.2, "Кулькова В. В.")
tb(100, 27.5, "Лаб. раб. №2", h=7, align=C)
tb(160, 7.5, "ВФ МЭИ гр. ИВТ-2-26", h=3.5, align=C)
tb(176, 27.5, "1:1", h=5, align=C); tb(180, 17.5, "1", h=3.5, align=C)

# дополнительные графы 19–23 и 24–25 на поле подшивки (ГОСТ 2.104)
CC = TextEntityAlignment.MIDDLE_CENTER
line(8, 5, 8, 150, B); line(13, 5, 13, 150, B); line(8, 5, 20, 5, B)
y = 5
for hgt, cap in [(25, "Инв. № подл."), (35, "Подп. и дата"), (25, "Взам. инв. №"),
                 (25, "Инв. № дубл."), (35, "Подп. и дата")]:
    line(8, y + hgt, 20, y + hgt, B)
    text(10.5, y + hgt / 2, cap, h=3, layer=T, align=CC, rot=90, width=0.7)
    y += hgt
line(8, 172, 8, 292, B); line(13, 172, 13, 292, B)
for yy in (172, 232, 292):
    line(8, yy, 20, yy, B)
text(10.5, 262, "Перв. примен.", h=3, layer=T, align=CC, rot=90, width=0.7)
text(10.5, 202, "Справ. №", h=3, layer=T, align=CC, rot=90, width=0.7)
# графа 26 (обозначение документа, повернутое) в левом верхнем углу
poly([(20, 278), (90, 278), (90, 292)], B)
# надписи под рамкой
text(96, 1, "Копировал", h=3, layer=T, width=0.8)
text(166, 1, "Формат  А4", h=3, layer=T, width=0.8)

doc.saveas(OUT)
print("saved", OUT)
