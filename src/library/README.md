# Variant library

Everything random in `PersonalityCard` is drawn from here, from one seed
(`image|name` by default), so a render is reproducible and the picks agree
with each other.

| File | What it holds |
| --- | --- |
| `assets.ts` | Manifest of `public/library/` — video overlays, textures, backdrops and sound cues (with the peak offset). Add a stock file here first. |
| `overlaySpec.ts` | The knobs of one overlay: opacity, speed, loop, duration, fit, rotate, target (backdrop / card / screen), start time, fades, sound. |
| `themes.ts` | Backdrop + overlay stack + sound cues + entrance delay + caption palette + which card accents are allowed. |
| `cardAccents.ts` | Light on the photo card: `sweep`, `flash`, `burn`, `none`. Exactly one is picked; stock hits are slowed to 1–2s. |
| `choreographies.ts` | Matched pairs: card entrance + caption entrance + card zoom + backdrop zoom/pan. |
| `variant.ts` | `resolveVariant(seed, pins)` → theme, choreography, accent, defaulted overlay list. |

## Adding a stock overlay

1. Drop the file into `public/library/overlays/` with a short kebab-case name.
2. Probe it: `ffprobe -show_entries stream=r_frame_rate,duration,codec_type file`.
3. Add an entry to `videoAssets` in `assets.ts` (black-background light/fire = `screen`, light film with dark dirt = `multiply`).
4. Reference it from a theme in `themes.ts`, or pass it ad hoc as `extraOverlays` in props.
   On a light paper backdrop set `invert: true` + `blend: "multiply"` to turn a light-on-black clip into dark-on-white.

## Adding a sound cue

Drop the file into `public/library/audio/`, find its loudest moment
(`ffmpeg -i f.mp3 -af asetnsamples=11025,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level -f null -`),
add it to `audioAssets` with that `peakAtSeconds`, then list it in a theme's `sounds` with the
composition time the peak should land on.

## Pinning from the pipeline

```
python -m scenario.render_cards norman020/….json --theme parchmentDamage,darkRays --card-accent none
```

Any of `--theme`, `--choreography`, `--card-accent` accept one id or a comma-separated pool.
Omit them and the composition picks per clip.

## Studio

The `Themes` folder has one composition per theme with the theme pinned;
the main `PersonalityCard` composition exposes every pin in the props panel.
