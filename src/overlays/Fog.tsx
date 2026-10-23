import React from "react";
import { AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";

const BLOB_COUNT = 4;

export const Fog: React.FC<{ seed?: string }> = ({ seed = "fog" }) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  const blobs = new Array(BLOB_COUNT).fill(0).map((_, i) => {
    const startX = random(`${seed}-x-${i}`) * width;
    const startY = height * 0.25 + random(`${seed}-y-${i}`) * height * 0.6;
    const driftDirection = random(`${seed}-dir-${i}`) - 0.5;
    const drift = interpolate(frame, [0, durationInFrames], [0, driftDirection * width * 0.35]);
    const size = width * (0.35 + random(`${seed}-size-${i}`) * 0.25);
    return { x: startX + drift, y: startY, size };
  });

  return (
    <AbsoluteFill style={{ mixBlendMode: "screen", opacity: 0.6 }}>
      {blobs.map((blob, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: blob.x - blob.size / 2,
            top: blob.y - blob.size / 2,
            width: blob.size,
            height: blob.size,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(255,255,255,0) 65%)",
            filter: "blur(14px)",
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
