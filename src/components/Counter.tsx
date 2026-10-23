import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export type CounterProps = {
  value: number;
  unit?: string;
  label?: string;
  countDelay?: number;
  countDurationInFrames?: number;
  style?: React.CSSProperties;
};

export const Counter: React.FC<CounterProps> = ({
  value,
  unit = "%",
  label,
  countDelay = 10,
  countDurationInFrames = 30,
  style,
}) => {
  const frame = useCurrentFrame();

  const countValue = Math.round(
    interpolate(frame - countDelay, [0, countDurationInFrames], [0, value], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );

  return (
    <div
      style={{
        background: "#1a1a1acc",
        padding: "24px 40px",
        borderRadius: 16,
        ...style,
      }}
    >
      <div style={{ fontSize: 64, color: "white", fontWeight: 700 }}>
        {countValue}
        {unit}
      </div>
      {label && <div style={{ fontSize: 28, color: "#aaa" }}>{label}</div>}
    </div>
  );
};
