#!/usr/bin/env python3
"""Build a beat-synced edit plan from footage.json + music.json.

Usage:
  make_plan.py --footage work/footage.json --music work/music.json \
      --style dynamic|cinematic --title "BARCELONA" [--subtitle "Welcome to"] \
      [--length 20] [--format auto|vertical|horizontal|square] [--music-start auto|12.3] \
      [--grade vivid] [--accents] [-o work/plan.json] [--video out/final.mp4]

The plan is a draft: read the printed table, then edit plan.json by hand
(swap clips, in-points, transitions, text) before rendering.

Clip roles come from footage.json "tags": opener, hero, closer (others are
used for variety: wide, detail, topdown, pov, food, people, night, interior...).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import die, load_json, save_json  # noqa: E402

FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080), "square": (1080, 1080)}


# ---------------------------------------------------------------- beat grid
def grid(beats, start, end, unit):
    """Times between start and end on a grid of `unit` beats (0.25, 0.5, 1, 2...)."""
    if not beats:
        die("music.json has no beats")
    bl = beats[1] - beats[0] if len(beats) > 1 else 0.5
    ext = beats[:]
    while ext[-1] < end + 4 * bl:          # extend grid past the analysed end
        ext.append(ext[-1] + bl)
    while ext[0] > start - bl:
        ext.insert(0, ext[0] - bl)
    pts = []
    if unit >= 1:
        step = int(round(unit))
        pts = ext[::step]
    else:
        sub = int(round(1 / unit))
        for a, b in zip(ext, ext[1:]):
            for k in range(sub):
                pts.append(a + (b - a) * k / sub)
    return [t for t in pts if start - 1e-6 <= t <= end + 1e-6]


def pick_unit(beat, lo, hi, prefer):
    best = None
    for u in (0.25, 0.5, 1, 2, 4):
        L = beat * u
        if lo <= L <= hi:
            if best is None or abs(L - prefer) < abs(best * beat - prefer):
                best = u
    if best is None:
        best = min((0.25, 0.5, 1, 2, 4), key=lambda u: abs(beat * u - prefer))
    return best


def snap(t, pts):
    return min(pts, key=lambda p: abs(p - t)) if pts else t


# --------------------------------------------------------------- clip pool
class Pool:
    def __init__(self, clips, base_dir):
        self.clips = [c for c in clips if not c.get("skip")]
        if not self.clips:
            die("no usable clips in footage.json")
        self.base = base_dir
        self.cursor = {c["id"]: 0 for c in self.clips}
        self.uses = {c["id"]: 0 for c in self.clips}
        self.order = self._interleave()
        self.i = 0

    def _interleave(self):
        """Order clips so that the same main tag rarely appears twice in a row."""
        rest = [c for c in self.clips if not ({"opener", "hero", "closer"} & set(c.get("tags", [])))]
        if not rest:
            rest = self.clips[:]
        out, last = [], None
        buckets = {}
        for c in rest:
            key = (c.get("tags") or ["_"])[0]
            buckets.setdefault(key, []).append(c)
        while any(buckets.values()):
            keys = sorted((k for k in buckets if buckets[k]), key=lambda k: -len(buckets[k]))
            k = next((k for k in keys if k != last), keys[0])
            out.append(buckets[k].pop(0))
            last = k
        return out

    def ranges(self, c):
        if c.get("use"):
            return [tuple(r) for r in c["use"]]
        d = c["duration"]
        edge = 0.3 if d > 1.2 else 0.0
        return [(edge, max(edge + 0.05, d - edge))]

    def source(self, c, need):
        """Return an in-point with `need` seconds of source, walking forward on each reuse."""
        rs = self.ranges(c)
        total = sum(b - a for a, b in rs)
        cur = self.cursor[c["id"]] % max(total, 1e-3)
        acc = 0.0
        for a, b in rs:
            if cur < acc + (b - a):
                t = a + (cur - acc)
                if t + need > b:            # not enough left in this range
                    t = max(a, b - need)
                self.cursor[c["id"]] += need + 0.4
                self.uses[c["id"]] += 1
                return round(t, 3)
            acc += b - a
        self.uses[c["id"]] += 1
        return round(rs[0][0], 3)

    def by_role(self, role, fallback="longest_calm", exclude=()):
        tagged = [c for c in self.clips if role in c.get("tags", []) and c["id"] not in exclude]
        if tagged:
            return tagged[0]
        roles = {"opener", "hero", "closer"} - {role}
        cand = ([c for c in self.clips if c["id"] not in exclude and not roles & set(c.get("tags", []))]
                or [c for c in self.clips if c["id"] not in exclude] or self.clips)
        if fallback == "longest_calm":
            return max(cand, key=lambda c: c["duration"] - 20 * c.get("motion", 0))
        if fallback == "wide":
            w = [c for c in cand if {"wide", "sky", "flag", "landscape"} & set(c.get("tags", []))]
            return (w or sorted(cand, key=lambda c: -c["duration"]))[0]
        return cand[0]

    def next(self, avoid=None, prefer_tags=None):
        n = len(self.order)
        for k in range(n):
            c = self.order[(self.i + k) % n]
            if avoid and c["id"] == avoid and n > 1:
                continue
            if prefer_tags and not (set(prefer_tags) & set(c.get("tags", []))):
                continue
            self.i = (self.i + k + 1) % n
            return c
        if prefer_tags:
            return self.next(avoid)
        c = self.order[self.i % n]
        self.i += 1
        return c

    def rel(self, c):
        return os.path.relpath(c["path"], self.base)


# ----------------------------------------------------------------- styles
def title_size(text, base):
    n = max(1, len(text))
    return round(base * (min(1.0, 9 / n)), 4)


def plan_dynamic(a, pool, beats, beat, W, H, L):
    """Fast intro flash-cuts -> hero shot + font-cycling title -> clips change under the
    title while the frame collapses -> full-screen beat cuts -> short end hold."""
    vert = H > W
    u_flash = pick_unit(beat, 0.12, 0.26, 0.18)
    u_main = pick_unit(beat, 0.28, 0.6, 0.4)
    u_anchor = pick_unit(beat, 0.25, 0.55, 0.33)
    g_flash = grid(beats, 0, L, u_flash)
    g_main = grid(beats, 0, L, u_main)
    g_beat = grid(beats, 0, L, 1)

    intro_end = snap(min(2.6, L * 0.15), g_beat[1:] or g_main)
    hero_end = snap(intro_end + max(2.4, min(4.5, 4 * beat)), g_beat)
    anchor_end = snap(hero_end + max(2.0, min(3.2, 4 * beat)), g_beat)
    # if the song holds a note / has a drop near there, collapse the frame on the hold
    # if the song holds a note / has a drop there, collapse the frame on it and cut on its end
    target = None
    hold = next((h for h in a.music.get("holds", []) if intro_end + 3 < h[1] - a.ms < L * 0.7), None)
    if hold:
        target = hold[1] - a.ms
    elif a.music.get("drop") and intro_end + 4 < a.music["drop"] - a.ms < L * 0.7:
        target = a.music["drop"] - a.ms
    if target is not None:
        ae = snap(target, g_beat)
        he = snap(min(intro_end + 5.0, max(intro_end + 2.4, ae - 3.0)), g_beat)
        if 1.5 <= ae - he <= 4.0:
            hero_end, anchor_end = he, ae
    end_hold = max(1.2, 2 * beat)

    segs = []

    def add(c, t0, t1, **kw):
        d = round(t1 - t0, 4)
        if d <= 0.02:
            return
        seg = {"clip": pool.rel(c), "in": pool.source(c, d * kw.get("speed", 1.0)), "dur": d}
        seg.update({k: v for k, v in kw.items() if v is not None})
        segs.append(seg)

    hero = pool.by_role("hero")
    pool.order = [c for c in pool.order if c["id"] != hero["id"]] or pool.order
    pts = [0.0] + [t for t in g_flash if 0 < t < intro_end - 0.05] + [intro_end]
    last = None
    for t0, t1 in zip(pts, pts[1:]):
        c = pool.next(avoid=last)
        add(c, t0, t1)
        last = c["id"]
    add(hero, intro_end, hero_end, zoom=[1.0, 1.04])
    g_an = grid(beats, hero_end, anchor_end, u_anchor)
    pts = [hero_end] + [t for t in g_an if hero_end + 0.05 < t < anchor_end - 0.05] + [anchor_end]
    for t0, t1 in zip(pts, pts[1:]):
        c = pool.next(avoid=last)
        add(c, t0, t1)
        last = c["id"]
    main_end = snap(L - end_hold, g_main)
    pts = [anchor_end] + [t for t in g_main if anchor_end + 0.05 < t < main_end - 0.05] + [main_end]
    hits = [h - a.ms for h in a.music.get("hits", [])]
    since_accent = 99
    for t0, t1 in zip(pts, pts[1:]):
        c = pool.next(avoid=last)
        tr = None
        if a.accents and since_accent > 5 and any(abs(h - t0) < 0.06 for h in hits):
            tr, since_accent = {"type": "flash_white", "frames": 2}, 0
        since_accent += 1
        add(c, t0, t1, transition_in=tr)
        last = c["id"]
    closer = pool.by_role("closer", "wide", exclude={hero["id"]})
    add(closer, main_end, L, zoom=[1.0, 1.05])

    title = a.title
    size = title_size(title, 0.15 if vert else 0.085)
    y = 0.5
    t_title = round(intro_end + (hero_end - intro_end) * 0.45, 3)
    overlays = []
    if a.subtitle:
        overlays.append({"type": "text", "text": a.subtitle, "font": "PlayfairDisplay",
                         "size": 0.035 if vert else 0.02, "color": "white",
                         "y": round(y - size * W / H * 0.75 - 0.01, 3),
                         "start": round(intro_end + 0.15, 3), "end": anchor_end, "fade_in": 0.2})
    overlays.append({"type": "mask_collapse", "start": hero_end, "end": anchor_end,
                     "collapse": round((anchor_end - hero_end) * 0.85, 3), "keep": 0.11, "y": y})
    overlays.append({"type": "title_cycle", "text": title, "start": t_title, "end": anchor_end,
                     "size": size, "color": a.color or "#F5D400", "y": y, "cycle_frames": 3,
                     "fonts": a.fonts or ["Anton", "Pacifico", "PermanentMarker", "PlayfairDisplay",
                                          "ArchivoBlack", "Caveat", "Monoton"]})
    look = {"grade": a.grade or "vivid", "glow": 0.0, "grain": 0, "vignette": False, "fade_out": 0.4}
    return segs, overlays, look


def plan_cinematic(a, pool, beats, beat, W, H, L):
    """Parallax opener + centre-reveal title -> zoom-blur + speed-ramp into the story ->
    beat cuts with light leaks, flashes, blur/dip transitions -> whip into a closer."""
    vert = H > W
    u_cut = pick_unit(beat, 0.6, 1.5, 0.8)
    g_cut = grid(beats, 0, L, u_cut)
    g_beat = grid(beats, 0, L, 1)
    opener_end = snap(max(2.8, min(4.5, 4 * beat)), g_beat)
    ramp_end = snap(opener_end + max(1.0, min(1.8, 2 * beat)), g_beat)
    closer_len = max(2.5, min(4.0, 4 * beat))
    body_end = snap(L - closer_len, g_beat)

    segs = []

    def add(c, t0, t1, **kw):
        d = round(t1 - t0, 4)
        if d <= 0.02:
            return
        need = d
        if kw.get("ramp"):
            r0, r1 = kw["ramp"]
            need = d * (r1 - r0) / __import__("math").log(r1 / r0)
        elif kw.get("speed"):
            need = d * kw["speed"]
        seg = {"clip": pool.rel(c), "in": pool.source(c, need), "dur": d}
        seg.update({k: v for k, v in kw.items() if v is not None})
        segs.append(seg)

    opener = pool.by_role("opener")
    closer = pool.by_role("closer", "wide", exclude={opener["id"]})
    pool.order = [c for c in pool.order if c["id"] not in (opener["id"], closer["id"])] or pool.order
    add(opener, 0, opener_end, zoom=[1.0, 1.08])
    c = pool.next(prefer_tags=["water", "pov", "wide", "landscape"])
    add(c, opener_end, ramp_end, ramp=[2.6, 1.0], transition_in={"type": "zoom_blur", "frames": 5})
    last = c["id"]
    pts = [ramp_end] + [t for t in g_cut if ramp_end + 0.1 < t < body_end - 0.1] + [body_end]
    mid = len(pts) // 2
    last_tr = None
    for i, (t0, t1) in enumerate(zip(pts, pts[1:])):
        c = pool.next(avoid=last)
        tags = set(c.get("tags", []))
        tr = None
        if i == mid and len(pts) > 6:
            tr = {"type": "dip_black", "frames": 4}
        elif (tags & {"night", "interior"} or c.get("night")) and last_tr != "blur":
            tr = {"type": "blur", "frames": 5}
        elif i % 5 == 3:
            tr = {"type": "flash_white", "frames": 3}
        zoom = [1.0, 1.06] if i % 2 == 0 else [1.06, 1.0]
        leak = {"at": "end", "dur": 0.5} if i % 4 == 1 else None
        add(c, t0, t1, zoom=zoom, transition_in=tr, light_leak=leak)
        last, last_tr = c["id"], (tr or {}).get("type")
    add(closer, body_end, L, zoom=[1.0, 1.05], transition_in={"type": "whip", "frames": 5})

    size = title_size(a.title, 0.16 if vert else 0.1)
    overlays = [{"type": "title_reveal", "text": a.title, "font": (a.fonts or ["Cinzel"])[0],
                 "size": size, "color": a.color or "white", "y": 0.5,
                 "start": round(min(0.6, beat), 3), "end": round(opener_end - 0.15, 3),
                 "reveal": 0.8, "fade_out": 0.45}]
    if a.subtitle:
        overlays.append({"type": "text", "text": a.subtitle, "font": "CormorantGaramond",
                         "size": 0.04 if vert else 0.025, "color": "white",
                         "y": round(0.5 + size * W / H * 0.8, 3), "start": round(min(0.6, beat) + 0.6, 3),
                         "end": round(opener_end - 0.15, 3), "fade_in": 0.4, "fade_out": 0.45})
    look = {"grade": a.grade or "golden", "glow": 0.22, "grain": 6, "vignette": True, "fade_out": 1.0}
    return segs, overlays, look


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--footage", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--style", choices=["dynamic", "cinematic"], default="dynamic")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--fonts", nargs="*", help="title font list (first = main)")
    ap.add_argument("--color", default=None, help="title colour, e.g. '#F5D400'")
    ap.add_argument("--length", type=float, default=0, help="seconds (default: 20 dynamic / 24 cinematic)")
    ap.add_argument("--format", default="auto", choices=["auto", *FORMATS])
    ap.add_argument("--music-start", default="auto")
    ap.add_argument("--grade", default=None)
    ap.add_argument("--accents", action="store_true", help="dynamic: white flash on strong hits")
    ap.add_argument("-o", "--out", default="work/plan.json")
    ap.add_argument("--video", default="out/final.mp4", help="output video path (relative to plan)")
    a = ap.parse_args()

    footage = load_json(a.footage)
    music = load_json(a.music)
    a.music = music
    base = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(base, exist_ok=True)
    clips = footage["clips"]
    pool = Pool(clips, base)

    if a.format == "auto":
        o = [c.get("orientation", "vertical") for c in pool.clips]
        a.format = max(set(o), key=o.count) if o else "vertical"
        if a.format not in FORMATS:
            a.format = "vertical"
    W, H = FORMATS[a.format]

    beats_abs = music["beats"]
    if a.music_start == "auto":
        cands = [b for b in music.get("downbeats", beats_abs) if b >= music.get("analysed_from", 0)]
        ms = cands[0] if cands else beats_abs[0]
        # don't start in silence: skip ahead to the first downbeat after the intro if very quiet
    else:
        ms = float(a.music_start)
    a.ms = ms
    beats = [round(b - ms, 4) for b in beats_abs if b >= ms - 1e-3]
    beat = music["beat"]
    remaining = music["duration"] - ms
    L = a.length or (20.0 if a.style == "dynamic" else 24.0)
    if L > remaining:
        print(f"note: music has only {remaining:.1f}s after start; length cut to that")
        L = remaining
    L = snap(L, grid(beats, 0, L + 2 * beat, 1)) if beats else L
    if not a.title:
        a.title = "TRAVEL"
    if not a.fonts and any("\u0400" <= ch <= "\u04ff" for ch in a.title + a.subtitle):
        # Cyrillic text: only fonts that contain Cyrillic glyphs
        a.fonts = (["RussoOne", "Lobster", "Unbounded", "MarckScript", "Oswald", "Caveat", "PlayfairDisplay"]
                   if a.style == "dynamic" else ["CormorantGaramond"])

    fn = plan_dynamic if a.style == "dynamic" else plan_cinematic
    segs, overlays, look = fn(a, pool, beats, beat, W, H, L)
    total = sum(s["dur"] for s in segs)
    plan = {
        "style": a.style,
        "output": {"width": W, "height": H, "fps": 30, "path": os.path.relpath(
            os.path.abspath(a.video), base) if os.path.isabs(a.video) else a.video},
        "music": {"path": os.path.relpath(music["path"], base), "start": round(ms, 3),
                  "fade_out": 1.2 if a.style == "cinematic" else 0.6},
        **look,
        "segments": segs,
        "overlays": overlays,
        "info": {"bpm": music["bpm"], "beat": beat, "length": round(total, 3)},
    }
    save_json(plan, a.out)
    print(f"{a.style} plan: {len(segs)} segments, {total:.2f}s, {W}x{H}, bpm {music['bpm']}, "
          f"music from {ms:.2f}s -> {a.out}")
    t = 0.0
    for i, s in enumerate(segs):
        extra = []
        if s.get("transition_in"):
            tr = s["transition_in"]
            extra.append("<" + (tr["type"] if isinstance(tr, dict) else tr))
        if s.get("ramp"):
            extra.append(f"ramp{s['ramp']}")
        if s.get("light_leak"):
            extra.append("leak")
        if s.get("zoom") and s["zoom"] != [1.0, 1.0]:
            extra.append(f"zoom{s['zoom']}")
        print(f"{i:3d} {t:6.2f}-{t + s['dur']:6.2f} ({s['dur']:.2f}) {os.path.basename(s['clip']):28s} "
              f"in {s['in']:6.2f}  {' '.join(extra)}")
        t += s["dur"]
    for o in overlays:
        print(f"    overlay {o['type']:13s} {o['start']:.2f}-{o['end']:.2f} {o.get('text', '')}")


if __name__ == "__main__":
    main()
