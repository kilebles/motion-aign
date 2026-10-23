import { random } from "remotion";

// Resolves a single value as-is, or one entry from an array, deterministically
// per seed — same seed always picks the same result, so re-renders stay
// reproducible instead of flickering between takes.
export const pickOne = <T,>(value: T | T[], seed: string, fallback: T): T => {
  if (!Array.isArray(value)) return value;
  if (value.length === 0) return fallback;
  const index = Math.floor(random(seed) * value.length);
  return value[index];
};
