#!/usr/bin/env python3
"""Render an edit plan (plan.json) to a finished video with ffmpeg.

Usage:
  render.py work/plan.json [--preview] [--keep] [--only-segments]

Pipeline:
  1. every segment -> exact-length intermediate clip (speed / ramp, cover-crop,
     Ken Burns zoom, transition in/out effects, light leak)
  2. concat (stream copy)
  3. finishing pass: grade, glow, mask collapse, titles, vignette, grain,
     final fade, music.
See references/plan_format.md for every field.
"""
import argparse
import math
import os
import random
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (die, ff_escape_text, ff_path, fit_fontsize, font_path,  # noqa: E402
                    hex_color, load_json, need_ffmpeg, probe, run, text_width)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}

# --- transitions: how many frames each side and what it does -----------------
# (frames are per side: last k frames of the outgoing clip + first k of the incoming)
TRANS_DEFAULT_FRAMES = {
    "cut": 0, "flash_white": 3, "flash": 3, "dip_black": 4, "zoom_blur": 5,
    "whip": 5, "whip_left": 5, "whip_right": 5, "blur": 6, "zoom_in": 5,
}

GRADES = {
    "none": "",
    "vivid": "eq=contrast=1.06:saturation=1.22:gamma=0.98,unsharp=5:5:0.4",
    "warm_film": ("colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.04:gm=0.0:bm=-0.04:rh=0.04:bh=-0.06,"
                  "curves=all='0/0.05 0.5/0.51 1/0.95',eq=saturation=0.93:contrast=1.02"),
    "golden": ("colorbalance=rs=0.08:gs=0.03:bs=-0.08:rm=0.06:gm=0.02:bm=-0.06:rh=0.06:bh=-0.08,"
               "curves=all='0/0.07 0.45/0.5 1/0.94',eq=saturation=0.9"),
    "teal_orange": ("colorbalance=rs=-0.06:gs=0.0:bs=0.08:rm=0.02:bm=-0.02:rh=0.08:gh=0.02:bh=-0.08,"
                    "eq=saturation=1.1:contrast=1.05"),
    "moody": ("curves=all='0/0.04 0.5/0.45 1/0.9',colorbalance=bs=0.05:bm=0.02:rh=0.03,"
              "eq=saturation=0.8:contrast=1.08"),
    "bw": "hue=s=0,eq=contrast=1.12",
}


def ease(p, kind="inout"):
    """ffmpeg expression for easing of a 0..1 progress expression string p."""
    if kind == "in":
        return f"pow({p},2)"
    if kind == "out":
        return f"(1-pow(1-{p},2))"
    return f"(3*pow({p},2)-2*pow({p},3))"


def clamp01(e):
    return f"clip({e},0,1)"


class Renderer:
    def __init__(self, plan, plan_path, preview=False, keep=False):
        self.plan = plan
        self.base_dir = os.path.dirname(os.path.abspath(plan_path))
        o = plan.get("output", {})
        self.W = int(o.get("width", 1080))
        self.H = int(o.get("height", 1920))
        self.fps = int(o.get("fps", 30))
        self.preview = preview
        if preview:
            self.W, self.H = self.W // 2 // 2 * 2, self.H // 2 // 2 * 2
        self.ss = 1 if preview else int(o.get("supersample", 2))
        self.crf = "26" if preview else str(o.get("crf", 18))
        self.preset = "ultrafast" if preview else o.get("preset", "medium")
        out = o.get("path", "out.mp4")
        if preview:
            root, ext = os.path.splitext(out)
            out = root + "_preview" + ext
        self.out_path = self.abs(out)
        self.tmp = self.abs(o.get("work_dir", "render_tmp"))
        self.keep = keep
        os.makedirs(self.tmp, exist_ok=True)
        os.makedirs(os.path.dirname(self.out_path) or ".", exist_ok=True)
        self.segs = plan["segments"]
        if not self.segs:
            die("plan has no segments")
        # frame-exact boundaries
        acc, self.frames, self.starts = 0.0, [], []
        prev = 0
        for s in self.segs:
            acc += float(s["dur"])
            end = int(round(acc * self.fps))
            n = max(1, end - prev)
            self.starts.append(prev / self.fps)
            self.frames.append(n)
            prev += n
        self.total_frames = prev
        self.total = prev / self.fps

    def abs(self, p):
        return p if os.path.isabs(p) else os.path.join(self.base_dir, p)

    # ------------------------------------------------------------------ leaks
    def leak_image(self, side):
        path = os.path.join(self.tmp, f"leak_{side}_{self.W}x{self.H}.png")
        if os.path.exists(path):
            return path
        cx = "W*0.92" if side == "right" else "W*0.08"
        cy = "H*0.28"
        rad = f"(max(W,H)*0.55)"
        d = f"exp(-((X-{cx})*(X-{cx})+(Y-{cy})*(Y-{cy}))/(2*{rad}*{rad}))"
        geq = f"r='255*{d}':g='150*{d}*{d}+40*{d}':b='40*{d}*{d}*{d}'"
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", f"color=black:s={self.W}x{self.H}", "-vf", f"format=gbrp,geq={geq}",
             "-frames:v", "1", path])
        return path

    # --------------------------------------------------------------- segments
    def trans(self, t):
        if not t:
            return "cut", 0
        if isinstance(t, str):
            t = {"type": t}
        typ = t.get("type", "cut")
        if typ not in TRANS_DEFAULT_FRAMES:
            die(f"unknown transition '{typ}'. Known: {', '.join(TRANS_DEFAULT_FRAMES)}")
        k = int(t.get("frames", TRANS_DEFAULT_FRAMES[typ]))
        if self.preview:
            k = max(1, k) if typ != "cut" else 0
        return typ, k

    def render_segment(self, i):
        s = self.segs[i]
        n = self.frames[i]
        D = n / self.fps
        fps, W, H, ss = self.fps, self.W, self.H, self.ss
        out = os.path.join(self.tmp, f"seg_{i:04d}.mp4")
        clip = self.abs(s["clip"])
        if not os.path.exists(clip):
            die(f"segment {i}: clip not found: {clip}")
        is_img = os.path.splitext(clip)[1].lower() in IMAGE_EXT

        t_in, k_in = self.trans(s.get("transition_in"))
        nxt = self.segs[i + 1] if i + 1 < len(self.segs) else None
        t_out, k_out = self.trans(nxt.get("transition_in")) if nxt else ("cut", 0)
        k_in, k_out = min(k_in, n // 2), min(k_out, n // 2)

        # speed / ramp -> how much source we need
        ramp = s.get("ramp")
        speed = float(s.get("speed", 1.0))
        if ramp and abs(ramp[0] - ramp[1]) > 1e-3:
            s0, s1 = float(ramp[0]), float(ramp[1])
            src = D * (s1 - s0) / math.log(s1 / s0)
            pts = f"setpts='({src}/({s1 - s0}))*log(({s0}+({s1 - s0})*(T-STARTT)/{src})/{s0})/TB'"
        else:
            src = D * speed
            pts = f"setpts=(PTS-STARTPTS)/{speed}"
        start = float(s.get("in", 0.0))
        if s.get("reverse"):
            pts += ",reverse"

        inputs = []
        if is_img:
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{D + 0.5:.3f}", "-i", clip]
            pts = "setpts=PTS-STARTPTS"
        else:
            inputs += ["-ss", f"{start:.3f}", "-t", f"{src + 0.4:.3f}", "-i", clip]

        # zoom profile (Ken Burns) + transition zooms
        z0, z1 = s.get("zoom", [1.0, 1.0])
        fx, fy = s.get("focus", [0.5, 0.5])
        nf = max(1, n - 1)
        zexpr = f"({z0}+({z1}-{z0})*on/{nf})"
        xshift = "0"
        if t_out in ("zoom_blur", "zoom_in") and k_out:
            p = clamp01(f"(on-{n - k_out})/{k_out}")
            zexpr += f"*(1+0.45*{ease(p, 'in')})"
        if t_in in ("zoom_blur", "zoom_in") and k_in:
            p = clamp01(f"1-on/{k_in}")
            zexpr += f"*(1+0.45*{ease(p, 'in')})"
        whip_out = t_out.startswith("whip") and k_out
        whip_in = t_in.startswith("whip") and k_in
        if whip_out or whip_in:
            zexpr = f"max({zexpr},1.3)"
        if whip_out:
            d = -1 if t_out == "whip_right" else 1   # default: content leaves to the left
            p = clamp01(f"(on-{n - k_out})/{k_out}")
            xshift += f"+{d}*{ease(p, 'in')}"
        if whip_in:
            d = -1 if t_in == "whip_right" else 1
            p = clamp01(f"1-on/{k_in}")
            xshift += f"-{d}*{ease(p, 'out')}"
        # x = focus position inside the free margin, plus whip offset across the margin
        xexpr = f"clip((iw-iw/zoom)*({fx}+({xshift})*0.5),0,iw-iw/zoom)"
        yexpr = f"clip((ih-ih/zoom)*{fy},0,ih-ih/zoom)"

        f = [pts, f"fps={fps}", f"tpad=stop_mode=clone:stop_duration={D + 1:.2f}"]
        static = (abs(z0 - 1) < 1e-6 and abs(z1 - 1) < 1e-6 and not whip_in and not whip_out
                  and t_in not in ("zoom_blur", "zoom_in") and t_out not in ("zoom_blur", "zoom_in"))
        if static:   # no zoom/pan: a plain cover-crop is enough (much faster)
            f += [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic",
                  f"crop={W}:{H}:(iw-ow)*{fx}:(ih-oh)*{fy}", "setsar=1"]
        else:
            f += [f"scale={W * ss}:{H * ss}:force_original_aspect_ratio=increase:flags=bicubic",
                  f"crop={W * ss}:{H * ss}:(iw-ow)*{fx}:(ih-oh)*{fy}", "setsar=1",
                  f"zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':d=1:s={W}x{H}:fps={fps}"]

        # blur windows
        def win_out(k):
            return f"gte(t,{(n - k) / fps:.4f})"

        def win_in(k):
            return f"lt(t,{k / fps:.4f})"
        if t_out == "zoom_blur" and k_out:
            f.append(f"gblur=sigma={W / 60:.1f}:enable='{win_out(k_out)}'")
        if t_in == "zoom_blur" and k_in:
            f.append(f"gblur=sigma={W / 60:.1f}:enable='{win_in(k_in)}'")
        if whip_out:
            f.append(f"gblur=sigma={W / 25:.1f}:sigmaV=0.5:enable='{win_out(k_out)}'")
        if whip_in:
            f.append(f"gblur=sigma={W / 25:.1f}:sigmaV=0.5:enable='{win_in(k_in)}'")
        if t_out == "blur" and k_out:
            f.append(f"gblur=sigma={W / 45:.1f}:enable='{win_out(k_out)}'")
            f.append(f"eq=brightness=0.12:enable='{win_out(max(1, k_out // 2))}'")
        if t_in == "blur" and k_in:
            f.append(f"gblur=sigma={W / 45:.1f}:enable='{win_in(k_in)}'")
            f.append(f"eq=brightness=0.12:enable='{win_in(max(1, k_in // 2))}'")

        # fades
        color = {"flash_white": "white", "flash": "white", "dip_black": "black",
                 "zoom_blur": "white"}
        if t_out in color and k_out:
            kk = k_out if t_out != "zoom_blur" else max(1, k_out // 2)
            f.append(f"fade=t=out:st={(n - kk) / fps:.4f}:d={kk / fps:.4f}:color={color[t_out]}")
        if t_in in color and k_in:
            kk = k_in if t_in != "zoom_blur" else max(1, k_in // 2)
            f.append(f"fade=t=in:st=0:d={kk / fps:.4f}:color={color[t_in]}")

        chain = ",".join(f)
        leak = s.get("light_leak")
        if leak:
            if leak is True:
                leak = {}
            side = leak.get("side", "right" if i % 2 else "left")
            ldur = min(D, float(leak.get("dur", min(0.6, D))))
            at = leak.get("at", "end")
            lst = {"start": 0.0, "mid": (D - ldur) / 2, "end": D - ldur}.get(at, 0.0) if isinstance(at, str) else float(at)
            strength = float(leak.get("strength", 1.0))
            img = self.leak_image(side)
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{D + 0.5:.3f}", "-i", img]
            half = ldur / 2
            graph = (f"[0:v]{chain},format=gbrp[b];"
                     f"[1:v]format=gbrp,colorchannelmixer=rr={strength}:gg={strength}:bb={strength},"
                     f"fade=t=in:st={lst:.3f}:d={half:.3f},fade=t=out:st={lst + half:.3f}:d={half:.3f}[l];"
                     f"[b][l]blend=all_mode=screen,format=yuv420p[v]")
        else:
            graph = f"[0:v]{chain},format=yuv420p[v]"

        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
               "-filter_complex", graph, "-map", "[v]", "-frames:v", str(n), "-an",
               "-c:v", "libx264", "-preset", "veryfast" if not self.preview else "ultrafast",
               "-crf", "14" if not self.preview else "24", "-pix_fmt", "yuv420p",
               "-r", str(fps), out]
        run(cmd)
        return out

    # ---------------------------------------------------------------- finish
    def text_draw(self, ov, text, font, fontsize, color, y, enable, alpha="1", extra=""):
        fp = font_path(font)
        fit = float(ov.get("fit", 0.88))
        if fit > 0:
            fontsize = fit_fontsize(fp, text, fontsize, fit * self.W)
        ff = ff_path(fp)
        shadow = ov.get("shadow", True)
        border = ov.get("border", 0)
        parts = [f"fontfile='{ff}'", f"text='{ff_escape_text(text)}'",
                 f"fontsize={int(fontsize)}", f"fontcolor={hex_color(color)}",
                 "x=(w-text_w)/2", f"y={y}-text_h/2", f"alpha='{alpha}'", f"enable='{enable}'"]
        if shadow:
            parts += ["shadowcolor=black@0.45", f"shadowx=0", f"shadowy={max(2, int(fontsize / 25))}"]
        if border:
            parts += [f"borderw={int(border)}", "bordercolor=black@0.6"]
        return "drawtext=" + ":".join(parts) + extra

    def fade_alpha(self, s, e, fi, fo):
        a = "1"
        if fi > 0:
            a = f"min({a},(t-{s})/{fi})"
        if fo > 0:
            a = f"min({a},({e}-t)/{fo})"
        return f"clip({a},0,1)"

    def finish(self, concat_path):
        p = self.plan
        W, H, fps = self.W, self.H, self.fps
        total = self.total
        complex_parts = []
        cur = "[0:v]"
        lbl = [0]

        def nl():
            lbl[0] += 1
            return f"[f{lbl[0]}]"

        def push(filters):
            nonlocal cur
            if not filters:
                return
            o = nl()
            complex_parts.append(f"{cur}{filters}{o}")
            cur = o

        grade = p.get("grade", "none")
        if grade not in GRADES:
            die(f"unknown grade '{grade}'. Known: {', '.join(GRADES)}")
        g = GRADES[grade]
        if p.get("exposure"):
            g = (g + "," if g else "") + f"eq=brightness={float(p['exposure'])}"
        push(g)
        glow = float(p.get("glow", 0))
        if glow > 0:
            a, b, gl, o = nl(), nl(), nl(), nl()
            complex_parts.append(f"{cur}format=gbrp,split{a}{b}")
            complex_parts.append(f"{b}gblur=sigma={W / 40:.1f},curves=all='0/0 0.6/0.25 1/1'{gl}")
            complex_parts.append(f"{a}{gl}blend=all_mode=screen:all_opacity={glow},format=yuv420p{o}")
            cur = o

        overlays = p.get("overlays", [])
        # 1) mask collapse (black bars) under the titles
        for ov in overlays:
            if ov.get("type") != "mask_collapse":
                continue
            s, e = float(ov["start"]), float(ov["end"])
            col = float(ov.get("collapse", e - s))
            keep = float(ov.get("keep", 0.1))
            cy = float(ov.get("y", 0.5))
            prog = ease(clamp01(f"(t-{s})/{col}"), ov.get("ease", "inout"))
            top_h = f"(({cy}-{keep}/2)*{H})"
            bot_h = f"((1-{cy}-{keep}/2)*{H})"
            bar1, bar2 = nl(), nl()
            complex_parts.append(f"color=black:s={W}x{H}:r={fps}:d={total:.3f}{bar1}")
            complex_parts.append(f"color=black:s={W}x{H}:r={fps}:d={total:.3f}{bar2}")
            o1, o2 = nl(), nl()
            en = f"between(t,{s},{e})"
            complex_parts.append(f"{cur}{bar1}overlay=x=0:y='-{H}+{top_h}*{prog}':eval=frame:enable='{en}'{o1}")
            complex_parts.append(f"{o1}{bar2}overlay=x=0:y='{H}-{bot_h}*{prog}':eval=frame:enable='{en}'{o2}")
            cur = o2

        # 2) text overlays
        rng = random.Random(7)
        for ov in overlays:
            typ = ov.get("type")
            if typ == "mask_collapse":
                continue
            s, e = float(ov["start"]), float(ov["end"])
            size = float(ov.get("size", 0.12)) * W
            color = ov.get("color", "white")
            yc = f"{float(ov.get('y', 0.5))}*h"
            fi, fo = float(ov.get("fade_in", 0)), float(ov.get("fade_out", 0))
            if typ == "text":
                alpha = self.fade_alpha(s, e, fi, fo)
                push(self.text_draw(ov, ov["text"], ov.get("font", "PlayfairDisplay"), size, color,
                                    yc, f"between(t,{s},{e})", alpha))
            elif typ == "title_cycle":
                fonts = ov.get("fonts") or ["Anton", "Pacifico", "PermanentMarker", "PlayfairDisplay",
                                            "ArchivoBlack", "Caveat"]
                cf = int(ov.get("cycle_frames", 3)) / fps
                settle = ov.get("settle_at")
                sched = {fnt: [] for fnt in fonts}
                t, last = s, None
                while t < e - 1e-6:
                    if settle is not None and t >= float(settle):
                        sched[fonts[0]].append((t, e))
                        break
                    if ov.get("order", "random") == "random":
                        choices = [x for x in fonts if x != last] or fonts
                        fnt = rng.choice(choices)
                    else:
                        fnt = fonts[int(round((t - s) / cf)) % len(fonts)]
                    t1 = min(e, t + cf * (rng.choice([1, 1, 1, 2]) if ov.get("jitter", True) else 1))
                    sched[fnt].append((t, t1))
                    last, t = fnt, t1
                alpha = self.fade_alpha(s, e, fi, fo)
                # same visual width for every font: the main font's width, capped by `fit`
                fit = float(ov.get("fit", 0.88))
                w_main = text_width(font_path(fonts[0]), ov["text"], 200) * size / 200
                target = min(w_main, fit * W) if fit > 0 else w_main
                draws = []
                for fnt, wins in sched.items():
                    if not wins:
                        continue
                    en = "+".join(f"between(t,{a:.4f},{b - 0.0005:.4f})" for a, b in wins)
                    fsz = size
                    if ov.get("equal_width", True):
                        fsz = 200 * target / max(1, text_width(font_path(fnt), ov["text"], 200))
                    fsz *= float((ov.get("font_scale") or {}).get(fnt, 1.0))
                    draws.append(self.text_draw(ov, ov["text"], fnt, fsz, color, yc, en, alpha))
                push(",".join(draws))
            elif typ == "title_reveal":
                # text on its own transparent strip, revealed from the centre outwards
                font = font_path(ov.get("font", "Cinzel"))
                if float(ov.get("fit", 0.88)) > 0:
                    size = fit_fontsize(font, ov["text"], size, float(ov.get("fit", 0.88)) * W)
                rev = float(ov.get("reveal", 0.7))
                bh = int(size * 1.8) // 2 * 2
                dur = e - s
                txt = nl()
                draw = (f"drawtext=fontfile='{ff_path(font)}':text='{ff_escape_text(ov['text'])}':"
                        f"fontsize={int(size)}:fontcolor={hex_color(color)}:x=(w-text_w)/2:y=(h-text_h)/2")
                if ov.get("shadow", True):
                    draw += f":shadowcolor=black@0.4:shadowx=0:shadowy={max(2, int(size / 25))}"
                soft = W * 0.06
                prog = ease(clamp01(f"T/{rev}"), "out")
                fade = f"clip(min(1,({dur}-T)/{max(fo, 0.01)}),0,1)" if fo > 0 else "1"
                aexpr = f"alpha(X,Y)*clip(({prog}*(W/2+{soft})-abs(X-W/2))/{soft},0,1)*{fade}"
                complex_parts.append(
                    f"color=black@0:s={W}x{bh}:r={fps}:d={dur:.3f},format=rgba,{draw},"
                    f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{aexpr}',setpts=PTS+{s}/TB{txt}")
                o = nl()
                ypos = f"{float(ov.get('y', 0.5))}*H-h/2"
                complex_parts.append(f"{cur}{txt}overlay=x=0:y={ypos}:eof_action=pass{o}")
                cur = o
            else:
                die(f"unknown overlay type '{typ}'")

        fin = []
        if p.get("vignette"):
            fin.append("vignette=angle=PI/5")
        grain = float(p.get("grain", 0))
        if grain > 0:
            fin.append(f"noise=c0s={int(grain)}:c0f=t+u")
        fo = float(p.get("fade_out", 0.6))
        if fo > 0:
            fin.append(f"fade=t=out:st={total - fo:.3f}:d={fo:.3f}")
        fi = float(p.get("fade_in", 0))
        if fi > 0:
            fin.append(f"fade=t=in:st=0:d={fi:.3f}")
        fin.append("format=yuv420p")
        push(",".join(fin))

        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", concat_path]
        amap = []
        m = p.get("music")
        if m:
            mp = self.abs(m["path"])
            if not os.path.exists(mp):
                die(f"music not found: {mp}")
            cmd += ["-ss", f"{float(m.get('start', 0)):.3f}", "-i", mp]
            afo = float(m.get("fade_out", 1.2))
            vol = float(m.get("volume", 1.0))
            complex_parts.append(
                f"[1:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol},"
                f"afade=t=out:st={max(0, total - afo):.3f}:d={afo:.3f}[a]")
            amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        graph = ";".join(complex_parts)
        cmd += ["-filter_complex", graph, "-map", cur, *amap,
                "-c:v", "libx264", "-preset", self.preset, "-crf", self.crf,
                "-pix_fmt", "yuv420p", "-r", str(fps), "-frames:v", str(self.total_frames),
                "-movflags", "+faststart", self.out_path]
        with open(os.path.join(self.tmp, "finish_cmd.txt"), "w") as fh:
            fh.write(" ".join(cmd))
        run(cmd)

    def render(self, only_segments=False):
        print(f"{len(self.segs)} segments, {self.total:.2f}s, {self.W}x{self.H}@{self.fps}"
              f"{' (preview)' if self.preview else ''}")
        workers = max(1, (os.cpu_count() or 2))
        done = [0]

        def job(i):
            r = self.render_segment(i)
            done[0] += 1
            print(f"\r  segments {done[0]}/{len(self.segs)}", end="", flush=True)
            return r
        with ThreadPoolExecutor(max_workers=workers) as ex:
            files = list(ex.map(job, range(len(self.segs))))
        print()
        lst = os.path.join(self.tmp, "concat.txt")
        with open(lst, "w") as fh:
            for fpath in files:
                fh.write(f"file '{fpath}'\n")
        concat = os.path.join(self.tmp, "concat.mp4")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", lst, "-c", "copy", concat])
        if only_segments:
            print(f"segments concatenated -> {concat}")
            return concat
        print("  finishing pass (grade, titles, music)...")
        self.finish(concat)
        if not self.keep:
            shutil.rmtree(self.tmp, ignore_errors=True)
        info = probe(self.out_path)
        print(f"done -> {self.out_path}  ({info['duration']:.2f}s, {info['width']}x{info['height']})")
        return self.out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--preview", action="store_true", help="half resolution, fast encode")
    ap.add_argument("--keep", action="store_true", help="keep intermediate files")
    ap.add_argument("--only-segments", action="store_true")
    a = ap.parse_args()
    need_ffmpeg()
    plan = load_json(a.plan)
    Renderer(plan, a.plan, preview=a.preview, keep=a.keep).render(a.only_segments)


if __name__ == "__main__":
    main()
