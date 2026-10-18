"""Собирает наклонный (15°) штриховой шрифт ГОСТ-вида из LibreCAD cyrillic_ii.lff (ISO 3098-2/-5)."""
import math, re, sys
src, uni, dst = sys.argv[1:4]
k = math.tan(math.radians(15))
text = open(src, encoding='utf-8').read()
utext = open(uni, encoding='utf-8').read()
def glyph_block(t, code):
    m = re.search(r'^\[%s\][^\n]*\n(.*?)(?=\n\s*\n|\Z)' % code, t, re.S | re.M | re.I)
    return m.group(1) if m else None
extra = {}
sq = glyph_block(utext, '25a1')
if sq:
    extra['25a1'] = ('□', sq)
extra['2116'] = ('№', "0,0;0,9;5,0;5,9\n6.3,5.2;6.3,8.8;8.5,8.8;8.5,5.2;6.3,5.2\n6.3,3.6;8.5,3.6")
for code, (ch, body) in extra.items():
    text += "\n[%s] %s\n%s\n" % (code, ch, body)
def skew_pt(m):
    x, y = float(m.group(1)), float(m.group(2))
    return "%s,%s" % (round(x + k * y, 3), m.group(2))
out = []
for line in text.split('\n'):
    if line.startswith('#') or line.startswith('[') or not line.strip() or line.startswith('C'):
        out.append(line)
        continue
    out.append(re.sub(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', skew_pt, line))
res = '\n'.join(out).replace('# Name:              ISO 3098-2 + ISO 3098-5 (cyrillic)',
                             '# Name:              GOST italic (ISO 3098-2/-5, наклон 15°)')
open(dst, 'w', encoding='utf-8').write(res)
print('saved', dst)
