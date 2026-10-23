import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

export const FilmGrain: React.FC<{ seed?: string }> = ({ seed = "grain" }) => {
  const frame = useCurrentFrame();
  // Cycle through a handful of turbulence seeds so the noise crawls instead
  // of sitting static on the frame.
  const turbulenceSeed = (frame % 6) + 1;
  const filterId = `film-grain-${seed}`;

  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: 0.4 }}>
      <svg width="100%" height="100%">
        <filter id={filterId}>
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.85"
            numOctaves={2}
            seed={turbulenceSeed}
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
          {/* Raw turbulence noise averages out to mid-gray, which
              "overlay" blending barely touches — push the values toward
              black/white so the grain actually reads once blended. */}
          <feComponentTransfer>
            <feFuncR type="linear" slope="3.5" intercept="-1.25" />
            <feFuncG type="linear" slope="3.5" intercept="-1.25" />
            <feFuncB type="linear" slope="3.5" intercept="-1.25" />
          </feComponentTransfer>
        </filter>
        <rect width="100%" height="100%" filter={`url(#${filterId})`} />
      </svg>
    </AbsoluteFill>
  );
};
