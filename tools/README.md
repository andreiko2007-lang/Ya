# Вспомогательные файлы для превью (PDF/PNG)

- `fonts/gost-italic.ttf` — наклонный шрифт в стиле ГОСТ 2.304 тип А для превью. Сделан из свободного
  шрифта osifont (LGPL 3, https://github.com/hikikomori82/osifont) скриптом `make_gost_italic_font.py`
  (наклон 15°, исправлена буква «Э»). Положите в `~/.fonts`.
- `render_a4_portrait.py`, `render_a4_landscape.py` — DXF → PDF/PNG (ezdxf + matplotlib).

В самих DXF стиль текста ссылается на «GOST type A» — в КОМПАС-3D подставится его штатный шрифт.
