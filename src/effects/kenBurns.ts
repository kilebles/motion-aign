import { Easing, interpolate } from "remotion";
import type { EffectFn } from "./types";

export type KenBurnsParams = {
  from?: number;
  to?: number;
  /** Horizontal drift in px, [start, end]. */
  panX?: [number, number];
  /** Vertical drift in px, [start, end]. */
  panY?: [number, number];
  durationInFrames?: number;
  easing?: "linear" | "easeInOut";
};

export const kenBurns: EffectFn<KenBurnsParams> = ({ frame, params }) => {
  const {
    from = 1,
    to = 1.12,
    panX = [0, 0],
    panY = [0, 0],
    durationInFrames = 150,
    easing = "linear",
  } = params;
  const easingFn = easing === "easeInOut" ? Easing.inOut(Easing.cubic) : undefined;
  const options = {
    extrapolateRight: "clamp" as const,
    ...(easingFn ? { easing: easingFn } : {}),
  };

  const scale = interpolate(frame, [0, durationInFrames], [from, to], options);
  const x = interpolate(frame, [0, durationInFrames], panX, options);
  const y = interpolate(frame, [0, durationInFrames], panY, options);

  return {
    transform: `translate(${x}px, ${y}px) scale(${scale})`,
  };
};
