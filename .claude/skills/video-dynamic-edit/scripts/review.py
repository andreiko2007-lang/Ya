#!/usr/bin/env python3
"""Review a video: timestamped contact sheets + detected cuts vs. music beats.

Usage:
  review.py video.mp4 [--fps 4] [--music work/music.json --music-start 12.3] [-o work/review]

Use it on the rendered edit (to check your own work) and on reference videos
the user sends (to measure cut rhythm before imitating a style).
Each sheet covers `cols*rows/fps` seconds; open them with the Read tool.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import font_path, load_json, need_ffmpeg, probe, run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=4)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--dur", type=float, default=0)
    ap.add_argument("--music", default=None)
    ap.add_argument("--music-start", type=float, default=None)
    ap.add_argument("--scene", type=float, default=0.3, help="cut detection threshold")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    need_ffmpeg()
    info = probe(a.video)
    out = a.out or os.path.splitext(a.video)[0] + "_review"
    os.makedirs(out, exist_ok=True)
    w = 320 if info["width"] >= info["height"] else 180
    font = font_path("Oswald")
    seek = ["-ss", str(a.start)] if a.start else []
    dur = ["-t", str(a.dur)] if a.dur else []
    vf = (f"fps={a.fps},scale={w}:-2,drawtext=fontfile='{font}':text='%{{pts\\:hms}}':"
          f"x=4:y=4:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={a.cols}x{a.rows}")
    if a.start:
        vf = vf.replace("%{pts\\:hms}", f"%{{pts\\:hms\\:{a.start}}}")
    for f in os.listdir(out):
        if f.startswith("sheet_"):
            os.remove(os.path.join(out, f))
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *seek, *dur, "-i", a.video,
         "-vf", vf, os.path.join(out, "sheet_%02d.jpg")])
    sheets = sorted(f for f in os.listdir(out) if f.startswith("sheet_"))
    per = a.cols * a.rows / a.fps
    print(f"{info['duration']:.2f}s {info['width']}x{info['height']} @{info.get('fps')}fps; "
          f"{len(sheets)} sheets ({per:.1f}s each, {1 / a.fps:.2f}s per tile) in {out}/")

    _, err = run(["ffmpeg", "-hide_banner", "-nostats", *seek, *dur, "-i", a.video, "-an", "-vf",
                  f"scale=320:-2,select='gt(scene,{a.scene})',showinfo", "-f", "null", "-"])
    cuts = [round(float(x) + a.start, 3) for x in re.findall(r"pts_time:([\d.]+)", err)]
    print(f"cuts ({len(cuts)}): {cuts}")
    if len(cuts) > 1:
        gaps = [round(b - x, 3) for x, b in zip(cuts, cuts[1:])]
        srt = sorted(gaps)
        print(f"shot length: median {srt[len(srt) // 2]:.2f}s, min {srt[0]:.2f}s, max {srt[-1]:.2f}s")
    if a.music:
        m = load_json(a.music)
        ms = a.music_start if a.music_start is not None else 0.0
        beats = [b - ms for b in m["beats"] if b >= ms]
        bl = m["beat"]
        subs = []
        for x, y in zip(beats, beats[1:]):
            subs += [x + (y - x) * k / 4 for k in range(4)]
        offs = [min(abs(c - s) for s in subs) for c in cuts] if subs else []
        on = sum(1 for o in offs if o <= 0.05)
        print(f"beat {bl:.3f}s: {on}/{len(cuts)} cuts within 50 ms of the beat grid (1/4-beat resolution)")
        bad = [(c, round(o, 3)) for c, o in zip(cuts, offs) if o > 0.05]
        if bad:
            print("off-beat cuts (time, offset):", bad[:20])


if __name__ == "__main__":
    main()
