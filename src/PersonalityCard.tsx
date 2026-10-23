import { loadFont } from "@remotion/fonts";
import React from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { z } from "zod";
import { Layer } from "./components/Layer";
import { backdropAssets } from "./library/assets";
import { cardAccentIds } from "./library/cardAccents";
import { choreographyIds } from "./library/choreographies";
import { overlaySpecSchema } from "./library/overlaySpec";
import { themeIds } from "./library/themes";
import { resolveVariant } from "./library/variant";
import { OverlayStack } from "./overlays/OverlayStack";
import { SoundStack } from "./overlays/SoundStack";

loadFont({
  family: "Minion Pro",
  url: staticFile("fonts/MinionPro-Bold.otf"),
  weight: "700",
});

// "one id" or "a pool of ids to pick from" — resolved per seed in resolveVariant.
const pickSchema = (ids: [string, ...string[]]) =>
  z.union([z.enum(ids), z.array(z.enum(ids))]).optional();

export const personalityCardSchema = z.object({
  image: z.string(),
  name: z.string(),
  years: z.string().optional(),
  /** Drives every random pick. Defaults to image + name, so two clips of the
   *  same person with different photos still get different variants. */
  seed: z.string().optional(),
  /** Backdrop + overlay stack + palette. Omit = any theme. */
  theme: pickSchema(themeIds),
  /** Matched card + caption entrance and slow motion. Omit = any. */
  choreography: pickSchema(choreographyIds),
  /** Light on the photo card: sweep, flash or none — never two at once.
   *  Omit = whatever the chosen theme allows. */
  cardAccent: pickSchema(cardAccentIds),
  /** Ad-hoc overlays appended to the theme's stack (same spec as themes.ts). */
  extraOverlays: z.array(overlaySpecSchema).default([]),
});

export type PersonalityCardProps = z.infer<typeof personalityCardSchema>;

export const PersonalityCard: React.FC<PersonalityCardProps> = ({
  image,
  name,
  years,
  seed,
  theme,
  choreography,
  cardAccent,
  extraOverlays,
}) => {
  const variantSeed = seed ?? `${image}|${name}`;
  const variant = resolveVariant({
    seed: variantSeed,
    theme,
    choreography,
    cardAccent,
    extraOverlays,
  });
  const { fps } = useVideoConfig();
  const { palette, backdrop } = variant.theme;
  const { card, caption, cardZoom, backdropMotion } = variant.choreography;

  // Themes with a backdrop transition hold the card back so the effect
  // plays first; the choreography's own stagger is kept on top of that.
  const entranceShift = Math.round(variant.entranceDelayInSeconds * fps);
  const delayed = (params: Record<string, unknown>) => ({
    ...params,
    delay: Number(params.delay ?? 0) + entranceShift,
  });

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* Far plane. There's no 3D camera in a 2D composition, so depth is
          faked with differential motion: the backdrop gets a small scale/pan
          delta over the whole clip (barely moves), while the photo card gets
          a bigger delta over a shorter window — the two drift apart like a
          real camera push-in. Which direction each goes is the choreography's
          call, so the pair always agrees. */}
      <Layer effect={backdropMotion.effect} effectParams={backdropMotion.params} style={{ inset: 0 }}>
        {backdrop.kind === "blurredPhoto" ? (
          <Img
            src={staticFile(image)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "blur(14px) brightness(0.5)",
            }}
          />
        ) : (
          <>
            <Img
              src={staticFile(backdropAssets[backdrop.asset].src)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
            {backdrop.photoBleed && (
              <AbsoluteFill
                style={{
                  mixBlendMode: backdrop.photoBleed.blend,
                  opacity: backdrop.photoBleed.opacity,
                }}
              >
                <Img
                  src={staticFile(image)}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    filter: "blur(30px)",
                  }}
                />
              </AbsoluteFill>
            )}
          </>
        )}
      </Layer>

      {/* Backdrop-only overlays — inserted before the card, so the photo
          (drawn later, on top) is never touched by them. */}
      <OverlayStack overlays={variant.overlays} target="backdrop" seed={variantSeed} />

      <AbsoluteFill style={{ background: palette.scrim }} />

      {/* Near plane. The zoom lives on this outer box (whose center is the
          photo's center, so it scales about the photo, not the frame) and the
          entrance on the inner one — Layer applies one effect each. */}
      {/* The box starts smaller than the space available so the push-in has
          headroom to grow into instead of colliding with the caption. */}
      <Layer
        effect={cardZoom.effect}
        effectParams={cardZoom.params}
        style={{ top: 80, bottom: 270, left: 0, right: 0 }}
      >
        <Layer
          effect={card.effect}
          effectParams={delayed(card.params)}
          style={{
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* height:100% on this wrapper plus width:auto on the image sizes
              the wrapper to hug the photo's own rendered edges — so the
              borderRadius clip and the card accents apply to the actual
              photo, not the whole flex area it's centered in. */}
          <div
            style={{
              position: "relative",
              height: "100%",
              maxWidth: "100%",
              borderRadius: 24,
              overflow: "hidden",
              boxShadow: palette.cardShadow,
            }}
          >
            <Img
              src={staticFile(image)}
              style={{
                height: "100%",
                width: "auto",
                maxWidth: "100%",
                objectFit: "contain",
                display: "block",
              }}
            />
            <OverlayStack overlays={variant.overlays} target="card" seed={variantSeed} />
          </div>
        </Layer>
      </Layer>

      <Layer
        effect={caption.effect}
        effectParams={delayed(caption.params)}
        style={{ bottom: 50, left: 0, right: 0, textAlign: "center" }}
      >
        <div
          style={{
            fontSize: 68,
            color: palette.name,
            fontFamily: '"Minion Pro", serif',
            fontWeight: 700,
            textShadow: palette.textShadow,
          }}
        >
          {name}
        </div>
        {years && (
          <div
            style={{
              fontSize: 34,
              color: palette.years,
              marginTop: 10,
              fontFamily: "sans-serif",
              textShadow: palette.textShadow,
            }}
          >
            {years}
          </div>
        )}
      </Layer>

      {/* Full-screen overlays — over the card and caption too. */}
      <OverlayStack overlays={variant.overlays} target="screen" seed={variantSeed} />

      <SoundStack sounds={variant.sounds} />
    </AbsoluteFill>
  );
};
