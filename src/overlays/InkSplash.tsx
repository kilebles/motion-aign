import React from "react";
import { AbsoluteFill, Easing, interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";

const SPLATTER_COUNT = 6;

export const InkSplash: React.FC<{ seed?: string }> = ({ seed = "ink" }) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  const splatters = new Array(SPLATTER_COUNT).fill(0).map((_, i) => {
    const x = random(`${seed}-x-${i}`) * width;
    const y = random(`${seed}-y-${i}`) * height;
    // Final, fully-spread size — the blot animates up to this, not starting
    // here, so it visibly grows rather than just fading in in place.
    const size = width * (0.16 + random(`${seed}-size-${i}`) * 0.22);

    // Asymmetric border-radius per corner turns a square into an irregular
    // blot instead of a perfect circle.
    const r1 = 30 + random(`${seed}-r1-${i}`) * 50;
    const r2 = 30 + random(`${seed}-r2-${i}`) * 50;
    const r3 = 30 + random(`${seed}-r3-${i}`) * 50;
    const r4 = 30 + random(`${seed}-r4-${i}`) * 50;
    const rotate = random(`${seed}-rot-${i}`) * 360;

    // Each blot starts spreading at a staggered point across the clip and
    // keeps growing/darkening for a while — decelerating like a liquid
    // being absorbed and spreading outward, not just fading in at fixed size.
    const appearAt = random(`${seed}-appear-${i}`) * durationInFrames * 0.35;
    const spreadDuration = 70 + random(`${seed}-spread-${i}`) * 60;

    const scale = interpolate(frame, [appearAt, appearAt + spreadDuration], [0.05, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const opacity = interpolate(
      frame,
      [appearAt, appearAt + spreadDuration * 0.4],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
    );

    return {
      x,
      y,
      size,
      borderRadius: `${r1}% ${100 - r1}% ${r3}% ${100 - r3}% / ${r2}% ${r4}% ${100 - r4}% ${100 - r2}%`,
      rotate,
      scale,
      opacity,
    };
  });

  return (
    <AbsoluteFill style={{ mixBlendMode: "multiply" }}>
      {splatters.map((splatter, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: splatter.x - splatter.size / 2,
            top: splatter.y - splatter.size / 2,
            width: splatter.size,
            height: splatter.size,
            borderRadius: splatter.borderRadius,
            transform: `rotate(${splatter.rotate}deg) scale(${splatter.scale})`,
            background:
              "radial-gradient(circle, rgba(90,8,8,0.9) 0%, rgba(60,5,5,0.55) 60%, rgba(60,5,5,0) 100%)",
            opacity: splatter.opacity,
            filter: "blur(2px)",
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
