# plan.json — format reference

`render.py` renders exactly what plan.json says. `make_plan.py` writes a draft;
edit it by hand to change anything. Paths are relative to the plan file.
Times are seconds on the **output** timeline (0 = first frame = `music.start`).

```jsonc
{
  "output": {
    "width": 1080, "height": 1920, "fps": 30,     // vertical 1080x1920 | horizontal 1920x1080 | square 1080x1080
    "path": "out/final.mp4",
    "supersample": 2,      // zoom quality (1 = faster, 2 = smooth Ken Burns)
    "crf": 18, "preset": "medium",
    "work_dir": "render_tmp"
  },
  "music": {"path": "../song.mp3", "start": 12.34, "fade_out": 1.2, "volume": 1.0},
  // omit "music" for a silent render

  "grade": "golden",       // none | vivid | warm_film | golden | teal_orange | moody | bw
  "exposure": 0.0,         // -0.1..0.1 brightness offset
  "glow": 0.22,            // 0..0.5 bloom (cinematic haze)
  "grain": 6,              // 0..15 film grain
  "vignette": true,
  "fade_in": 0, "fade_out": 1.0,   // to/from black, whole video

  "segments": [            // played back to back; each one is one shot
    {
      "clip": "../raw/IMG_0412.MOV",   // video or photo (jpg/png = still with Ken Burns)
      "in": 3.2,           // source in-point (s)
      "dur": 0.44,         // OUTPUT duration (s); boundaries are rounded to frames cumulatively
      "speed": 1.0,        // constant speed (2 = 2x faster; 0.5 = slow motion, needs 60fps source to look smooth)
      "ramp": [2.6, 1.0],  // speed ramp from start speed to end speed (overrides speed)
      "reverse": false,
      "zoom": [1.0, 1.08], // scale at start / end (push-in; [1.06,1.0] = pull-out)
      "focus": [0.5, 0.5], // crop centre 0..1 (x, y) — e.g. [0.3,0.5] keeps the left subject in a vertical crop
      "transition_in": {"type": "zoom_blur", "frames": 5},   // between previous shot and this one
      "light_leak": {"at": "end", "dur": 0.5, "side": "right", "strength": 1.0}  // or true
    }
  ],

  "overlays": [            // drawn over the whole timeline in this order: mask_collapse first, then text
    {"type": "text", "text": "Welcome to", "font": "PlayfairDisplay", "size": 0.035,
     "color": "white", "y": 0.44, "start": 2.8, "end": 11.5, "fade_in": 0.2, "fade_out": 0},

    {"type": "title_cycle", "text": "BARCELONA", "start": 5.1, "end": 11.5,
     "size": 0.15, "color": "#F5D400", "y": 0.5,
     "fonts": ["Anton", "Pacifico", "PermanentMarker", "PlayfairDisplay", "ArchivoBlack", "Caveat", "Monoton"],
     "cycle_frames": 3,      // frames per font
     "order": "random",      // or "sequence"
     "jitter": true,         // sometimes hold a font for 2 steps (feels hand-made)
     "settle_at": null,      // time to stop cycling and rest on fonts[0]
     "equal_width": true,    // every font scaled to the same visual width
     "fit": 0.88},           // max width as a fraction of the frame

    {"type": "title_reveal", "text": "FRANCE", "font": "Cinzel", "size": 0.16, "color": "white",
     "y": 0.5, "start": 0.6, "end": 2.7, "reveal": 0.8, "fade_out": 0.45},
     // letters appear from the centre outwards over `reveal` seconds

    {"type": "mask_collapse", "start": 8.0, "end": 11.5, "collapse": 3.0, "keep": 0.11, "y": 0.5,
     "ease": "inout"}
     // black bars close in from top and bottom until a strip of `keep` (fraction of height)
     // around `y` remains; at `end` the bars disappear (hard cut back to full frame = the punch)
  ]
}
```

`size` is a fraction of the output **width** (font size in px = size × width).
`y` is the centre of the text as a fraction of the height.

## Transitions (`transition_in.type`)
| type | look | default frames/side | use for |
|---|---|---|---|
| `cut` | hard cut | 0 | default; beat cuts |
| `flash_white` (`flash`) | fade to white and back | 3 | accent hit, energy jump |
| `dip_black` | quick dip to black | 4 | change of chapter / location / day→night |
| `zoom_blur` | outgoing pushes in + blur + white, incoming pulls back from zoom | 5 | after the opener, into a speed ramp |
| `zoom_in` | same push without blur/white | 5 | punchier, cleaner |
| `whip` / `whip_right` | horizontal slide with motion blur | 5 | into the closing shot, between two moving shots |
| `blur` | defocus + slight brighten | 6 | into interiors, night, stained glass, lights |

The frames are taken from both shots (last k of the previous one, first k of this one),
so the beat-synced cut point is unchanged.

## Bundled fonts (assets/fonts, all SIL OFL)
Latin only: Anton, BebasNeue, ArchivoBlack, AbrilFatface, PermanentMarker, Monoton, Cinzel
With Cyrillic: Oswald, RussoOne, Unbounded, Rubik, RubikMonoOne, Lobster, MarckScript,
Pacifico, Caveat, PlayfairDisplay, CormorantGaramond.
**For Russian text use only the Cyrillic fonts.** Latin-only fonts render empty boxes.
A font can also be an absolute path to any .ttf/.otf the user sends.
Good Cyrillic cycle set: `["RussoOne","Lobster","Unbounded","MarckScript","Oswald","Caveat","PlayfairDisplay"]`.
