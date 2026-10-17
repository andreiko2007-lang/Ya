"""Лабораторная работа №2, вариант 2 — чертёж корпуса квадратного сечения.

Генерирует DXF (AutoCAD 2010), который открывается в КОМПАС-3D через
«Файл → Открыть» (тип файла DXF). Масштаб 1:1, формат А4 (книжный).

Запуск:  python build_v2.py   (нужен пакет ezdxf)
"""
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = sys.argv[1] if len(sys.argv) > 1 else "LR2_variant2.dxf"

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

    def text(x, y, s, h=3.5, layer="Размеры", align=TextEntityAlignment.LEFT, rot=0, width=0.8):
        rot_t = rot
        t = msp.add_text(s, height=h, rotation=nrot(rot_t),
                         dxfattribs={"layer": layer, "style": "GOST", "width": width})
        t.set_placement(P(x, y), align=align)

    return P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text




# ================================================================ ГЕОМЕТРИЯ ДЕТАЛИ
# Размеры по заданию (вариант 2)
L = 70.0           # общая длина
H = 32.5           # квадрат 65
CH_SQ = 2.5        # фаски 2,5×45° на рёбрах квадрата (правая часть)
X_GR1, X_GR2 = 16.0, 25.0   # кольцевая проточка Ø45 (16 и 45 от правого торца)
R_GR = 22.5        # Ø45
SLOT_L = 30.0      # пазы 20×7,5 длиной 30 от правого торца
SLOT_W = 10.0      # ширина паза 20 / 2
SLOT_Y = H - 7.5   # дно паза
SQ_A = 28.0 / math.sqrt(2)  # квадратное отверстие □28, повёрнутое на 45° (вершина 19,8)
SQ_DEPTH = 20.0
X_SQ = L - SQ_DEPTH          # 50
M26_R = 13.0
M26_RMIN = 12.188  # М26×1,5
M26_CH = 2.0       # фаска 2×45°
X_CHM = X_SQ - (M26_R + M26_CH - M26_RMIN)
X_UG1, X_UG2 = 7.0, 10.0     # внутренняя проточка шириной 3 (размеры 10 и 3)
R_UG = 13.75       # Ø проточки (на исходном чертеже не указан)
H6_R = 3.0         # Ø6, 4 отв. (сквозные в левой части)
H6_PCD_R = 27.5    # окружность центров (на исходном чертеже не указана)

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



# ================================================================ ГЛАВНЫЙ ВИД
# ось детали вертикальна: часть с отверстиями Ø6 внизу, квадратное отверстие вверху
MX, MY = 112.0, 192.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(MX, MY, 90)

# --- верхняя половина: вид
poly([(0, 0), (0, H), (X_GR1, H), (X_GR1, R_GR), (X_GR2, R_GR), (X_GR2, H), (L, H), (L, 0)])
line(X_GR2, H - CH_SQ, L, H - CH_SQ)                         # ребро фаски квадрата

# --- нижняя половина: разрез
yh = -H6_PCD_R
A = [(0, -M26_RMIN), (X_UG1, -M26_RMIN), (X_UG1, -R_UG), (X_UG2, -R_UG), (X_UG2, -M26_RMIN),
     (X_CHM, -M26_RMIN), (X_SQ, -(M26_R + M26_CH)), (X_SQ, -SQ_A), (L, -SQ_A), (L, -SLOT_Y),
     (L - SLOT_L, -SLOT_Y), (L - SLOT_L, -H), (X_GR2, -H), (X_GR2, -R_GR), (X_GR1, -R_GR),
     (X_GR1, yh + H6_R), (0, yh + H6_R)]
B = [(0, yh - H6_R), (X_GR1, yh - H6_R), (X_GR1, -H), (0, -H)]
poly(A, closed=True)
poly(B, closed=True)
hatch(A)
hatch(B)
# паз за секущей плоскостью
line(L - SLOT_L, -H, L, -H)
line(L, -SLOT_Y, L, -H)
# линии видимого контура за секущей плоскостью
line(0, -M26_RMIN, 0, 0)
line(X_UG1, -R_UG, X_UG1, 0)
line(X_UG2, -R_UG, X_UG2, 0)
line(X_CHM, -M26_RMIN, X_CHM, 0)
line(X_SQ, -SQ_A, X_SQ, 0)
line(L, -SQ_A, L, 0)
line(X_SQ, 0, L, -SQ_A, "Тонкая")                            # плоские грани квадрата
line(X_SQ, -SQ_A, L, 0, "Тонкая")
line(X_UG2, -M26_R, X_SQ - M26_CH, -M26_R, "Тонкая")        # наружный Ø резьбы
# отверстие Ø6: кромки на торцах
line(0, yh + H6_R, 0, yh - H6_R)
line(X_GR1, yh + H6_R, X_GR1, yh - H6_R)
# осевые
line(-5, 0, L + 5, 0, "Осевая")
line(-4, yh, X_GR1 + 4, yh, "Осевая")
line(-4, H6_PCD_R, X_GR1 + 4, H6_PCD_R, "Осевая")

# --- размеры главного вида
dim_lin((0, H), (L, H), (0, H + 16))                                         # 70
dim_lin((0, H), (X_GR1, H), (0, H + 8))                                      # 16
dim_lin((L - SLOT_L, -SLOT_Y), (L, H), (0, H + 8))                           # 30
dim_lin((X_GR1, R_GR), (X_GR1, -R_GR), (-16, 0), angle=90, text=DIA + "45")
dim_lin((0, -M26_RMIN), (X_UG2, -R_UG), (0, -H - 16))                        # 10
dim_lin((X_UG1, -R_UG), (X_UG2, -R_UG), (X_UG2 + 8, -H - 8))                 # 3
dim_lin((X_SQ - M26_CH, -M26_R), (X_SQ, -(M26_R + M26_CH)), (X_SQ - 14, -H - 8),
        text="2×45°")
dim_lin((X_SQ, -SQ_A), (L, -SLOT_Y), (0, -H - 8))                            # 20
dim_lin((X_GR2, -H), (L, -SLOT_Y), (0, -H - 16))                             # 45
# M26 — полуразмер
XD = -7
line(0, -M26_R, XD - 2, -M26_R, "Размеры")
line(XD, 6, XD, -M26_R, "Размеры")
hh = msp.add_hatch(color=3, dxfattribs={"layer": "Размеры"})
hh.paths.add_polyline_path([P(XD, -M26_R), P(XD - 0.5, -M26_R + 3), P(XD + 0.5, -M26_R + 3)],
                           is_closed=True)
text(XD - 1, -4, "M26", rot=90, align=TextEntityAlignment.BOTTOM_CENTER)

# ================================================================ ВИД СВЕРХУ
# вид сверху (на торец с квадратным отверстием) — по ГОСТ 2.305 под главным видом
SX, SY = 112.0, 112.0
P, line, poly, circle, arc, hatch, dim_lin, dim_dia, dim_rad, text = mk(SX, SY, 90)
# координаты: u — как Z главного вида, v — как Y главного вида
c = CH_SQ
outline = [(-H + c, H), (-SLOT_W, H), (-SLOT_W, SLOT_Y), (SLOT_W, SLOT_Y), (SLOT_W, H),
           (H - c, H), (H, H - c), (H, -H + c), (H - c, -H), (SLOT_W, -H), (SLOT_W, -SLOT_Y),
           (-SLOT_W, -SLOT_Y), (-SLOT_W, -H), (-H + c, -H), (-H, -H + c), (-H, H - c)]
poly(outline, closed=True)
poly([(0, SQ_A), (SQ_A, 0), (0, -SQ_A), (-SQ_A, 0)], closed=True)   # □28
circle(0, 0, M26_RMIN)
arc(0, 0, M26_R, 100, 350, "Тонкая")
circle(0, 0, R_GR, "Штриховая")                                     # проточка Ø45
arc(0, 0, H6_PCD_R, 0, 360, "Осевая")
for cx, cy in ((0, H6_PCD_R), (0, -H6_PCD_R), (H6_PCD_R, 0), (-H6_PCD_R, 0)):
    circle(cx, cy, H6_R, "Штриховая")
    line(cx - 5, cy, cx + 5, cy, "Осевая")
    line(cx, cy - 5, cx, cy + 5, "Осевая")
line(-H - 4, 0, H + 4, 0, "Осевая")
line(0, -H - 4, 0, H + 4, "Осевая")

# --- размеры вида сверху
dim_lin((-H + c, H), (H - c, H), (0, H + 14), text=SQ + "65")
dim_lin((-SLOT_W, H), (SLOT_W, H), (0, H + 6))                              # 20
dim_lin((-SLOT_W, H), (-SLOT_W, SLOT_Y), (-H - 8, 0), angle=90)              # 7,5
dim_lin((H - c, H), (H, H - c), (H + 6, H + 6), angle=90, text="2,5×45°")
dim_lin((-SQ_A, 0), (0, -SQ_A), (-SQ_A / 2 - 12, -SQ_A / 2 - 12), angle=135,
        text=SQ + "28")
dim_dia(H6_PCD_R, 0, H6_R, 0, text=DIA + "6 4 отв.", loc=(50, 30))
dia_full(R_GR, 120, DIA + "45", ext=28)

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
tb(17.6, 26.2, "Васильева К. М."); tb(17.6, 21.2, "Кулькова В. В.")
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
