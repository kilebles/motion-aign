// Asset manifest for public/library/. Every file the compositions can reach
// for is described here once — path, native timing, how it should be blended
// and whether it carries sound — so themes and overlay specs refer to assets
// by name and never to raw paths.
//
// Adding a stock overlay: drop the file into public/library/overlays/, probe
// it (`ffprobe -show_entries stream=r_frame_rate,duration file`) and add an
// entry below. Black-background light/fire/smoke clips are "screen"; light
// clips with dark dirt/scratches are "multiply".

export type BlendMode = "screen" | "multiply" | "overlay" | "soft-light" | "normal";

export type VideoAsset = {
  src: string;
  fps: number;
  durationInSeconds: number;
  blend: BlendMode;
  hasAudio: boolean;
  /** Original stock file name, for tracing the source. */
  source: string;
};

export const videoAssets = {
  /** Light grey film with dark dust and scratch marks. */
  filmDamage: {
    src: "library/overlays/film-damage.mp4",
    fps: 23.976,
    durationInSeconds: 15.0,
    blend: "multiply",
    hasAudio: false,
    source: "Film Damage 16.mp4",
  },
  /** Red/orange film burn flash, very short (13 frames), ends on black. */
  filmBurn: {
    src: "library/overlays/film-burn.mp4",
    fps: 25,
    durationInSeconds: 0.52,
    blend: "screen",
    hasAudio: true,
    source: "Free Film Burn (353).mp4",
  },
  /** Slow diagonal blue-ish god rays on black. */
  lightRays: {
    src: "library/overlays/light-rays.mp4",
    fps: 29.97,
    durationInSeconds: 15.0,
    blend: "screen",
    hasAudio: true,
    source: "Light Rays 4k (742).mp4",
  },
  /** One bright lens-flare pass, dark → flare → black. */
  lightFlare: {
    src: "library/overlays/light-flare.mp4",
    fps: 25,
    durationInSeconds: 2.2,
    blend: "screen",
    hasAudio: false,
    source: "Light transition (453).mp4",
  },
  /** Short warm flash on black (~1.1s). */
  lightFlash: {
    src: "library/overlays/light-flash.mp4",
    fps: 25,
    durationInSeconds: 1.12,
    blend: "screen",
    hasAudio: false,
    source: "Light_transition.mp4",
  },
  /** White sheet that burns away to black — a reveal transition. */
  paperBurn: {
    src: "library/overlays/paper-burn.mp4",
    fps: 24,
    durationInSeconds: 2.08,
    blend: "screen",
    hasAudio: true,
    source: "Paper Burning Transition Overlay 4k - 546.mp4",
  },
  /** White grain specks on black, 10s. */
  grain: {
    src: "library/overlays/grain.mov",
    fps: 25,
    durationInSeconds: 10.0,
    blend: "screen",
    hasAudio: false,
    source: "Grain.mov",
  },
  /** Rolling smoke on black, ~5.3s. */
  smoke: {
    src: "library/overlays/smoke.webm",
    fps: 30,
    durationInSeconds: 5.3,
    blend: "screen",
    hasAudio: false,
    source: "dust_impact.webm",
  },
} as const satisfies Record<string, VideoAsset>;

export type VideoAssetName = keyof typeof videoAssets;

export type ImageAsset = {
  src: string;
  blend: BlendMode;
  source: string;
};

export const imageAssets = {
  /** White specks on transparent (its own alpha does the blending). */
  specks: { src: "library/textures/specks.png", blend: "normal", source: "texture_overlay.png" },
} as const satisfies Record<string, ImageAsset>;

export type ImageAssetName = keyof typeof imageAssets;

export type AudioAsset = {
  src: string;
  durationInSeconds: number;
  /** Where the loudest moment sits inside the file — sounds are placed so
   *  this peak lands on the visual hit, not the file start. */
  peakAtSeconds: number;
  source: string;
};

export const audioAssets = {
  /** Short fire whoomp, ~2.2s, peak at 0.6s. Pairs with the paper burn. */
  fireball: {
    src: "library/audio/fireball.mp3",
    durationInSeconds: 2.19,
    peakAtSeconds: 0.6,
    source: "2 fireball.mp3",
  },
  /** Rising whoosh with a long tail, ~5.3s, peak at 1.35s. Pairs with the flare/rays. */
  whoosh: {
    src: "library/audio/whoosh.mp3",
    durationInSeconds: 5.33,
    peakAtSeconds: 1.35,
    source: "3transition-9.mp3",
  },
} as const satisfies Record<string, AudioAsset>;

export type AudioAssetName = keyof typeof audioAssets;

export type BackdropAsset = {
  src: string;
  /** Drives the default caption palette: dark text on light paper, light on dark. */
  tone: "light" | "dark";
  source: string;
};

// NOTE: the three reference backdrops are low-res (≤ 736px wide) and get
// upscaled ~2.6× to 1920. Replace them with ≥ 1920px versions of the same
// look when available — same path, nothing else to change.
export const backdropAssets = {
  parchmentFrame: {
    src: "library/backdrops/parchment-frame.jpg",
    tone: "light",
    source: "photo1.jpg",
  },
  albumPage: { src: "library/backdrops/album-page.jpg", tone: "dark", source: "photo2.jpg" },
  blackPaint: { src: "library/backdrops/black-paint.jpg", tone: "dark", source: "photo3.jpg" },
} as const satisfies Record<string, BackdropAsset>;

export type BackdropAssetName = keyof typeof backdropAssets;
