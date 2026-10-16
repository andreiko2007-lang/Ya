"""Лабораторная работа №2, вариант 5 — чертёж втулки с резьбовой головкой М70.

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_v5.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR2_variant5.dxf"

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
                                 dimstyle="ГОСТ", override={"dimtmove": 1},
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
# Размеры по заданию (вариант 5)
L = 87.84          # общая длина
L_HEAD = 30.0      # резьбовая головка М70
R_HEAD = 35.0      # М70
R_HEAD_MIN = 33.0  # внутренний Ø резьбы (тонкая линия)
CH_L = 2.0         # фаска 2×45° на левом торце
CH_R = 1.6         # фаска 1,6×45° у уступа
R_SHAFT = 25.0     # Ø50
FLAT = 20.0        # лыски, размер 40
FLAT_Y = math.sqrt(R_SHAFT ** 2 - FLAT ** 2)   # 15 — ребро лыски
R_BORE_A = 28.0    # расточка Ø56
L_BORE_A = 15.0
R_BORE_B = 10.0    # сквозное отверстие (по исходному чертежу ≈ Ø20, размер не указан)
R_BORE_C = 15.0    # расточка на торце (≈ Ø30 по виду, размер не указан)
L_BORE_C = 20.0
X_BORE_C = L - L_BORE_C
HOLE6_Y = 20.0     # отверстия Ø6, 2 отв. на Ø40
HOLE6_R = 3.0
HOLE6_CH = 1.5     # фаска 1,5×45°
HOLE6_DEPTH = 20.0
CONE = HOLE6_R / math.tan(math.radians(59))
HOLE10_Z = 28.0    # отверстия Ø10, 2 отв. (на окружности расточки Ø56)
HOLE10_R = 5.0

# ================================================================ ГЛАВНЫЙ ВИД
# ось детали вертикальна: головка М70 внизу, вид слева от оси, разрез справа
MX, MY = 112.0, 176.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY, 90)

# --- верхняя половина: вид
poly([(0, 0), (0, R_HEAD - CH_L), (CH_L, R_HEAD), (L_HEAD - CH_R, R_HEAD),
      (L_HEAD, R_HEAD - CH_R), (L_HEAD, R_SHAFT), (L, R_SHAFT), (L, 0)])
line(CH_L, 0, CH_L, R_HEAD)                                  # кромки фасок
line(L_HEAD - CH_R, 0, L_HEAD - CH_R, R_HEAD)
line(CH_L, R_HEAD_MIN, L_HEAD - CH_R, R_HEAD_MIN, "Тонкая")  # внутренний Ø резьбы
line(L_HEAD, FLAT_Y, L, FLAT_Y)                              # ребро лыски

# --- нижняя половина: разрез
yc = -HOLE6_Y
HCM = HOLE6_CH
outline = [(0, -R_BORE_A), (0, -(R_HEAD - CH_L)), (CH_L, -R_HEAD),
           (L_HEAD - CH_R, -R_HEAD), (L_HEAD, -(R_HEAD - CH_R)), (L_HEAD, -R_SHAFT),
           (L, -R_SHAFT), (L, yc - HOLE6_R - HOLE6_CH)]
poly(outline)
poly([(L, yc + HOLE6_R + HOLE6_CH), (L, -R_BORE_C), (X_BORE_C, -R_BORE_C),
      (X_BORE_C, -R_BORE_B), (L_BORE_A, -R_BORE_B), (L_BORE_A, -R_BORE_A),
      (0, -R_BORE_A)])
line(CH_L, -R_HEAD_MIN, L_HEAD - CH_R, -R_HEAD_MIN, "Тонкая")
# линии видимого контура за секущей плоскостью
line(0, -R_BORE_A, 0, 0)
line(L_BORE_A, -R_BORE_B, L_BORE_A, 0)
line(X_BORE_C, -R_BORE_B, X_BORE_C, 0)
line(L, -R_BORE_C, L, 0)
# отверстие Ø6 (в разрезе)
line(L, yc + HOLE6_R + HOLE6_CH, L - HCM, yc + HOLE6_R)
line(L, yc - HOLE6_R - HOLE6_CH, L - HCM, yc - HOLE6_R)
line(L - HCM, yc + HOLE6_R, L - HCM, yc - HOLE6_R)
line(L - HCM, yc + HOLE6_R, L - HOLE6_DEPTH, yc + HOLE6_R)
line(L - HCM, yc - HOLE6_R, L - HOLE6_DEPTH, yc - HOLE6_R)
line(L - HOLE6_DEPTH, yc + HOLE6_R, L - HOLE6_DEPTH - CONE, yc)
line(L - HOLE6_DEPTH, yc - HOLE6_R, L - HOLE6_DEPTH - CONE, yc)
line(L, yc + HOLE6_R + HOLE6_CH, L, yc - HOLE6_R - HOLE6_CH)   # кромка отверстия на торце
line(L - HOLE6_DEPTH, yc + HOLE6_R, L - HOLE6_DEPTH, yc - HOLE6_R)  # переход в конус
# невидимое отверстие Ø10 за секущей плоскостью
line(L_BORE_A, -HOLE10_R, L_HEAD, -HOLE10_R, "Штриховая")
# штриховка
hatch([(0, -R_BORE_A), (0, -(R_HEAD - CH_L)), (CH_L, -R_HEAD),
       (L_HEAD - CH_R, -R_HEAD), (L_HEAD, -(R_HEAD - CH_R)), (L_HEAD, -R_SHAFT),
       (L, -R_SHAFT), (L, yc - HOLE6_R - HOLE6_CH), (L - HCM, yc - HOLE6_R),
       (L - HOLE6_DEPTH, yc - HOLE6_R), (L - HOLE6_DEPTH - CONE, yc),
       (L - HOLE6_DEPTH, yc + HOLE6_R), (L - HCM, yc + HOLE6_R),
       (L, yc + HOLE6_R + HOLE6_CH), (L, -R_BORE_C), (X_BORE_C, -R_BORE_C),
       (X_BORE_C, -R_BORE_B), (L_BORE_A, -R_BORE_B), (L_BORE_A, -R_BORE_A)])
# осевые
line(-5, 0, L + 5, 0, "Осевая")
line(L - HOLE6_DEPTH - CONE - 3, yc, L + 4, yc, "Осевая")
line(L - 22, HOLE6_Y, L + 4, HOLE6_Y, "Осевая")

# --- размеры главного вида
dim_lin((0, R_HEAD - CH_L), (L, R_SHAFT), (0, R_HEAD + 20), text="87,84")
dim_lin((0, R_HEAD - CH_L), (L_HEAD, R_HEAD - CH_R), (0, R_HEAD + 13))        # 30
dim_lin((0, R_HEAD - CH_L), (CH_L, R_HEAD), (-12, R_HEAD + 6),
        text="2×45°")
dim_lin((L_HEAD - CH_R, R_HEAD), (L_HEAD, R_HEAD - CH_R), (L_HEAD + 12, R_HEAD + 6),
        text="1,6×45°")
dim_lin((CH_L, R_HEAD), (CH_L, -R_HEAD), (-16, 0), angle=90, text="M70")
# Ø56 — полуразмер
XD = -6
line(0, -R_BORE_A, XD - 2, -R_BORE_A, "Размеры")
line(XD, 6, XD, -R_BORE_A, "Размеры")
h = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
h.paths.add_polyline_path([P(XD, -R_BORE_A), P(XD - 0.5, -R_BORE_A + 3), P(XD + 0.5, -R_BORE_A + 3)],
                          is_closed=True)
text(XD - 1, -12, DIA + "56", rot=90, align=TextEntityAlignment.BOTTOM_CENTER)
dim_lin((0, -R_BORE_A), (L_BORE_A, -R_BORE_A), (0, -R_HEAD - 8))               # 15
dim_lin((L_BORE_A, -R_BORE_A), (L_HEAD, -(R_HEAD - CH_R)), (0, -R_HEAD - 8))  # 15
dim_lin((X_BORE_C, -R_SHAFT), (L, -R_SHAFT), (0, -R_HEAD - 8))                # 20
dim_lin((L - HCM, yc - HOLE6_R), (L, yc - HOLE6_R - HOLE6_CH), (L + 8, -R_SHAFT - 6),
        text="1,5×45°")

# ================================================================ ВИД СВЕРХУ
# вид сверху — по ГОСТ 2.305 располагается под главным видом
SX, SY = 112.0, 106.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(SX, SY, 90)
# координаты: u — поперёк оси (как Z главного вида), v — как Y главного вида
circle(0, 0, R_HEAD)                                         # М70: наружный Ø
arc(0, 0, R_HEAD_MIN, 100, 350, "Тонкая")                    # внутренний Ø резьбы
a0 = math.degrees(math.atan2(FLAT_Y, FLAT))
arc(0, 0, R_SHAFT, a0, 180 - a0)                             # Ø50 с лысками 40
arc(0, 0, R_SHAFT, 180 + a0, 360 - a0)
line(FLAT, -FLAT_Y, FLAT, FLAT_Y)
line(-FLAT, -FLAT_Y, -FLAT, FLAT_Y)
circle(0, 0, R_BORE_C)
circle(0, 0, R_BORE_B)
circle(0, 0, R_BORE_A, "Штриховая")
for s in (1, -1):
    circle(0, s * HOLE6_Y, HOLE6_R)
    circle(0, s * HOLE6_Y, HOLE6_R + HOLE6_CH)
    circle(s * HOLE10_Z, 0, HOLE10_R)
arc(0, 0, HOLE6_Y, 0, 360, "Осевая")                         # окружность центров Ø40
line(-R_HEAD - 4, 0, R_HEAD + 4, 0, "Осевая")
line(0, -R_HEAD - 4, 0, R_HEAD + 4, "Осевая")
for s in (1, -1):
    line(-HOLE6_R - 6, s * HOLE6_Y, HOLE6_R + 6, s * HOLE6_Y, "Осевая")
    line(s * HOLE10_Z, -HOLE10_R - 3, s * HOLE10_Z, HOLE10_R + 3, "Осевая")

# --- размеры вида сверху
dim_lin((-FLAT, FLAT_Y), (FLAT, FLAT_Y), (0, R_HEAD + 8))                     # 40
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


dia_full(R_SHAFT, 146, DIA + "50", ext=22)
dia_full(HOLE6_Y, 210, DIA + "40", ext=30)
dim_dia(0, HOLE6_Y, HOLE6_R, 0, text=DIA + "6 2 отв.", loc=(30, 44))
dim_dia(HOLE10_Z, 0, HOLE10_R, 0, text=DIA + "10 2 отв.", loc=(44, -14))

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
tb(17.6, 26.2, "Дмитриев В. В."); tb(17.6, 21.2, "Кулькова В. В.")
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
