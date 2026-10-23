import type React from "react";
import { pickOne } from "../pickOne";
import { DustParticles } from "./DustParticles";
import { FilmGrain } from "./FilmGrain";
import { Fog } from "./Fog";
import { InkSplash } from "./InkSplash";
import { LightLeak } from "./LightLeak";
import { Vignette } from "./Vignette";

export const overlayRegistry: Record<string, React.FC<{ seed?: string }>> = {
  fog: Fog,
  lightLeak: LightLeak,
  filmGrain: FilmGrain,
  dustParticles: DustParticles,
  vignette: Vignette,
  inkSplash: InkSplash,
  none: () => null,
};

export type OverlayName = keyof typeof overlayRegistry;

// Resolves `overlay: "fog"` as-is, or `overlay: ["fog", "dustParticles", ...]`
// into one deterministic pick per seed — same seed (e.g. the personality's
// name) always picks the same overlay, so re-renders stay reproducible.
export const pickOverlay = (overlay: string | string[], seed: string): string =>
  pickOne(overlay, seed, "none");
