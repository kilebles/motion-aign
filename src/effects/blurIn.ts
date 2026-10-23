import { Easing, interpolate } from "remotion";
import type { EffectFn } from "./types";

export type BlurInParams = {
  /** Starting blur radius in px. */
  blur?: number;
  delay?: number;
  durationInFrames?: number;
};

// Resolves out of a blur like a lens pulling focus. Uses a clamped ease
// rather than a spring so the blur never overshoots below zero.
export const blurIn: EffectFn<BlurInParams> = ({ frame, params }) => {
  const { blur = 20, delay = 0, durationInFrames = 40 } = params;

  const progress = interpolate(frame - delay, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return {
    opacity: progress,
    filter: `blur(${(1 - progress) * blur}px)`,
    transform: `scale(${1 + (1 - progress) * 0.04})`,
  };
};
