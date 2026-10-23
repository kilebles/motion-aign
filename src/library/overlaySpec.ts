import { z } from "zod";
import { audioAssets, imageAssets, videoAssets, type BlendMode } from "./assets";

const asEnum = (keys: string[]) => z.enum(keys as [string, ...string[]]);

const blendSchema = z.enum(["screen", "multiply", "overlay", "soft-light", "normal"]);

// Where in the stack an overlay is drawn:
//   backdrop — over the background only, under the photo card and caption
//   screen   — over everything, card and caption included
//   card     — inside the photo card's rounded clip
export const overlayTargetSchema = z.enum(["backdrop", "screen", "card"]);
export type OverlayTarget = z.infer<typeof overlayTargetSchema>;

// A stock video overlay, described with the same knobs a motion designer
// would set by hand: opacity, speed, loop, duration, fit, rotation, target,
// start time, sound.
export const videoOverlaySchema = z.object({
  kind: z.literal("video"),
  asset: asEnum(Object.keys(videoAssets)),
  /** 0..1 */
  opacity: z.number().min(0).max(1).default(1),
  /** Playback rate: 0.5 = half speed. */
  speed: z.number().positive().default(1),
  loop: z.boolean().default(false),
  /** Seconds on screen. Omit = until the end of the clip. A non-looping
   *  overlay is also cut at its own native length so it never freezes on
   *  its last frame. */
  durationInSeconds: z.number().positive().optional(),
  fit: z.enum(["cover", "contain"]).default("cover"),
  /** Degrees. The clip is scaled up so a rotated "cover" still covers. */
  rotate: z.number().default(0),
  target: overlayTargetSchema.default("backdrop"),
  startAtSeconds: z.number().min(0).default(0),
  /** Seconds of fade in/out at the edges so long overlays don't pop. */
  fadeInSeconds: z.number().min(0).default(0),
  fadeOutSeconds: z.number().min(0).default(0),
  /** Overrides the asset's default blend mode. */
  blend: blendSchema.optional(),
  /** Invert the clip's colours. Turns a black-background "screen" overlay
   *  (light on black) into a "multiply" one (dark on white) so the same
   *  stock clip also works on light paper backdrops. Set blend: "multiply". */
  invert: z.boolean().default(false),
  /** Play the clip's own audio (only matters for assets that have one). */
  sound: z.boolean().default(false),
});

export const imageOverlaySchema = z.object({
  kind: z.literal("image"),
  asset: asEnum(Object.keys(imageAssets)),
  opacity: z.number().min(0).max(1).default(1),
  target: overlayTargetSchema.default("backdrop"),
  blend: blendSchema.optional(),
});

// Procedural overlays from src/overlays (fog, dustParticles, lightLeak, ...).
export const proceduralOverlaySchema = z.object({
  kind: z.literal("procedural"),
  name: z.string(),
  opacity: z.number().min(0).max(1).default(1),
  target: overlayTargetSchema.default("backdrop"),
});

export const overlaySpecSchema = z.discriminatedUnion("kind", [
  videoOverlaySchema,
  imageOverlaySchema,
  proceduralOverlaySchema,
]);

export type VideoOverlaySpec = z.infer<typeof videoOverlaySchema>;
export type ImageOverlaySpec = z.infer<typeof imageOverlaySchema>;
export type ProceduralOverlaySpec = z.infer<typeof proceduralOverlaySchema>;
export type OverlaySpec = z.infer<typeof overlaySpecSchema>;

// Input shapes (before zod fills the defaults) — what themes are written in.
export type OverlaySpecInput = z.input<typeof overlaySpecSchema>;

// A sound cue. `peakAtSeconds` is where its loudest moment should land in
// the composition; the file is offset by its own peak so the hit lines up
// with the visual it accompanies.
export const soundSpecSchema = z.object({
  asset: asEnum(Object.keys(audioAssets)),
  peakAtSeconds: z.number().min(0),
  volume: z.number().min(0).max(1).default(1),
});

export type SoundSpec = z.infer<typeof soundSpecSchema>;
export type SoundSpecInput = z.input<typeof soundSpecSchema>;

export const resolveBlend = (spec: OverlaySpec): BlendMode => {
  if (spec.kind === "video") return spec.blend ?? videoAssets[spec.asset as keyof typeof videoAssets].blend;
  if (spec.kind === "image") return spec.blend ?? imageAssets[spec.asset as keyof typeof imageAssets].blend;
  return "normal";
};
