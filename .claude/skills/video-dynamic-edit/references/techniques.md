# Technique catalogue (measured from two reference edits)

Both references are 1280x720 / 30 fps travel edits. Cut times were measured with
ffmpeg scene detection, and loudness with astats.

## Style A: "dynamic" (Barcelona, ~21 s, TikTok/Reels energy)

| time | what happens | technique |
|---|---|---|
| 0–2.6 s | ~13 clips: streets, top-down coffee, market, window, POV | **flash-cut intro**, 0.15–0.23 s per clip (5–7 frames, quarter beats). The music is loud here (≈ −7 dB). |
| 2.6 s | hard stop on one wide static shot (Park Güell) | **chaos → calm contrast**: the music drops to ≈ −20 dB |
| 3–5 s | small white serif "Welcome to"; the person walks out of frame | the frame is cleared before the title lands |
| ~5.3 s | yellow **BARCELONA** | |
| 5.3–11 s | the title font changes every 2–3 frames (grotesk, script, hand-drawn, italic, black) | **font cycling**, the signature effect |
| 8.4–11 s | the title stays put, the footage under it changes every ~0.3 s | **title as anchor**: the background changes, the text doesn't |
| 9–11 s | the visible picture shrinks vertically to a thin strip around the title, black around it | **mask collapse / letterbox squeeze**, on a held synth note (flat −15 dB) = tension |
| 11–18 s | full-screen cuts every 0.3–0.4 s, exactly on the beat dips | **beat cuts**; shot types repeat as rhymes: top-down food, coffee, walking POV, nightclub, market |

Recipe: fast → stop → title build → squeeze → release into beat cuts. No transitions,
only hard cuts; the energy comes from cut rate and typography.

## Style B: "cinematic" (France, ~18 s)

| time | what happens | technique |
|---|---|---|
| 0–4 s | cathedral through leaves, sun flare, slow drift | **foreground + parallax**, depth layers |
| 0.8–1.5 s | "FRANCE" appears from the centre outwards (AN → RANC → FRANCE), white serif | **centre mask reveal** |
| 4.3–5 s | the title fades, a radial blur pushes in, white frame, a wave rushes in | **zoom-blur + flash transition** |
| 5–6.3 s | the camera races over pebbles and surf | **speed ramp** (fast → normal) |
| 6.3–14 s | cliffs, Seine, seagull, couple on the beach, woman in the wind | cuts every ~0.7 s = 1 beat at 84 BPM |
| ~7.3 s | an orange burn over the couple shot | **light leak** |
| ~12.5 s | a black frame, then a gold interior | **dip to black** = chapter change (nature → interiors) |
| 12.7–14 s | stained glass defocuses into white, then a rose window | **defocus/overexposure transition** |
| 14.5 s | the flag slides in from the right with motion blur | **whip pan** |
| 15–18 s | the flag holds, the picture darkens, the music fades | **fade-out ending** |

Look: warm golden-hour grade, lifted blacks, haze/bloom, teal & orange accents,
grain, vignette. Almost every shot has something in the foreground.

## Rules from both
1. Every cut lands on the beat grid: 0.3–0.45 s (dynamic) or ~0.7 s (cinematic).
2. Break the tempo before the title: a held shot plus a quiet or held note in the music.
3. The title is part of the edit: it cycles or reveals, and it ties clips together.
4. The opening and ending are distinct: flash intro or parallax opener at the start, fade, flag or wide shot at the end.
5. Repeat shot types (top-down, POV, water) so the edit reads as one style.

## Choosing footage per role
- **opener** (cinematic): slow, beautiful, with depth and a foreground; 3–4 s usable.
- **hero** (dynamic title shot): wide and static, with clean sky or space for the title; 4–6 s usable.
- **closer**: a symbol of the place (flag, skyline, sunset, landmark), wide, calm.
- **ramp clip** (cinematic, after the opener): fast camera movement, water, road, POV.
- **flash-intro clips**: anything with strong colour or a clear subject. They only last 6 frames.
- Night or interior shots go together, ideally after a `dip_black` or `blur` transition.
- Avoid shaky starts: skip the first 0.3 s of phone clips (the planner does this).
