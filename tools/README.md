# Вспомогательные файлы для превью (PDF/PNG)

- `fonts/gostitalic.lff` — наклонный (15°) штриховой шрифт в стиле ГОСТ 2.304 для превью варианта 2 ЛР №2.
  Сделан из шрифта LibreCAD `cyrillic_ii.lff` (ISO 3098-2/-5, GPL v2+) скриптом `make_gost_italic_lff.py`
  (наклон, интервалы, добавлены «№» и «□»). Положите в `~/.fonts`.
- `render_a4_portrait_gost.py` — DXF → PDF/PNG с этим шрифтом (используется для варианта 2).
- `render_a4_portrait.py`, `render_a4_landscape.py` — DXF → PDF/PNG обычным шрифтом (остальные чертежи).

В самих DXF стиль текста ссылается на «GOST type A» — в КОМПАС-3D подставится его штатный шрифт.
