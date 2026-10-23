import type { BackdropAssetName, BlendMode } from "./assets";
import type { OverlaySpecInput, SoundSpecInput } from "./overlaySpec";

export type Palette = {
  name: string;
  years: string;
  textShadow: string;
  /** Gradient painted between backdrop and card for caption legibility. */
  scrim: string;
  cardShadow: string;
};

const darkPalette: Palette = {
  name: "#ffffff",
  years: "#bbbbbb",
  textShadow: "0 2px 10px rgba(0,0,0,0.65)",
  scrim: "linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.15) 32%, rgba(0,0,0,0) 55%)",
  cardShadow: "0 30px 70px rgba(0,0,0,0.6)",
};

const paperPalette: Palette = {
  name: "#2f2114",
  years: "#54412f",
  textShadow: "0 1px 2px rgba(255,245,225,0.6)",
  scrim: "linear-gradient(to top, rgba(70,45,20,0.28) 0%, rgba(70,45,20,0.06) 30%, rgba(70,45,20,0) 50%)",
  cardShadow: "0 24px 60px rgba(40,25,10,0.45)",
};

export type Backdrop =
  | { kind: "blurredPhoto" }
  | {
      kind: "image";
      asset: BackdropAssetName;
      /** Faint copy of the blurred personality photo over the texture, so
       *  the paper still carries the subject's colours. */
      photoBleed?: { opacity: number; blend: BlendMode };
    };

export type Theme = {
  id: string;
  description: string;
  backdrop: Backdrop;
  overlays: OverlaySpecInput[];
  /** Sound cues, placed by their peak (see overlaySpec.ts). */
  sounds?: SoundSpecInput[];
  /** Holds the card and caption back so a transition effect on the backdrop
   *  plays first and the card lands on it. Card accents shift with it. */
  entranceDelayInSeconds?: number;
  palette: Palette;
  /** Card accents this theme may be combined with (see cardAccents.ts). */
  cardAccents: string[];
  /** Choreographies this theme may use; omit = any. */
  choreographies?: string[];
};

// Shared bits ---------------------------------------------------------------

const grain = (opacity: number): OverlaySpecInput => ({
  kind: "video",
  asset: "grain",
  opacity,
  loop: true,
  target: "backdrop",
});

// Same grain clip, inverted to dark specks for light paper.
const paperGrain = (opacity: number): OverlaySpecInput => ({
  kind: "video",
  asset: "grain",
  opacity,
  loop: true,
  invert: true,
  blend: "multiply",
  target: "backdrop",
});

const specks = (opacity: number): OverlaySpecInput => ({
  kind: "image",
  asset: "specks",
  opacity,
  target: "backdrop",
});

// Themes --------------------------------------------------------------------
//
// Each theme = backdrop + overlay stack (+ sounds) + palette + which card
// accents fit. Transition-style clips (burn, flare) sit on the backdrop with
// a matching sound cue and an entrance delay, so the order on screen is:
// effect hits → card lands → caption follows.

export const themes: Record<string, Theme> = {
  classic: {
    id: "classic",
    description: "Blurred personality photo with grain and dust specks (the original look).",
    backdrop: { kind: "blurredPhoto" },
    overlays: [grain(1), specks(0.55)],
    palette: darkPalette,
    cardAccents: ["sweep", "flash", "none"],
  },

  parchmentDamage: {
    id: "parchmentDamage",
    description:
      "Parchment with slow film dust/scratches and a faint drift of dark smoke across the paper.",
    backdrop: {
      kind: "image",
      asset: "parchmentFrame",
      photoBleed: { opacity: 0.16, blend: "multiply" },
    },
    overlays: [
      {
        kind: "video",
        asset: "smoke",
        opacity: 0.22,
        speed: 0.5,
        loop: true,
        invert: true,
        blend: "multiply",
        target: "backdrop",
      },
      {
        kind: "video",
        asset: "filmDamage",
        opacity: 0.4,
        speed: 0.5,
        loop: false,
        durationInSeconds: 10,
        fit: "cover",
        rotate: 0,
        target: "backdrop",
        startAtSeconds: 1,
        fadeInSeconds: 0.5,
      },
    ],
    palette: paperPalette,
    cardAccents: ["burn", "sweep", "flash"],
  },

  parchmentRays: {
    id: "parchmentRays",
    description:
      "Parchment with slow shadow bands (inverted light rays) sweeping the paper, plus dark grain.",
    backdrop: {
      kind: "image",
      asset: "parchmentFrame",
      photoBleed: { opacity: 0.16, blend: "multiply" },
    },
    overlays: [
      paperGrain(0.3),
      {
        kind: "video",
        asset: "lightRays",
        opacity: 0.4,
        speed: 0.7,
        loop: false,
        invert: true,
        blend: "multiply",
        target: "backdrop",
        fadeInSeconds: 1,
      },
    ],
    palette: paperPalette,
    cardAccents: ["burn", "flash", "sweep"],
  },

  albumPaperBurn: {
    id: "albumPaperBurn",
    description:
      "Dark album page. A paper sheet flares up and burns away over the backdrop at 1s with a fireball hit; the card lands as the flames clear.",
    backdrop: {
      kind: "image",
      asset: "albumPage",
      photoBleed: { opacity: 0.2, blend: "soft-light" },
    },
    overlays: [
      grain(0.35),
      {
        kind: "video",
        asset: "paperBurn",
        opacity: 0.8,
        speed: 1,
        loop: false,
        durationInSeconds: 2,
        fit: "cover",
        rotate: 0,
        target: "backdrop",
        startAtSeconds: 1,
        fadeInSeconds: 0.25,
        sound: false, // the fireball cue below replaces the clip's own audio
      },
    ],
    // Flames are at their widest ~0.5s into the clip → peak at 1.5s.
    sounds: [{ asset: "fireball", peakAtSeconds: 1.5, volume: 0.9 }],
    entranceDelayInSeconds: 1.3,
    palette: darkPalette,
    // No light sweep on album pages; a slowed flash or nothing.
    cardAccents: ["none", "flash"],
  },

  darkRays: {
    id: "darkRays",
    description: "Black paint; blue light rays fade in over the backdrop at 1s on a whoosh, card follows.",
    backdrop: {
      kind: "image",
      asset: "blackPaint",
      photoBleed: { opacity: 0.28, blend: "screen" },
    },
    overlays: [
      grain(0.5),
      {
        kind: "video",
        asset: "lightRays",
        opacity: 0.6,
        speed: 1,
        loop: false,
        durationInSeconds: 10,
        fit: "cover",
        rotate: 0,
        target: "backdrop",
        startAtSeconds: 1,
        fadeInSeconds: 0.6,
        sound: false,
      },
    ],
    sounds: [{ asset: "whoosh", peakAtSeconds: 1.6, volume: 0.8 }],
    entranceDelayInSeconds: 1.0,
    palette: darkPalette,
    cardAccents: ["sweep", "flash", "none"],
  },

  darkFlare: {
    id: "darkFlare",
    description:
      "Black paint; one blue lens flare over the backdrop at 1s on a whoosh, the card lands on the flare, dust drifts after.",
    backdrop: {
      kind: "image",
      asset: "blackPaint",
      photoBleed: { opacity: 0.28, blend: "screen" },
    },
    overlays: [
      grain(0.5),
      { kind: "procedural", name: "dustParticles", opacity: 0.45, target: "backdrop" },
      {
        kind: "video",
        asset: "lightFlare",
        opacity: 0.8,
        speed: 1,
        loop: false,
        durationInSeconds: 2,
        fit: "cover",
        rotate: 0,
        target: "backdrop",
        startAtSeconds: 1,
      },
    ],
    // Flare is brightest 0.85s into the clip → peak at 1.85s.
    sounds: [{ asset: "whoosh", peakAtSeconds: 1.85, volume: 0.8 }],
    entranceDelayInSeconds: 1.5,
    palette: darkPalette,
    cardAccents: ["none", "flash"],
  },
};

export const themeIds = Object.keys(themes) as [string, ...string[]];
