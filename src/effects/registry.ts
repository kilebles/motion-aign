import { pickOne } from "../pickOne";
import { blurIn } from "./blurIn";
import { fadeSlide } from "./fadeSlide";
import { kenBurns } from "./kenBurns";
import { scaleIn } from "./scaleIn";
import type { EffectFn } from "./types";

// Each effect narrows its own params; the registry erases that so Layer can
// dispatch by name. Unknown keys are simply ignored by the effect.
export const effectRegistry: Record<string, EffectFn> = {
  fadeSlide: fadeSlide as EffectFn,
  scaleIn: scaleIn as EffectFn,
  blurIn: blurIn as EffectFn,
  kenBurns: kenBurns as EffectFn,
  none: () => ({}),
};

export type EffectName = keyof typeof effectRegistry;

// Resolves `effect: "fadeSlide"` as-is, or `effect: ["fadeSlide", "scaleIn"]`
// into one deterministic pick per seed — same seed always picks the same
// effect, so re-renders stay reproducible instead of flickering between takes.
export const pickEffect = (effect: string | string[], seed: string): string =>
  pickOne(effect, seed, "none");
