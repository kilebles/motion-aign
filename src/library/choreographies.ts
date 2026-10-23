// A choreography is the *pair* of entrances (photo card + caption) plus the
// slow motion of the card and backdrop, chosen together so the moves agree:
// same direction and stagger for slides, opposite zooms for parallax, etc.

export type Motion = { effect: string; params: Record<string, unknown> };

export type Choreography = {
  id: string;
  description: string;
  card: Motion;
  caption: Motion;
  /** Slow zoom on the card box across the clip (scales about the photo). */
  cardZoom: Motion;
  /** Slow zoom/pan on the backdrop across the clip. */
  backdropMotion: Motion;
};

const F = 30; // comp fps, for readable frame maths

export const choreographies: Record<string, Choreography> = {
  rise: {
    id: "rise",
    description: "Card and caption both rise from below, staggered; slow push-in.",
    card: { effect: "fadeSlide", params: { from: "bottom", distance: 60, durationInFrames: 50 } },
    caption: {
      effect: "fadeSlide",
      params: { from: "bottom", distance: 40, delay: 30, durationInFrames: 40 },
    },
    cardZoom: { effect: "kenBurns", params: { from: 1, to: 1.14, durationInFrames: 260, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.15, to: 1.21, durationInFrames: 300, easing: "easeInOut" },
    },
  },

  settle: {
    id: "settle",
    description: "Card drops in from above while the caption rises to meet it; backdrop pulls out.",
    card: { effect: "fadeSlide", params: { from: "top", distance: 90, durationInFrames: 55 } },
    caption: {
      effect: "fadeSlide",
      params: { from: "bottom", distance: 50, delay: 34, durationInFrames: 40 },
    },
    cardZoom: { effect: "kenBurns", params: { from: 1, to: 1.12, durationInFrames: 280, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.24, to: 1.17, durationInFrames: 300, easing: "easeInOut" },
    },
  },

  glideLeft: {
    id: "glideLeft",
    description: "Card and caption glide in from the right; the backdrop pans the same way.",
    card: { effect: "fadeSlide", params: { from: "right", distance: 160, durationInFrames: 55 } },
    caption: {
      effect: "fadeSlide",
      params: { from: "right", distance: 90, delay: 26, durationInFrames: 45 },
    },
    cardZoom: { effect: "kenBurns", params: { from: 1, to: 1.1, durationInFrames: 280, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.2, to: 1.2, panX: [50, -50], durationInFrames: 300, easing: "easeInOut" },
    },
  },

  glideRight: {
    id: "glideRight",
    description: "Mirror of glideLeft: everything enters from the left.",
    card: { effect: "fadeSlide", params: { from: "left", distance: 160, durationInFrames: 55 } },
    caption: {
      effect: "fadeSlide",
      params: { from: "left", distance: 90, delay: 26, durationInFrames: 45 },
    },
    cardZoom: { effect: "kenBurns", params: { from: 1, to: 1.1, durationInFrames: 280, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.2, to: 1.2, panX: [-50, 50], durationInFrames: 300, easing: "easeInOut" },
    },
  },

  bloom: {
    id: "bloom",
    description: "Card scales up into place, caption follows with a smaller scale; backdrop pulls out.",
    card: { effect: "scaleIn", params: { from: 0.86, durationInFrames: 55 } },
    caption: { effect: "scaleIn", params: { from: 0.94, delay: 34, durationInFrames: 40 } },
    cardZoom: { effect: "kenBurns", params: { from: 1, to: 1.12, durationInFrames: 270, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.26, to: 1.17, durationInFrames: 300, easing: "easeInOut" },
    },
  },

  focus: {
    id: "focus",
    description: "Card and caption resolve out of blur, like a lens pulling focus; slow push-in.",
    card: { effect: "blurIn", params: { blur: 26, durationInFrames: 2 * F } },
    caption: { effect: "blurIn", params: { blur: 14, delay: 34, durationInFrames: 45 } },
    cardZoom: { effect: "kenBurns", params: { from: 1.03, to: 1.15, durationInFrames: 280, easing: "easeInOut" } },
    backdropMotion: {
      effect: "kenBurns",
      params: { from: 1.15, to: 1.22, durationInFrames: 300, easing: "easeInOut" },
    },
  },
};

export const choreographyIds = Object.keys(choreographies) as [string, ...string[]];
