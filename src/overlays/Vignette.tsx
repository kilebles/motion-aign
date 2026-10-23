import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const Vignette: React.FC<{ seed?: string }> = () => {
  const frame = useCurrentFrame();
  const pulse = interpolate(Math.sin(frame / 45), [-1, 1], [0.55, 0.7]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${pulse}) 100%)`,
      }}
    />
  );
};
