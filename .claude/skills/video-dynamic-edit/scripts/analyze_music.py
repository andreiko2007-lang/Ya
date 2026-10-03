#!/usr/bin/env python3
"""Beat / tempo / section analysis of a music track (ffmpeg + pure Python).

Usage:
  analyze_music.py song.mp3 -o work/music.json [--start 0] [--length 60]

Output JSON:
  bpm, beat (seconds per beat), beats [...], downbeats [...],
  hits [...]      strongest onsets (accents, good for flashes / title pops),
  drop            time of the biggest energy jump (the "drop"), or null,
  holds [[a,b]]   sustained / low-onset stretches (good for a held shot, title, mask collapse),
  energy [...]    loudness per 0.5 s (dB), for reading the song's shape.
All times are relative to the start of the file (not to --start).
"""
import argparse
import array
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import need_ffmpeg, probe, save_json  # noqa: E402

SR = 11025
HOP = 256                     # ~23 ms
FPS_ENV = SR / HOP


def decode(path, start, length, af=None):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if length:
        cmd += ["-t", str(length)]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR)]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "s16le", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    a = array.array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    return a


def frame_energy(samples):
    n = len(samples) // HOP
    out = [0.0] * n
    for i in range(n):
        seg = samples[i * HOP:(i + 1) * HOP]
        out[i] = sum(x * x for x in seg) / HOP + 1e-9
    return out


def flux(energy):
    le = [math.log10(e) for e in energy]
    on = [0.0] + [max(0.0, le[i] - le[i - 1]) for i in range(1, len(le))]
    return on


def smooth(x, w):
    if w <= 1:
        return x[:]
    h = w // 2
    out = []
    acc = sum(x[:h])
    cnt = h
    for i in range(len(x)):
        if i + h < len(x):
            acc += x[i + h]
            cnt += 1
        if i - h - 1 >= 0:
            acc -= x[i - h - 1]
            cnt -= 1
        out.append(acc / cnt)
    return out


def normalize(x):
    """Scale so the 98th percentile is 1.0 (robust to one huge onset at t=0)."""
    srt = sorted(x)
    m = srt[int(len(srt) * 0.98)] if srt else 1
    m = m or (srt[-1] if srt else 1) or 1
    return [min(1.5, v / m) for v in x]


def tempo(env):
    """Autocorrelation tempo with a mild preference around 100-125 BPM."""
    mean = sum(env) / len(env)
    e = [v - mean for v in env]
    best, best_lag, scores = -1e18, None, {}
    lo, hi = int(FPS_ENV * 60 / 190), int(FPS_ENV * 60 / 60)
    n = len(e)
    for lag in range(lo, hi + 1):
        s = sum(e[i] * e[i + lag] for i in range(0, n - lag)) / (n - lag)
        bpm = 60 * FPS_ENV / lag
        w = math.exp(-0.5 * (math.log2(bpm / 112) / 0.9) ** 2)
        scores[lag] = s
        if s * w > best:
            best, best_lag = s * w, lag
    # parabolic refinement
    lag = best_lag
    if lo < lag < hi:
        a, b, c = scores[lag - 1], scores[lag], scores[lag + 1]
        d = (a - 2 * b + c)
        off = 0.5 * (a - c) / d if d else 0
        lag = lag + max(-0.5, min(0.5, off))
    return lag


def track(env, period):
    """Choose the beat phase, then nudge each beat to the local onset peak."""
    n = len(env)
    best_ph, best_s = 0, -1
    for ph10 in range(int(period * 10)):
        ph = ph10 / 10
        s, k = 0.0, 0
        t = ph
        while t < n:
            s += env[int(t)]
            k += 1
            t += period
        if s > best_s:
            best_s, best_ph = s, ph
    beats = []
    t = best_ph
    win = max(1, int(period * 0.12))
    while t < n:
        c = int(round(t))
        lo, hi = max(0, c - win), min(n - 1, c + win)
        pk = max(range(lo, hi + 1), key=lambda i: env[i]) if hi >= lo else c
        # only snap when the peak is clearly there; otherwise keep the grid
        beats.append(pk if env[pk] > 0.25 else c)
        t += period
    return beats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("music")
    ap.add_argument("-o", "--out", default="work/music.json")
    ap.add_argument("--start", type=float, default=0.0, help="analyse from this second")
    ap.add_argument("--length", type=float, default=0.0, help="analyse only this many seconds")
    ap.add_argument("--bpm", type=float, default=0.0, help="force tempo (if you know it)")
    a = ap.parse_args()
    need_ffmpeg()
    info = probe(a.music)
    full = decode(a.music, a.start, a.length)
    low = decode(a.music, a.start, a.length, af="lowpass=f=160")
    e_full, e_low = frame_energy(full), frame_energy(low)
    on = normalize([x + 1.5 * y for x, y in zip(flux(e_full), flux(e_low))])
    env = smooth(on, 2)
    period = (60 * FPS_ENV / a.bpm) if a.bpm else tempo(env)
    bpm = 60 * FPS_ENV / period
    # fold very fast tempos into a cuttable range
    while bpm > 170:
        period *= 2
        bpm /= 2
    beats_f = track(env, period)
    beats = [round(a.start + b / FPS_ENV, 3) for b in beats_f]

    # downbeats: the phase (mod 4) with the most low-end energy
    phase_sum = [0.0] * 4
    lflux = normalize(flux(e_low))
    for i, b in enumerate(beats_f):
        phase_sum[i % 4] += lflux[b] if b < len(lflux) else 0
    p0 = max(range(4), key=lambda k: phase_sum[k])
    downbeats = beats[p0::4]

    # strongest accents (peaks well above their neighbourhood)
    loc = smooth(on, int(FPS_ENV * 1.5))
    cand = [(on[i] - loc[i], i) for i in range(1, len(on) - 1)
            if on[i] >= on[i - 1] and on[i] >= on[i + 1] and on[i] > 0.3]
    cand.sort(reverse=True)
    hits, taken = [], []
    for score, i in cand:
        if all(abs(i - j) > FPS_ENV * 0.8 for j in taken):
            taken.append(i)
            hits.append(round(a.start + i / FPS_ENV, 3))
        if len(hits) >= 24:
            break
    hits.sort()

    # loudness per 0.5 s, drop = biggest rise of smoothed loudness
    half = int(FPS_ENV / 2)
    db = []
    for i in range(0, len(e_full), half):
        seg = e_full[i:i + half]
        db.append(round(10 * math.log10(sum(seg) / len(seg) / (32768 ** 2)), 1))
    sm = smooth(db, 3)
    drop, best = None, 4.0
    for i in range(2, len(sm) - 2):
        rise = sm[i + 1] - sm[i - 2]
        if rise > best:
            best, drop = rise, round(a.start + (i + 0.5) * 0.5, 2)
    if drop is not None and beats:
        drop = min(beats, key=lambda b: abs(b - drop))

    # holds: >=1.2 s where onset density is low but the track is not silent
    dens = smooth(on, int(FPS_ENV * 0.8))
    med = sorted(dens)[len(dens) // 2] or 1e-6
    loud_floor = sorted(e_full)[len(e_full) // 4]
    holds, s0 = [], None
    for i, d in enumerate(dens):
        quiet_note = d < 0.45 * med and e_full[i] > loud_floor
        if quiet_note and s0 is None:
            s0 = i
        if (not quiet_note or i == len(dens) - 1) and s0 is not None:
            if (i - s0) / FPS_ENV >= 1.2:
                holds.append([round(a.start + s0 / FPS_ENV, 2), round(a.start + i / FPS_ENV, 2)])
            s0 = None

    res = {"path": os.path.abspath(a.music), "duration": info["duration"],
           "analysed_from": a.start, "bpm": round(bpm, 2), "beat": round(period / FPS_ENV, 4),
           "beats": beats, "downbeats": downbeats, "hits": hits, "drop": drop,
           "holds": holds, "energy_db_per_half_sec": db}
    save_json(res, a.out)
    print(f"bpm {bpm:.1f} (beat {period / FPS_ENV:.3f}s), {len(beats)} beats, "
          f"first beat {beats[0] if beats else '-'}s, drop {drop}, holds {holds}")
    print("hits:", hits[:12], "..." if len(hits) > 12 else "")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
