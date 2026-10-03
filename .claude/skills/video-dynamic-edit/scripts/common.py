"""Shared helpers: ffmpeg/ffprobe wrappers, fonts, small math."""
import json
import os
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(SKILL_DIR, "assets", "fonts")


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def need_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} not found. Install it (apt-get install -y ffmpeg).")


def run(cmd, quiet=True):
    """Run a command list; raise with stderr tail on failure."""
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        tail = p.stderr.decode("utf-8", "replace")[-3000:]
        raise RuntimeError(f"command failed: {' '.join(cmd[:6])} ...\n{tail}")
    return p.stdout, p.stderr.decode("utf-8", "replace")


def probe(path):
    out, _ = run(["ffprobe", "-v", "error", "-print_format", "json",
                  "-show_format", "-show_streams", path])
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0) or 0)
    res = {"path": os.path.abspath(path), "duration": round(dur, 3),
           "has_audio": a is not None, "has_video": v is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        if "rotate" in (v.get("tags") or {}):
            rot = int(v["tags"]["rotate"])
        if abs(rot) % 180 == 90:
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "0/1").split("/")
        fps = float(num) / float(den) if float(den) else 0
        res.update({"width": w, "height": h, "fps": round(fps, 3),
                    "orientation": "vertical" if h > w else ("square" if h == w else "horizontal")})
    return res


def font_path(name):
    """Resolve a font by bundled name ('Anton'), file name, or absolute path."""
    if not name:
        name = "Anton"
    if os.path.isfile(name):
        return os.path.abspath(name)
    for cand in (name, name + ".ttf", name.replace(" ", "") + ".ttf"):
        p = os.path.join(FONTS_DIR, cand)
        if os.path.isfile(p):
            return p
    # fall back to fontconfig
    try:
        out, _ = run(["fc-match", "-f", "%{file}", name])
        if out:
            return out.decode()
    except Exception:
        pass
    die(f"font not found: {name}. Bundled: {', '.join(list_fonts())}")


def list_fonts():
    return sorted(f[:-4] for f in os.listdir(FONTS_DIR) if f.endswith(".ttf"))


def ff_escape_text(s):
    """Escape text for drawtext text='...' inside a filtergraph."""
    return (s.replace("\\", "\\\\\\\\").replace("'", "’")
             .replace(":", "\\:").replace("%", "\\%").replace(",", "\\,"))


def ff_path(p):
    """Escape a file path for use inside a filtergraph option."""
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def hex_color(c):
    c = c.strip()
    if c.startswith("#"):
        return "0x" + c[1:]
    return c


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


_TEXT_W_CACHE = {}


def text_width(font_file, text, fontsize=200):
    """Rendered width in px of `text` at `fontsize` (measured with drawtext + cropdetect)."""
    key = (font_file, text, fontsize)
    if key in _TEXT_W_CACHE:
        return _TEXT_W_CACHE[key]
    W = int(fontsize * (len(text) + 2) * 1.6) + 40
    H = int(fontsize * 2.2)
    vf = (f"drawtext=fontfile='{ff_path(font_file)}':text='{ff_escape_text(text)}':"
          f"fontsize={fontsize}:fontcolor=white:x=20:y=20,cropdetect=limit=0.1:round=1:skip=0")
    _, err = run(["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:d=0.1",
                  "-vf", vf, "-frames:v", "2", "-f", "null", "-"])
    import re
    m = re.findall(r"crop=(\d+):(\d+):", err)
    w = int(m[-1][0]) if m else int(fontsize * len(text) * 0.6)
    _TEXT_W_CACHE[key] = w
    return w


def fit_fontsize(font_file, text, fontsize, max_w):
    """Shrink fontsize so the text is at most max_w px wide."""
    w = text_width(font_file, text, 200) * fontsize / 200.0
    return fontsize if w <= max_w else fontsize * max_w / w
