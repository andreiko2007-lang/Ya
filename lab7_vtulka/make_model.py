"""3D-модель шлицевой втулки, ЛР №7, вариант 19 (ГОСТ 1139-80, средняя серия).

Модель строится так же, как в методичке для КОМПАС-3D:
  1) эскиз втулки (полупрофиль) -> операция вращения;
  2) эскиз шлицевого отверстия на торце -> вырезать выдавливанием насквозь;
  3) эскиз-прямоугольник -> сечение по эскизу (вырез четверти ступицы).

Результат:
  vtulka_v19.step         — целая деталь (открывается в КОМПАС-3D: Файл -> Открыть);
  vtulka_v19_razrez.step  — деталь с вырезанной четвертью ступицы (как рис. 2.16);
  vtulka_v19.stl          — для просмотра/3D-печати;
  vtulka_v19_*.png        — изображения модели.

Запуск:  python3 make_model.py
Зависимости: cadquery (для картинок ещё libosmesa6).
"""
import math
from pathlib import Path

import cadquery as cq

OUT = Path(__file__).resolve().parent / "3d"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- исходные данные
Z, d, D, b, c, r = 8, 42.0, 48.0, 8.0, 0.4, 0.3   # табл. 2.1, вариант 19
L = 1.6 * D            # длина втулки            76,8
D_FL = 2.0 * D         # диаметр фланца          96
D_HUB = 1.5 * D        # диаметр ступицы         72
T_FL = 0.25 * D        # толщина фланца          12
CH = 1.0               # фаска на входе в отверстие 1x45°
DENSITY = 7.85e-3      # г/мм^3, сталь 08

Rd, RD, Rh, Rf = d / 2, D / 2, D_HUB / 2, D_FL / 2

# ---------------------------------------------------------------- 1. операция вращения
# эскиз втулки: полупрофиль в плоскости XY, ось вращения — ось X
profile = [
    (0, Rd + CH), (0, Rf), (T_FL, Rf), (T_FL, Rh), (L, Rh),
    (L, Rd + CH), (L - CH, Rd), (CH, Rd),
]
body = (cq.Workplane("XY").polyline(profile).close()
        .revolve(360, (0, 0, 0), (1, 0, 0)))


# ---------------------------------------------------------------- 2. шлицевое отверстие
def P(phi, v, u):
    """Точка в системе паза: u — по радиусу, v — поперёк паза."""
    cph, sph = math.cos(phi), math.sin(phi)
    return (u * cph - v * sph, u * sph + v * cph)


def spline_wire():
    hb = b / 2
    v_ch = hb + c                              # фаска c на кромке паза у d
    u_ch_arc = math.sqrt(Rd ** 2 - v_ch ** 2)
    u_ch_wall = math.sqrt(Rd ** 2 - hb ** 2) + c
    vc = hb - r                                # центр скругления r у дна паза (D)
    uc = math.sqrt((RD - r) ** 2 - vc ** 2)
    k = RD / (RD - r)
    tv, tu = vc * k, uc * k                    # точка касания скругления с окружностью D
    a_t = math.atan2(tu - uc, tv - vc)         # угол точки касания от центра скругления
    a_m = (0 + a_t) / 2                        # середина дуги скругления

    step = 2 * math.pi / Z
    wp = cq.Workplane("YZ", origin=(-1, 0, 0))
    first = None
    for i in range(Z):
        phi = math.pi / 2 + i * step
        p0 = P(phi, -v_ch, u_ch_arc)
        if first is None:
            first = p0
            wp = wp.moveTo(*p0)
        wp = wp.lineTo(*P(phi, -hb, u_ch_wall))
        wp = wp.lineTo(*P(phi, -hb, uc))
        wp = wp.threePointArc(P(phi, -vc - r * math.cos(a_m), uc + r * math.sin(a_m)),
                              P(phi, -tv, tu))
        wp = wp.threePointArc(P(phi, 0, RD), P(phi, tv, tu))
        wp = wp.threePointArc(P(phi, vc + r * math.cos(a_m), uc + r * math.sin(a_m)),
                              P(phi, hb, uc))
        wp = wp.lineTo(*P(phi, hb, u_ch_wall))
        wp = wp.lineTo(*P(phi, v_ch, u_ch_arc))
        nxt = phi + step
        mid = phi + step / 2
        end = P(nxt, -v_ch, u_ch_arc) if i < Z - 1 else first
        wp = wp.threePointArc((Rd * math.cos(mid), Rd * math.sin(mid)), end)
    return wp.close()


hole = spline_wire().extrude(L + 2)            # «Вырезать выдавливанием» насквозь
vtulka = body.cut(hole)

# ---------------------------------------------------------------- 3. сечение по эскизу
cutter = cq.Workplane("XY").box(L - T_FL + 1, Rf + 5, Rf + 5, centered=False) \
    .translate((T_FL, 0, 0))
vtulka_cut = vtulka.cut(cutter)

# ---------------------------------------------------------------- экспорт
solid = vtulka.val()
assert solid.isValid(), "модель невалидна"
vol = solid.Volume()
mass = vol * DENSITY
cq.exporters.export(vtulka, str(OUT / "vtulka_v19.step"))
cq.exporters.export(vtulka_cut, str(OUT / "vtulka_v19_razrez.step"))
cq.exporters.export(vtulka, str(OUT / "vtulka_v19.stl"), tolerance=0.02, angularTolerance=0.1)


# ---------------------------------------------------------------- изображения
# Рендер через VTK без экрана (нужен libosmesa6 или EGL).
def render(shape, path, cam_dir, size=(1400, 1100)):
    import tempfile
    import vtk

    with tempfile.TemporaryDirectory() as tmp:
        stl = str(Path(tmp) / "m.stl")
        cq.exporters.export(shape, stl, tolerance=0.01, angularTolerance=0.05)
        reader = vtk.vtkSTLReader()
        reader.SetFileName(stl)
        reader.Update()

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(reader.GetOutputPort())
    normals.SetFeatureAngle(30)
    normals.SplittingOn()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(0.42, 0.66, 0.82)
    prop.SetAmbient(0.25)
    prop.SetDiffuse(0.75)
    prop.SetSpecular(0.25)
    prop.SetSpecularPower(20)

    edges = vtk.vtkFeatureEdges()
    edges.SetInputConnection(reader.GetOutputPort())
    edges.SetFeatureAngle(30)
    edges.BoundaryEdgesOn()
    edges.FeatureEdgesOn()
    edges.ManifoldEdgesOff()
    edges.NonManifoldEdgesOff()
    emapper = vtk.vtkPolyDataMapper()
    emapper.SetInputConnection(edges.GetOutputPort())
    emapper.ScalarVisibilityOff()
    eactor = vtk.vtkActor()
    eactor.SetMapper(emapper)
    eactor.GetProperty().SetColor(0.08, 0.15, 0.22)
    eactor.GetProperty().SetLineWidth(1.5)

    ren = vtk.vtkRenderer()
    ren.AddActor(actor)
    ren.AddActor(eactor)
    ren.SetBackground(1, 1, 1)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.AddRenderer(ren)
    win.SetSize(*size)
    win.SetMultiSamples(8)

    cam = ren.GetActiveCamera()
    fx, fy, fz = L / 2, 0.0, 0.0
    cam.SetFocalPoint(fx, fy, fz)
    cam.SetPosition(fx + cam_dir[0], fy + cam_dir[1], fz + cam_dir[2])
    cam.SetViewUp(0, 0, 1)
    ren.ResetCamera()
    cam.Zoom(1.15)
    win.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.Update()
    png = vtk.vtkPNGWriter()
    png.SetFileName(str(path))
    png.SetInputConnection(w2i.GetOutputPort())
    png.Write()


render(vtulka, OUT / "vtulka_v19_vid.png", (260, -200, 130))       # со стороны ступицы
render(vtulka, OUT / "vtulka_v19_flanec.png", (-260, -200, 130))   # со стороны фланца
render(vtulka_cut, OUT / "vtulka_v19_razrez.png", (230, 170, 160)) # разрез, как рис. 2.16

print(f"Объём {vol:.0f} мм³, масса ≈ {mass:.0f} г (сталь 08)")
