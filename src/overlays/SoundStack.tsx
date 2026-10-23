import React from "react";
import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { audioAssets } from "../library/assets";
import type { SoundSpec } from "../library/overlaySpec";

// Places each sound so its peak lands on `peakAtSeconds`. If the peak is
// wanted earlier than the file's own lead-in allows, the lead-in is trimmed
// instead of shifting the hit.
export const SoundStack: React.FC<{ sounds: SoundSpec[] }> = ({ sounds }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {sounds.map((spec, index) => {
        const asset = audioAssets[spec.asset as keyof typeof audioAssets];
        const offset = spec.peakAtSeconds - asset.peakAtSeconds;
        const from = Math.round(Math.max(0, offset) * fps);
        const trimBefore = Math.round(Math.max(0, -offset) * fps);
        const length = Math.max(1, Math.round(asset.durationInSeconds * fps) - trimBefore);
        return (
          <Sequence key={index} from={from} durationInFrames={length} layout="none">
            <Audio src={staticFile(asset.src)} trimBefore={trimBefore} volume={() => spec.volume} />
          </Sequence>
        );
      })}
    </>
  );
};
