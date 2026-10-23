import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { imageAssets } from "../library/assets";
import { resolveBlend, type OverlaySpec, type OverlayTarget } from "../library/overlaySpec";
import { overlayRegistry } from "./registry";
import { VideoOverlay } from "./VideoOverlay";

const renderOverlay = (spec: OverlaySpec, seed: string, index: number) => {
  switch (spec.kind) {
    case "video":
      return <VideoOverlay key={index} spec={spec} />;
    case "image": {
      const asset = imageAssets[spec.asset as keyof typeof imageAssets];
      return (
        <AbsoluteFill key={index} style={{ mixBlendMode: resolveBlend(spec), opacity: spec.opacity }}>
          <Img
            src={staticFile(asset.src)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      );
    }
    case "procedural": {
      const Component = overlayRegistry[spec.name] ?? overlayRegistry.none;
      return (
        <AbsoluteFill key={index} style={{ opacity: spec.opacity }}>
          <Component seed={`${seed}-${spec.name}-${index}`} />
        </AbsoluteFill>
      );
    }
  }
};

// Draws every overlay in `overlays` whose target matches — the composition
// mounts one stack per z-slot (backdrop / card / screen) at the right depth.
export const OverlayStack: React.FC<{
  overlays: OverlaySpec[];
  target: OverlayTarget;
  seed: string;
}> = ({ overlays, target, seed }) => (
  <>
    {overlays.map((spec, index) =>
      spec.target === target ? renderOverlay(spec, seed, index) : null,
    )}
  </>
);
