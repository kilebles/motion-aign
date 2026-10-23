import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { effectRegistry } from "../effects/registry";

export type LayerProps = {
  effect: string;
  effectParams?: Record<string, unknown>;
  style?: React.CSSProperties;
  children: React.ReactNode;
};

export const Layer: React.FC<LayerProps> = ({
  effect,
  effectParams = {},
  style,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const effectFn = effectRegistry[effect] ?? effectRegistry.none;
  const { opacity, transform, filter } = effectFn({ frame, fps, params: effectParams });

  return (
    <div style={{ position: "absolute", opacity, transform, filter, ...style }}>
      {children}
    </div>
  );
};
