"""Лабораторная работа №2, вариант 13 — чертёж фланца с квадратным отверстием.

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_v13.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR2_variant13.dxf"

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
# Размеры по заданию (вариант 13)
L = 55.0           # общая длина
T_FL = 15.0        # толщина фланца
R_OUT = 27.5       # Ø55
CH_OUT = 3.0       # фаска 3×45°
FL_H = 40.0        # фланец 80 / 2
FL_TOP = 10.0      # верхняя грань 20 / 2
FL_SIDE = 30.0     # боковые грани (ширина фланца 60, по исходному чертежу)
FL_SIDE_H = 20.0   # боковые грани 40 / 2
SLOT_C = 35.0      # центры пазов R5: 70 / 2
SLOT_R = 5.0       # R5
SQ_H = 7.5         # квадрат 15 / 2
SQ_DEPTH = 30.0    # квадратное отверстие на глубину до расточки (55 − 25)
M30_R = 15.0
M30_RMIN = 13.106  # внутренний диаметр М30 (шаг 3,5)
BORE_D = 25.0      # глубина отверстия под резьбу
THR_L = 20.0       # длина резьбы М30
M30_CH = 2.0       # фаска 2×45°
HOLE_Y = 20.0      # оси резьбовых отверстий (40 / 2)
HOLE_R = 5.0       # резьба М10 (размер на исходном чертеже не указан)
HOLE_RMIN = 4.188
HOLE_DEPTH = 20.0  # глубина отверстия
HOLE_THR = 17.0    # длина резьбы
HOLE_CH = 1.5      # фаска 1,5×45°
CONE = HOLE_RMIN / math.tan(math.radians(59))

X_BORE = L - BORE_D      # 30
X_THR = L - THR_L        # 35
X_CHM = L - (M30_R + M30_CH - M30_RMIN)  # фаска 45° доходит до внутреннего Ø резьбы

# ================================================================ ГЛАВНЫЙ ВИД
# (соединение половины вида и половины фронтального разреза)
# ось детали вертикальна: фланец внизу, вид слева от оси, разрез справа
MX, MY = 112.0, 190.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY, 90)

# --- верхняя половина: вид
poly([(0, 0), (0, FL_H), (T_FL, FL_H), (T_FL, R_OUT), (L - CH_OUT, R_OUT),
      (L, R_OUT - CH_OUT), (L, 0)])
line(L - CH_OUT, 0, L - CH_OUT, R_OUT)                   # кромка фаски
line(0, FL_SIDE_H, T_FL, FL_SIDE_H)                      # ребро скоса фланца

# --- нижняя половина: разрез
yc = -HOLE_Y
outer = [(0, -SQ_H), (0, yc + HOLE_R + HOLE_CH)]
poly(outer)
poly([(0, yc - HOLE_R - HOLE_CH), (0, -FL_H), (T_FL, -FL_H), (T_FL, -R_OUT),
      (L - CH_OUT, -R_OUT), (L, -(R_OUT - CH_OUT)), (L, -(M30_R + M30_CH))])
# паз R5 (за секущей плоскостью видна стенка паза)
line(0, -(SLOT_C - SLOT_R), T_FL, -(SLOT_C - SLOT_R))
# квадратное отверстие и отверстие под резьбу М30
# расточка Ø30 под выход резьбы (x 30…35), далее резьба М30 до торца
poly([(0, -SQ_H), (SQ_DEPTH, -SQ_H), (X_BORE, -M30_R), (X_THR, -M30_R),
      (X_THR, -M30_RMIN), (X_CHM, -M30_RMIN), (L, -(M30_R + M30_CH))])
# линии видимого контура за секущей плоскостью
line(0, -SQ_H, 0, 0)                                     # кромка квадратного отверстия
line(X_BORE, -SQ_H, X_BORE, 0)                           # дно расточки
line(X_THR, -M30_RMIN, X_THR, 0)                         # начало резьбы
line(X_CHM, -M30_RMIN, X_CHM, 0)                         # кромка фаски резьбы
line(L, -(M30_R + M30_CH), L, 0)                         # торец
line(X_THR, -M30_R, L - M30_CH, -M30_R, "Тонкая")         # наружный Ø резьбы
line(0, 0, SQ_DEPTH, -SQ_H, "Тонкая")                    # плоская грань
line(0, -SQ_H, SQ_DEPTH, 0, "Тонкая")
# резьбовое отверстие (в разрезе)
HCM = HOLE_R + HOLE_CH - HOLE_RMIN   # фаска 45° доходит до внутреннего Ø резьбы
line(0, yc + HOLE_R + HOLE_CH, HCM, yc + HOLE_RMIN)
line(0, yc - HOLE_R - HOLE_CH, HCM, yc - HOLE_RMIN)
line(HCM, yc + HOLE_RMIN, HCM, yc - HOLE_RMIN)
line(HCM, yc + HOLE_RMIN, HOLE_DEPTH, yc + HOLE_RMIN)
line(HCM, yc - HOLE_RMIN, HOLE_DEPTH, yc - HOLE_RMIN)
line(HOLE_DEPTH, yc + HOLE_RMIN, HOLE_DEPTH + CONE, yc)
line(HOLE_DEPTH, yc - HOLE_RMIN, HOLE_DEPTH + CONE, yc)
line(HOLE_CH, yc + HOLE_R, HOLE_THR, yc + HOLE_R, "Тонкая")
line(HOLE_CH, yc - HOLE_R, HOLE_THR, yc - HOLE_R, "Тонкая")
line(HOLE_THR, yc + HOLE_R, HOLE_THR, yc - HOLE_R)
# штриховка
hatch([(0, -SQ_H), (SQ_DEPTH, -SQ_H), (X_BORE, -M30_R), (X_THR, -M30_R),
       (X_THR, -M30_RMIN), (X_CHM, -M30_RMIN),
       (L - M30_CH, -M30_R), (L, -(M30_R + M30_CH)), (L, -(R_OUT - CH_OUT)),
       (L - CH_OUT, -R_OUT), (T_FL, -R_OUT), (T_FL, -(SLOT_C - SLOT_R)),
       (0, -(SLOT_C - SLOT_R)),
       (0, yc - HOLE_R - HOLE_CH), (HCM, yc - HOLE_RMIN),
       (HOLE_DEPTH, yc - HOLE_RMIN), (HOLE_DEPTH + CONE, yc), (HOLE_DEPTH, yc + HOLE_RMIN),
       (HCM, yc + HOLE_RMIN), (0, yc + HOLE_R + HOLE_CH)])
# осевые
line(-5, 0, L + 6, 0, "Осевая")
line(-4, yc, HOLE_DEPTH + CONE + 3, yc, "Осевая")
line(-4, HOLE_Y, T_FL + 4, HOLE_Y, "Осевая")

# --- размеры главного вида
dim_lin((0, FL_H), (L, R_OUT - CH_OUT), (0, FL_H + 13))                 # 55
dim_lin((0, FL_H), (T_FL, FL_H), (0, FL_H + 6))                         # 15
dim_lin((L - CH_OUT, R_OUT), (L, R_OUT - CH_OUT), (0, R_OUT + 8),
        text="3×45°")
dim_lin((L - CH_OUT, R_OUT), (L - CH_OUT, -R_OUT), (L + 17, 0), angle=90,
        text=DIA + "55")
# M30 — полуразмер: размерная линия заходит за ось, одна стрелка
XD = L + 8
line(L - M30_CH, -M30_R, XD + 2, -M30_R, "Размеры")
line(XD, 6, XD, -M30_R, "Размеры")
h = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
h.paths.add_polyline_path([P(XD, -M30_R), P(XD - 0.5, -M30_R + 3), P(XD + 0.5, -M30_R + 3)],
                          is_closed=True)
text(XD - 1, -4, "M30", rot=90, align=TextEntityAlignment.BOTTOM_CENTER)
dim_lin((L - M30_CH, -M30_R), (L, -(M30_R + M30_CH)), (0, -FL_H + 2),
        text="2×45°")
dim_lin((X_THR, -M30_R), (L, -(M30_R + M30_CH)), (0, -FL_H - 8))        # 20
dim_lin((X_BORE, -M30_R), (L, -(R_OUT - CH_OUT)), (0, -FL_H - 16))   # 25
dim_lin((0, -FL_H), (HOLE_DEPTH, yc - HOLE_RMIN), (0, -FL_H - 16))      # 20
dim_lin((0, yc - HOLE_R - HOLE_CH), (HOLE_CH, yc - HOLE_R), (-10, -FL_H - 8),
        text="1,5×45°")

# ================================================================ ВИД СПРАВА
# вид сверху — по ГОСТ 2.305 располагается под главным видом
SX, SY = 112.0, 122.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(SX, SY, 90)

# фланец: восьмиугольник 60×80 со скосами и двумя пазами R5
for s in (1, -1):
    poly([(SLOT_R, s * FL_H), (FL_TOP, s * FL_H), (FL_SIDE, s * FL_SIDE_H),
          (FL_SIDE, 0)])
    poly([(-SLOT_R, s * FL_H), (-FL_TOP, s * FL_H), (-FL_SIDE, s * FL_SIDE_H),
          (-FL_SIDE, 0)])
    line(SLOT_R, s * FL_H, SLOT_R, s * SLOT_C)
    line(-SLOT_R, s * FL_H, -SLOT_R, s * SLOT_C)
arc(0, SLOT_C, SLOT_R, 180, 360)
arc(0, -SLOT_C, SLOT_R, 0, 180)
# цилиндр Ø55 и фаска 3×45°
circle(0, 0, R_OUT)
circle(0, 0, R_OUT - CH_OUT)
# резьба М30: внутренний Ø — основная, наружный — тонкая дуга 3/4
circle(0, 0, M30_RMIN)
arc(0, 0, M30_R, 100, 350, "Тонкая")
# квадратное отверстие 15
poly([(-SQ_H, -SQ_H), (SQ_H, -SQ_H), (SQ_H, SQ_H), (-SQ_H, SQ_H)], closed=True)
# невидимые резьбовые отверстия
for s in (1, -1):
    circle(0, s * HOLE_Y, HOLE_R, "Штриховая")
    circle(0, s * HOLE_Y, HOLE_RMIN, "Штриховая")
# осевые
line(-FL_SIDE - 5, 0, FL_SIDE + 5, 0, "Осевая")
line(0, -FL_H - 5, 0, FL_H + 5, "Осевая")
for s in (1, -1):
    line(-HOLE_R - 3, s * HOLE_Y, HOLE_R + 3, s * HOLE_Y, "Осевая")

# --- размеры вида справа
dim_lin((FL_TOP, FL_H), (FL_TOP, -FL_H), (FL_SIDE + 18, 0), angle=90)          # 80
dim_lin((FL_SIDE, FL_SIDE_H), (FL_SIDE, -FL_SIDE_H), (FL_SIDE + 9, 0), angle=90)  # 40
dim_lin((-SLOT_R, SLOT_C), (-SLOT_R, -SLOT_C), (-FL_SIDE - 25, 0), angle=90)    # 70
dim_lin((-HOLE_R, HOLE_Y), (-HOLE_R, -HOLE_Y), (-FL_SIDE - 17, 0), angle=90)    # 40
dim_lin((-SQ_H, SQ_H), (-SQ_H, -SQ_H), (-FL_SIDE - 9, 0), angle=90,
        text=SQ + "15")
dim_lin((-FL_TOP, -FL_H), (FL_TOP, -FL_H), (0, -FL_H - 9))                     # 20
dim_rad(0, SLOT_C, SLOT_R, 300, text="R5")

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
tb(17.6, 26.2, "Плахов Р. Д."); tb(17.6, 21.2, "Кулькова В. В.")
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
