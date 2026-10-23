import React from "react";
import { AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";

const PARTICLE_COUNT = 55;

export const DustParticles: React.FC<{ seed?: string }> = ({ seed = "dust" }) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  const particles = new Array(PARTICLE_COUNT).fill(0).map((_, i) => {
    const baseX = random(`${seed}-x-${i}`) * width;
    const baseY = random(`${seed}-y-${i}`) * height;
    const speed = 0.15 + random(`${seed}-speed-${i}`) * 0.35;
    const sway = (random(`${seed}-sway-${i}`) - 0.5) * 60;
    const risen = interpolate(frame, [0, durationInFrames], [0, height * speed]);
    const y = (((baseY - risen) % height) + height) % height;
    const x = baseX + Math.sin(frame / 40 + i) * sway * 0.3;
    const size = 3 + random(`${seed}-size-${i}`) * 5;
    const opacity = 0.35 + random(`${seed}-op-${i}`) * 0.5;
    return { x, y, size, opacity };
  });

  return (
    <AbsoluteFill style={{ mixBlendMode: "screen" }}>
      {particles.map((particle, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: particle.x,
            top: particle.y,
            width: particle.size,
            height: particle.size,
            borderRadius: "50%",
            background: "white",
            boxShadow: `0 0 ${particle.size * 2}px ${particle.size * 0.6}px rgba(255,255,255,0.8)`,
            opacity: particle.opacity,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
