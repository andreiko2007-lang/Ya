import sys, ezdxf, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
doc=ezdxf.readfile(sys.argv[1])
for st in doc.styles:
    st.dxf.font='DejaVuSans.ttf'
fig=plt.figure(figsize=(8.27,11.69)); ax=fig.add_axes([0,0,1,1])
cfg=Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK, min_lineweight=0.12, lineweight_scaling=1.0)
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
fig.set_size_inches(297/25.4,210/25.4); ax.set_position([0,0,1,1]); ax.set_xlim(0,297); ax.set_ylim(0,210); ax.set_aspect("equal")
fig.savefig(sys.argv[2], dpi=int(sys.argv[3]) if len(sys.argv)>3 else 150)
