import { pickOne } from "../pickOne";
import { cardAccents, cardAccentIds } from "./cardAccents";
import { choreographies, choreographyIds, type Choreography } from "./choreographies";
import {
  overlaySpecSchema,
  soundSpecSchema,
  type OverlaySpec,
  type OverlaySpecInput,
  type SoundSpec,
} from "./overlaySpec";
import { themeIds, themes, type Theme } from "./themes";

export type Pick = string | string[] | undefined;

export type VariantInput = {
  seed: string;
  theme?: Pick;
  choreography?: Pick;
  cardAccent?: Pick;
  extraOverlays?: OverlaySpecInput[];
};

export type Variant = {
  theme: Theme;
  choreography: Choreography;
  cardAccent: string;
  /** Fully-defaulted overlay stack: theme overlays + card accent + extras.
   *  Card-target overlays already include the theme's entrance delay. */
  overlays: OverlaySpec[];
  sounds: SoundSpec[];
  /** Seconds the card and caption entrances are held back. */
  entranceDelayInSeconds: number;
};

// One seed → one coherent set of picks. Every pick uses its own sub-seed so
// changing the theme pool doesn't reshuffle the choreographies, and the
// theme's own allow-lists keep incompatible combinations (e.g. a card flash
// during a full-screen burn) from ever being drawn.
export const resolveVariant = ({
  seed,
  theme,
  choreography,
  cardAccent,
  extraOverlays = [],
}: VariantInput): Variant => {
  const themeId = pickOne(theme ?? [...themeIds], `${seed}:theme`, "classic");
  const resolvedTheme = themes[themeId] ?? themes.classic;

  const choreographyPool = choreography ?? resolvedTheme.choreographies ?? [...choreographyIds];
  const choreographyId = pickOne(choreographyPool, `${seed}:choreography`, "rise");
  const resolvedChoreography = choreographies[choreographyId] ?? choreographies.rise;

  const accentPool = cardAccent ?? resolvedTheme.cardAccents ?? [...cardAccentIds];
  const accentId = pickOne(accentPool, `${seed}:accent`, "none");
  const accentOverlays = cardAccents[accentId] ?? [];

  const entranceDelayInSeconds = resolvedTheme.entranceDelayInSeconds ?? 0;

  const overlays = [...resolvedTheme.overlays, ...accentOverlays, ...extraOverlays]
    .map((spec) => overlaySpecSchema.parse(spec))
    .map((spec) =>
      spec.kind === "video" && spec.target === "card"
        ? { ...spec, startAtSeconds: spec.startAtSeconds + entranceDelayInSeconds }
        : spec,
    );

  const sounds = (resolvedTheme.sounds ?? []).map((spec) => soundSpecSchema.parse(spec));

  return {
    theme: resolvedTheme,
    choreography: resolvedChoreography,
    cardAccent: accentId,
    overlays,
    sounds,
    entranceDelayInSeconds,
  };
};
