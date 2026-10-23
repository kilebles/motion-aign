import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export const LightLeak: React.FC<{ seed?: string }> = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // A warm diagonal streak sweeps once across the whole clip.
  const position = interpolate(frame, [0, durationInFrames], [-30, 130], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ mixBlendMode: "screen", opacity: 0.5 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(115deg, transparent ${position - 25}%, rgba(255,180,90,0.85) ${position}%, transparent ${position + 25}%)`,
        }}
      />
    </AbsoluteFill>
  );
};
