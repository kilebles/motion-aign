import type { OverlaySpecInput } from "./overlaySpec";

// Accents drawn inside the photo card's clip. Exactly one is picked per
// clip, so two lights never stack on the same card. Start times are
// relative to the card's entrance (the theme's entrance delay is added).
//
// Stock hits are slowed down: a light on a still photo reads best over
// 1–2s, the raw clips are 0.5–1.1s.
export const cardAccents: Record<string, OverlaySpecInput[]> = {
  /** Warm diagonal streak sweeping once across the photo. */
  sweep: [{ kind: "procedural", name: "lightLeak", opacity: 1, target: "card" }],
  /** One warm flash as the card lands, stretched to ~2.2s. */
  flash: [
    {
      kind: "video",
      asset: "lightFlash",
      opacity: 0.5,
      speed: 0.5,
      loop: false,
      target: "card",
      startAtSeconds: 1.1,
    },
  ],
  /** Film burn flash over the photo only, stretched to ~1.3s. */
  burn: [
    {
      kind: "video",
      asset: "filmBurn",
      opacity: 0.85,
      speed: 0.4,
      loop: false,
      target: "card",
      startAtSeconds: 1.2,
      sound: true,
    },
  ],
  none: [],
};

export const cardAccentIds = Object.keys(cardAccents) as [string, ...string[]];
