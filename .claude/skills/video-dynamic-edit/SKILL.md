---
name: video-dynamic-edit
description: Edit raw clips + music into a dynamic, beat-synced short video (Reels/TikTok/Shorts or 16:9 travel film) with ffmpeg. Flash-cut intros, font-cycling titles, mask-collapse, speed ramps, zoom-blur/whip/flash/dip transitions, light leaks, cinematic grade. Use when the user sends footage (and optionally music or a reference video) and asks to edit, cut or assemble a video, make a reel or travel edit, "смонтировать видео", "сделать монтаж", "нарезка под музыку", "как в референсе", or wants a reference video's editing style analysed and reproduced.
---

# Dynamic video editing (ffmpeg)

The skill turns the user's clips and music into a finished edit in one of two measured
styles, and can reproduce a reference video's rhythm. Everything runs on `ffmpeg` plus
plain Python 3, with no other dependencies. The fonts are bundled.

- **dynamic**: a flash-cut intro (≈0.2 s cuts), then a hero shot with a font-cycling title. Clips change under the title while the frame collapses to a strip, then full-screen beat cuts. Bright "vivid" grade, hard cuts.
- **cinematic**: a parallax opener with a title revealed from the centre, then zoom-blur + flash into a speed ramp, then ~1-beat cuts with light leaks, flash, blur and dip transitions, and a whip into the closer with a fade. Golden grade, glow, grain, vignette.

Read `references/techniques.md` for what each technique is and when it works, and
`references/plan_format.md` for every field you can edit.

`S=.claude/skills/video-dynamic-edit/scripts` (relative to the repo root). Work in a
`work/` folder in the scratchpad (or wherever the user wants the output).

## Workflow

### 0. Collect inputs
- Footage: the uploaded files (often under `/root/.claude/uploads/...`), a folder, or photos.
- Music: an audio file, or the audio of a video. Extract it with `ffmpeg -i x.mp4 -vn -c:a libmp3lame -q:a 2 music.mp3`.
  If there is no music, ask once. If the user doesn't care, render without `music`, and say so.
- Title text, style, format (vertical 9:16 is the default for phone footage) and length (15–30 s typical).
  Don't block on these: pick sensible defaults and state them.
- **Reference video sent?** Analyse it first:
  `python3 $S/review.py ref.mp4 --fps 4` (cut list + median shot length + contact sheets),
  `python3 $S/analyze_music.py ref.mp4 -o work/ref_music.json` (tempo), then Read the sheets.
  Map what you see to the closest style and plan fields (cut length → grid unit; titles → overlays; transitions).

### 1. Footage inventory
```bash
python3 $S/analyze_footage.py <files-or-folder> -o work/footage.json
```
Read **every** `work/sheets/cXX.jpg` (6 timestamped frames per clip). Then edit `footage.json`
for each clip:
- `tags`: give one clip the role `opener` (cinematic), `hero` (dynamic title shot), and `closer`.
  Add content tags: wide, detail, topdown, pov, food, people, night, interior, water, sky, flag...
- `use`: the good source ranges, e.g. `[[1.5, 4.0]]`. Skip shaky starts, people blocking the view, and burned-in text.
- `skip: true` for unusable clips (black, blurry, duplicates).

### 2. Music
```bash
python3 $S/analyze_music.py music.mp3 -o work/music.json
```
Check the BPM against your ear and the printed `hits`, `drop` and `holds`. Half or double
tempo is fine, because the planner subdivides. If the beat grid is clearly wrong, rerun with
`--bpm N`. Choose where the music starts: the song's best part, usually a chorus or drop. Look at
`energy_db_per_half_sec`. A good dynamic start is a loud section with a hold or drop 6–12 s later.

### 3. Plan
```bash
python3 $S/make_plan.py --footage work/footage.json --music work/music.json \
  --style dynamic --title "BARCELONA" --subtitle "Welcome to" --length 18 \
  --format vertical --music-start auto -o work/plan.json --video out/final.mp4 [--accents]
```
Read the printed table and refine `work/plan.json` by hand:
- Swap clips so that neighbouring shots contrast (colour, scale, direction). Repeat shot types as rhymes.
- Set `focus` for vertical crops of horizontal footage, so the subject is not cut off.
- Put strongest shots on downbeats, `hits` and right after the drop.
- For Russian titles, set Cyrillic `fonts` (see plan_format.md). Latin-only fonts show boxes.
- Change transitions or leaks where the content asks for it. Keep the dynamic style mostly hard cuts.
Never change `dur` values in a way that breaks the beat grid. Swap content, not timing.

### 4. Preview → check → final
```bash
python3 $S/render.py work/plan.json --preview      # half-res, fast
python3 $S/review.py work/out/final_preview.mp4 --music work/music.json --music-start <start> --fps 5 --cols 10 --rows 5
```
Read the review sheets. Check:
- Titles fit and are readable.
- No black or frozen frames, unless a short clip is held on purpose.
- Crops keep the subjects.
- The cuts report says they are on the grid.
- Burned-in text from sources does not clash.

Fix the plan, then do the full render with `python3 $S/render.py work/plan.json`.
A full 1080p render takes ~2–4 s per output second on 4 cores. Run long renders in the background.

### 5. Deliver
Send the mp4 with SendUserFile (`display: render`). In 3–6 lines, tell the user the structure
(timestamps of intro, title and drop), which techniques you used where, and what you can change
(music start, title, font set, pace, style).

## Gotchas
- Vertical output from horizontal footage crops ~70% of the width. Choose `focus` per shot, or use `--format horizontal`.
- Clips shorter than their segment are frozen on the last frame (`tpad`). Give the planner clips ≥ the cut length, or shorten the segment.
- `speed < 1` (slow motion) looks smooth only with 50/60 fps sources.
- The text size is a fraction of the width, and the font is auto-shrunk to `fit` (default 88%).
- Photos work as clips (Ken Burns via `zoom`).
- Errors from `render.py` include the ffmpeg stderr tail. The full final command is saved in `work_dir/finish_cmd.txt` with `--keep`.
