import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { Counter } from "./components/Counter";
import { Layer } from "./components/Layer";
import { pickEffect } from "./effects/registry";
import type { Block, SceneProps } from "./schema";

const renderContent = (block: Block) => {
  switch (block.type) {
    case "image":
      return (
        <Img
          src={staticFile(block.src)}
          style={{ width: "100%", height: "100%" }}
        />
      );
    case "text":
      return (
        <div style={{ color: "white", fontSize: 32 }}>{block.text}</div>
      );
    case "counter":
      return (
        <Counter
          value={block.value}
          unit={block.unit}
          label={block.label}
        />
      );
  }
};

export const Scene: React.FC<SceneProps> = ({
  background,
  backgroundEffect,
  backgroundEffectParams,
  blocks,
}) => {
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {background && (
        <Layer
          effect={backgroundEffect}
          effectParams={backgroundEffectParams}
          style={{ inset: 0 }}
        >
          <Img
            src={staticFile(background)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Layer>
      )}
      {blocks.map((block) => {
        const effectName = pickEffect(block.effect, block.id);
        return (
          <Layer
            key={block.id}
            effect={effectName}
            effectParams={{ delay: block.at, ...block.effectParams }}
            style={block.style as React.CSSProperties}
          >
            {renderContent(block)}
          </Layer>
        );
      })}
    </AbsoluteFill>
  );
};
