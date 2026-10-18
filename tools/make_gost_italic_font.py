import math, sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
src, dst = sys.argv[1], sys.argv[2]
f = TTFont(src)
gs = f.getGlyphSet()
glyf = f['glyf']; hmtx = f['hmtx']; cm = f.getBestCmap()
os2 = f['OS/2']
cap = getattr(os2, 'sCapHeight', 0) or 1400
xh = getattr(os2, 'sxHeight', 0) or 1000
def draw(name, transform):
    pen = TTGlyphPen(gs)
    gs[name].draw(TransformPen(pen, transform))
    return pen.glyph()
# 1) исправить «Э»: взять «э» и растянуть по высоте до прописной
E, e = cm[0x042D], cm[0x044D]
glyf[E] = draw(e, (1.08, 0, 0, cap / xh, 0, 0))
w, lsb = hmtx[e]; hmtx[E] = (int(w * 1.08), lsb)
gs = f.getGlyphSet()
# 2) наклон 15° вправо для всех глифов (как ГОСТ тип А)
k = math.tan(math.radians(15))
for name in f.getGlyphOrder():
    g = glyf[name]
    if g.isComposite() or g.numberOfContours == 0:
        continue
    glyf[name] = draw(name, (1, 0, k, 1, -k * xh * 0.6, 0))
for rec in f['name'].names:
    if rec.nameID in (1, 3, 4, 6):
        rec.string = 'GOSTitalic'
f['post'].italicAngle = -15
f.save(dst)
print('saved', dst)
