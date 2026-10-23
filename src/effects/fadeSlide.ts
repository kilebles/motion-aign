import { interpolate, spring } from "remotion";
import type { EffectFn } from "./types";

export type FadeSlideParams = {
  from?: "top" | "bottom" | "left" | "right";
  distance?: number;
  delay?: number;
  durationInFrames?: number;
};

export const fadeSlide: EffectFn<FadeSlideParams> = ({
  frame,
  fps,
  params,
}) => {
  const {
    from = "bottom",
    distance = 100,
    delay = 0,
    durationInFrames = 20,
  } = params;

  const progress = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    durationInFrames,
  });

  const offset = interpolate(progress, [0, 1], [distance, 0]);
  const axis = from === "left" || from === "right" ? "X" : "Y";
  const sign = from === "right" || from === "bottom" ? 1 : -1;

  return {
    opacity: interpolate(progress, [0, 1], [0, 1], {
      extrapolateRight: "clamp",
    }),
    transform: `translate${axis}(${sign * offset}px)`,
  };
};
