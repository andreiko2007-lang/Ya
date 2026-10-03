#!/usr/bin/env python3
"""Inventory raw footage: metadata, brightness, motion, contact sheets.

Usage:
  analyze_footage.py <clip-or-folder> [...] -o work/footage.json [--sheets work/sheets]

Writes footage.json (one entry per clip) and a contact sheet per clip
(6 frames with timestamps). LOOK at the sheets, then fill in each clip's
"tags" and "use" ranges in footage.json before running make_plan.py.
"""
import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import need_ffmpeg, probe, run, save_json, font_path  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PHOTO_DUR = 6.0   # a photo behaves like a still clip of this length


def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if os.path.splitext(f)[1].lower() in VIDEO_EXT | IMAGE_EXT:
                    out.append(os.path.join(p, f))
        elif os.path.isfile(p):
            out.append(p)
        else:
            print(f"skip (not found): {p}", file=sys.stderr)
    return out


def measure(path):
    vf = "fps=4,scale=160:-2,signalstats,select='gte(scene,0)',metadata=print"
    _, err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an",
                  "-vf", vf, "-f", "null", "-"])
    yavg = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", err)]
    scene = [float(x) for x in re.findall(r"lavfi\.scene_score=([\d.]+)", err)]
    luma = sum(yavg) / len(yavg) if yavg else 0
    motion = sum(scene) / len(scene) if scene else 0
    # per-second motion profile -> find the calmest and the most dynamic second
    prof = [round(sum(scene[i:i + 4]) / max(1, len(scene[i:i + 4])), 4)
            for i in range(0, len(scene), 4)]
    return luma, motion, prof


def sheet(path, dur, out_png, cols=6):
    n = cols
    step = dur / (n + 1)
    font = font_path("Oswald")
    parts = []
    inputs = []
    for i in range(n):
        t = step * (i + 1)
        inputs += ["-ss", f"{t:.3f}", "-i", path]
        parts.append(
            f"[{i}:v]scale=320:-2,setsar=1,crop=320:min(ih\\,568),"
            f"drawtext=fontfile='{font}':text='{t:.1f}s':x=6:y=6:fontsize=22:"
            f"fontcolor=white:box=1:boxcolor=black@0.6[v{i}]")
    # pad all to same height
    graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) + \
        f"xstack=inputs={n}:layout=" + "|".join(f"{'+'.join(['w0'] * i) or '0'}_0" for i in range(n)) + \
        ":fill=black[out]"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", out_png])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", default="work/footage.json")
    ap.add_argument("--sheets", default=None, help="dir for contact sheets (default: next to json)")
    a = ap.parse_args()
    need_ffmpeg()
    clips = collect(a.inputs)
    if not clips:
        sys.exit("no video files found")
    sheets = a.sheets or os.path.join(os.path.dirname(os.path.abspath(a.out)), "sheets")
    os.makedirs(sheets, exist_ok=True)

    def one(idx_path):
        idx, p = idx_path
        info = probe(p)
        if not info.get("has_video"):
            return None
        is_img = os.path.splitext(p)[1].lower() in IMAGE_EXT
        if is_img:
            info["duration"] = PHOTO_DUR
            info["photo"] = True
        luma, motion, prof = measure(p)
        cid = f"c{idx:02d}"
        png = os.path.join(sheets, f"{cid}.jpg")
        try:
            if is_img:
                run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", p,
                     "-vf", "scale=480:-2", "-frames:v", "1", png])
            else:
                sheet(p, info["duration"], png)
        except RuntimeError as e:
            print(f"sheet failed for {p}: {e}", file=sys.stderr)
            png = None
        info.update({
            "id": cid,
            "name": os.path.basename(p),
            "luma": round(luma, 1),
            "night": luma < 60,
            "motion": round(motion, 4),
            "motion_per_sec": prof,
            "sheet": png,
            # --- fill these in after looking at the sheet ---
            "tags": [],      # e.g. hero, opener, closer, wide, detail, topdown, pov, food, people, night, interior, water, sky, flag
            "use": [],       # good source ranges, e.g. [[2.0, 5.5]]; empty = whole clip minus 0.3s edges
            "skip": False,
        })
        return info

    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as ex:
        res = [r for r in ex.map(one, enumerate(clips)) if r]
    save_json({"clips": res}, a.out)
    print(f"{len(res)} clips -> {a.out}; contact sheets in {sheets}/")
    print(f"{'id':4} {'dur':>6} {'size':>10} {'luma':>5} {'motion':>7}  name")
    for c in res:
        print(f"{c['id']:4} {c['duration']:6.1f} {c['width']:>4}x{c['height']:<5} "
              f"{c['luma']:5.0f} {c['motion']:7.3f}  {c['name']}")


if __name__ == "__main__":
    main()
