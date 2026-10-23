import { interpolate, spring } from "remotion";
import type { EffectFn } from "./types";

export type ScaleInParams = {
  from?: number;
  delay?: number;
  durationInFrames?: number;
};

export const scaleIn: EffectFn<ScaleInParams> = ({ frame, fps, params }) => {
  const { from = 0.6, delay = 0, durationInFrames = 20 } = params;

  const progress = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    durationInFrames,
  });

  return {
    opacity: interpolate(progress, [0, 1], [0, 1], {
      extrapolateRight: "clamp",
    }),
    transform: `scale(${interpolate(progress, [0, 1], [from, 1])})`,
  };
};
