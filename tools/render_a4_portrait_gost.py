import sys, ezdxf, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
doc=ezdxf.readfile(sys.argv[1])
for st in doc.styles:
    st.dxf.font='gostitalic.lff'
    st.dxf.width=0.75
# штриховой шрифт ISO 3098 шире шрифта ГОСТ тип А — сужаем, чтобы пропорции совпали
def fix_text(e):
    e.dxf.width = e.dxf.get('width', 1.0) * 0.75
    e.dxf.lineweight = max(25, int(e.dxf.height * 8))   # толщина штриха как у шрифта ГОСТ
for e in doc.modelspace().query('TEXT'):
    fix_text(e)
for blk in doc.blocks:
    for e in blk.query('TEXT MTEXT'):
        if e.dxftype() == 'TEXT':
            fix_text(e)
        else:
            e.dxf.lineweight = 28
fig=plt.figure(figsize=(8.27,11.69)); ax=fig.add_axes([0,0,1,1])
cfg=Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK, min_lineweight=0.12, lineweight_scaling=1.0)
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
fig.set_size_inches(210/25.4,297/25.4); ax.set_position([0,0,1,1]); ax.set_xlim(0,210); ax.set_ylim(0,297); ax.set_aspect("equal")
fig.savefig(sys.argv[2], dpi=int(sys.argv[3]) if len(sys.argv)>3 else 150)
