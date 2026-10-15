"""Лабораторная работа №2, вариант 19 — чертёж фланцевой втулки.

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_v19.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR2_variant19.dxf"

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
def mk(ox, oy, rot=0):
    """Функции рисования в локальной системе вида с началом (ox, oy),
    повёрнутой на rot градусов (0 или 90) против часовой стрелки."""
    ca, sa = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))

    def P(x, y):
        return (ox + x * ca - y * sa, oy + x * sa + y * ca)

    def nrot(a):
        """Направление текста/размера без перевёрнутых надписей."""
        a = (a + rot) % 360
        return a - 180 if 90 < a <= 270 else a

    def line(x1, y1, x2, y2, layer="Основная"):
        msp.add_line(P(x1, y1), P(x2, y2), dxfattribs={"layer": layer})

    def poly(pts, layer="Основная", closed=False):
        msp.add_lwpolyline([P(*p) for p in pts], close=closed, dxfattribs={"layer": layer})

    def circle(x, y, r, layer="Основная"):
        msp.add_circle(P(x, y), r, dxfattribs={"layer": layer})

    def arc(x, y, r, a1, a2, layer="Основная"):
        msp.add_arc(P(x, y), r, a1 + rot, a2 + rot, dxfattribs={"layer": layer})

    def hatch(pts, angle=45, spacing=2.0):
        h = msp.add_hatch(dxfattribs={"layer": "Штриховка"})
        h.set_pattern_fill("ANSI31", scale=spacing / 3.175, angle=angle - 45)
        h.paths.add_polyline_path([P(*p) for p in pts], is_closed=True)

    def dim_lin(p1, p2, base, angle=0, text="<>"):
        d = msp.add_linear_dim(base=P(*base), p1=P(*p1), p2=P(*p2), angle=(angle + rot) % 180,
                               text=text, dimstyle="ГОСТ", dxfattribs={"layer": "Размеры"})
        d.render()

    def dim_dia(cx, cy, r, ang, text="<>", loc=None):
        kw = {"location": P(*loc)} if loc else {"angle": ang + rot}
        d = msp.add_diameter_dim(center=P(cx, cy), radius=r, text=text, **kw,
                                 dimstyle="ГОСТ", override={"dimtmove": 1},
                                 dxfattribs={"layer": "Размеры"})
        d.render()

    def dim_rad(cx, cy, r, ang, text="<>"):
        d = msp.add_radius_dim(center=P(cx, cy), radius=r, angle=ang + rot, text=text,
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
# Размеры по заданию (вариант 19)
L = 60.0          # общая длина
R_OUT = 30.0      # Ø60
CH_OUT = 2.5      # фаска 2,5×45°
T_FL = 12.0       # толщина фланца-проушин
LUG_C = 40.0      # межосевое 80 / 2
LUG_R = 6.0       # R6, ширина проушины 12
R_LUG_HOLE = 5.0  # Ø10, 2 отв.
SQ_H = 17.5       # квадрат 35 / 2
SQ_DEPTH = 30.0
SQ_R = 4.0        # R4
R_GROOVE = 11.0   # Ø22
GROOVE_W = 7.0
R_BORE = 7.0      # Ø14
SLOT_H = 4.0      # паз 8 / 2
SLOT_D = 10.0     # глубина паза
M12_Y = 18.0      # ось резьбовых отверстий (2 отв.)
M12_R = 6.0
M12_RMIN = 5.1    # внутренний диаметр резьбы ≈ Ø10,2
M12_THR = 12.0    # длина резьбы
M12_DRILL = 15.0  # глубина сверления
M12_CH = 2.0      # фаска 2×45°
CONE = M12_RMIN / math.tan(math.radians(59))  # конец сверла 118°

X_GROOVE = L - SQ_DEPTH - GROOVE_W  # 23
X_SQ = L - SQ_DEPTH                 # 30
X_SLOT = L - SLOT_D                 # 50
LUG_ARC = 45.0                      # центр скругления R6 торца проушины (по исходному чертежу)
LUG_TOP = LUG_ARC + LUG_R           # 51

# ================================================================ ГЛАВНЫЙ ВИД
# (соединение половины вида и половины фронтального разреза)
# ось детали вертикальна: фланец внизу, вид слева от оси, разрез справа
MX, MY = 112.0, 177.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY, 90)

# --- верхняя половина: вид
poly([(0, 0), (0, LUG_TOP), (T_FL, LUG_TOP), (T_FL, R_OUT),
      (L - CH_OUT, R_OUT), (L, R_OUT - CH_OUT), (L, SLOT_H), (X_SLOT, SLOT_H), (X_SLOT, 0)])
line(L - CH_OUT, SLOT_H, L - CH_OUT, R_OUT)            # кромка фаски
# --- нижняя половина: разрез
lower_outer = [(0, -R_BORE), (0, -(M12_Y - M12_R - M12_CH))]
poly(lower_outer)
poly([(0, -(M12_Y + M12_R + M12_CH)), (0, -(LUG_C - R_LUG_HOLE))])
poly([(0, -(LUG_C + R_LUG_HOLE)), (0, -LUG_TOP), (T_FL, -LUG_TOP), (T_FL, -R_OUT),
      (L - CH_OUT, -R_OUT), (L, -(R_OUT - CH_OUT)), (L, -SQ_H)])
line(L - CH_OUT, -R_OUT, L - CH_OUT, -SQ_H)            # кромка фаски
# внутренний контур: Ø14 → канавка Ø22 → квадрат 35
poly([(0, -R_BORE), (X_GROOVE, -R_BORE), (X_GROOVE, -R_GROOVE), (X_SQ, -R_GROOVE),
      (X_SQ, -SQ_H), (L, -SQ_H)])
# линии видимого контура за секущей плоскостью
line(0, -R_BORE, 0, 0)                                   # кромка отверстия Ø14 на торце
line(X_GROOVE, -R_BORE, X_GROOVE, 0)
line(X_SQ, -R_GROOVE, X_SQ, 0)
line(L, -SQ_H, L, -SLOT_H)
line(X_SLOT, -SLOT_H, L, -SLOT_H)
line(X_SLOT, -SLOT_H, X_SLOT, 0)
# обозначение плоской грани квадратного отверстия (диагонали)
line(X_SQ, 0, L, -SQ_H, "Тонкая")
line(X_SQ, -SQ_H, L, 0, "Тонкая")
# отверстие под болт Ø10 в проушине (в разрезе)
line(0, -(LUG_C - R_LUG_HOLE), T_FL, -(LUG_C - R_LUG_HOLE))
line(0, -(LUG_C + R_LUG_HOLE), T_FL, -(LUG_C + R_LUG_HOLE))
# резьбовое отверстие M12 (в разрезе)
yc = -M12_Y
HCM = M12_R + M12_CH - M12_RMIN   # фаска 45° доходит до внутреннего Ø резьбы
line(0, yc + M12_R + M12_CH, HCM, yc + M12_RMIN)        # фаска
line(0, yc - M12_R - M12_CH, HCM, yc - M12_RMIN)
line(HCM, yc + M12_RMIN, HCM, yc - M12_RMIN)
line(HCM, yc + M12_RMIN, M12_DRILL, yc + M12_RMIN)      # внутр. Ø резьбы
line(HCM, yc - M12_RMIN, M12_DRILL, yc - M12_RMIN)
line(M12_DRILL, yc + M12_RMIN, M12_DRILL + CONE, yc)    # конус сверла
line(M12_DRILL, yc - M12_RMIN, M12_DRILL + CONE, yc)
line(M12_CH, yc + M12_R, M12_THR, yc + M12_R, "Тонкая")  # наружн. Ø резьбы
line(M12_CH, yc - M12_R, M12_THR, yc - M12_R, "Тонкая")
line(M12_THR, yc + M12_R, M12_THR, yc - M12_R)          # граница резьбы
# штриховка
hatch([(0, -R_BORE), (X_GROOVE, -R_BORE), (X_GROOVE, -R_GROOVE), (X_SQ, -R_GROOVE),
       (X_SQ, -SQ_H), (L, -SQ_H), (L, -(R_OUT - CH_OUT)), (L - CH_OUT, -R_OUT),
       (T_FL, -R_OUT), (T_FL, -(LUG_C - R_LUG_HOLE)), (0, -(LUG_C - R_LUG_HOLE)),
       (0, yc - M12_R - M12_CH), (HCM, yc - M12_RMIN),
       (M12_DRILL, yc - M12_RMIN), (M12_DRILL + CONE, yc), (M12_DRILL, yc + M12_RMIN),
       (HCM, yc + M12_RMIN), (0, yc + M12_R + M12_CH)])
hatch([(0, -(LUG_C + R_LUG_HOLE)), (T_FL, -(LUG_C + R_LUG_HOLE)),
       (T_FL, -LUG_TOP), (0, -LUG_TOP)])
# осевые линии
line(-5, 0, L + 6, 0, "Осевая")
line(-3, -LUG_C, T_FL + 3, -LUG_C, "Осевая")
line(-3, LUG_C, T_FL + 3, LUG_C, "Осевая")
line(-3, yc, M12_DRILL + CONE + 3, yc, "Осевая")

# --- размеры главного вида
dim_lin((0, LUG_TOP), (T_FL, LUG_TOP), (0, LUG_TOP + 8))                 # 12
dim_lin((0, -R_BORE), (M12_DRILL, yc + M12_RMIN), (0, 22))               # 15 глубина сверления
dim_lin((0, -R_BORE), (M12_THR, yc + M12_R), (0, 15))                    # 12 длина резьбы
dim_lin((0, -LUG_TOP), (L, -SQ_H), (0, -LUG_TOP - 18))                   # 60
dim_lin((X_GROOVE, -R_GROOVE), (X_SQ, -R_GROOVE), (0, -LUG_TOP - 9))     # 7
dim_lin((X_SQ, -SQ_H), (L, -SQ_H), (0, -LUG_TOP - 9))                    # 30
dim_lin((0, -LUG_TOP), (M12_CH, yc - M12_R), (-14, -LUG_TOP - 9),
        text="2×45°")                                           # фаска 2×45°
dim_lin((L - CH_OUT, R_OUT), (L, R_OUT - CH_OUT), (0, R_OUT + 10),
        text="2,5×45°")                                         # фаска 2,5×45°
dim_lin((L, SLOT_H), (L, -SLOT_H), (L + 7, 0), angle=90)                # 8
dim_lin((L - CH_OUT, R_OUT), (L - CH_OUT, -R_OUT), (L + 14, 0), angle=90,
        text=DIA + "60")                                                  # Ø60
dim_lin((0, yc + M12_R), (0, yc - M12_R), (-7, 0), angle=90, text="M12")
text(-12.5, yc - 4, "2 отв.", rot=90, align=TextEntityAlignment.MIDDLE_CENTER)

# ================================================================ ВИД СВЕРХУ
# вид сверху — по ГОСТ 2.305 располагается под главным видом
SX, SY = 112.0, 108.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(SX, SY, 90)

circle(0, 0, R_OUT)
# фаска Ø55 — прервана пазом
a_ch = math.degrees(math.asin(SLOT_H / (R_OUT - CH_OUT)))
arc(0, 0, R_OUT - CH_OUT, a_ch, 180 - a_ch)
arc(0, 0, R_OUT - CH_OUT, 180 + a_ch, 360 - a_ch)
# проушины R6 с отверстиями Ø10
y_join = math.sqrt(R_OUT ** 2 - LUG_R ** 2)
for s in (1, -1):
    line(-LUG_R, s * y_join, -LUG_R, s * LUG_ARC)
    line(LUG_R, s * y_join, LUG_R, s * LUG_ARC)
    if s == 1:
        arc(0, LUG_ARC, LUG_R, 0, 180)
    else:
        arc(0, -LUG_ARC, LUG_R, 180, 360)
    circle(0, s * LUG_C, R_LUG_HOLE)
# паз шириной 8 (сквозь торец)
x_slot_out = math.sqrt(R_OUT ** 2 - SLOT_H ** 2)
for sx in (1, -1):
    for sy in (1, -1):
        line(sx * SQ_H, sy * SLOT_H, sx * x_slot_out, sy * SLOT_H)
# квадратное отверстие 35 со скруглениями R4
a, r = SQ_H, SQ_R
line(-a + r, a, a - r, a)
line(-a + r, -a, a - r, -a)
line(a, -a + r, a, a - r)
line(-a, -a + r, -a, a - r)
arc(a - r, a - r, r, 0, 90)
arc(-a + r, a - r, r, 90, 180)
arc(-a + r, -a + r, r, 180, 270)
arc(a - r, -a + r, r, 270, 360)
# канавка Ø22 и отверстие Ø14
circle(0, 0, R_GROOVE)
circle(0, 0, R_BORE)
# невидимые резьбовые отверстия M12
for s in (1, -1):
    circle(0, s * M12_Y, M12_R, "Штриховая")
    circle(0, s * M12_Y, M12_RMIN, "Штриховая")
# осевые
line(-R_OUT - 5, 0, R_OUT + 5, 0, "Осевая")
line(0, -LUG_TOP - 5, 0, LUG_TOP + 5, "Осевая")
for s in (1, -1):
    line(-LUG_R - 3, s * LUG_C, LUG_R + 3, s * LUG_C, "Осевая")
    line(-M12_R - 3, s * M12_Y, M12_R + 3, s * M12_Y, "Осевая")

# --- размеры вида справа
dim_lin((0, LUG_C), (0, -LUG_C), (R_OUT + 8, 0), angle=90)              # 80
dim_lin((-SQ_H, SQ_H), (-SQ_H, -SQ_H), (-R_OUT - 6, 0), angle=90,
        text=SQ + "35")                                                   # □35
dim_rad(SQ_H - SQ_R, SQ_H - SQ_R, SQ_R, 45, text="R4")
dim_rad(0, -LUG_ARC, LUG_R, 225, text="R6")
dim_dia(0, 0, R_GROOVE, 60, text=DIA + "22")
dim_dia(0, 0, R_BORE, 120, text=DIA + "14")
dim_dia(0, LUG_C, R_LUG_HOLE, 0, text=DIA + "10 2 отв.", loc=(22, 50))

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
tb(17.6, 26.2, "Шлейко И. Ю."); tb(17.6, 21.2, "Кулькова В. В.")
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
