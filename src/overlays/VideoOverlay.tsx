import React from "react";
import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { videoAssets } from "../library/assets";
import { resolveBlend, type VideoOverlaySpec } from "../library/overlaySpec";

// Scale factor so a clip rotated by `deg` still covers a W×H frame.
const coverScaleForRotation = (deg: number, width: number, height: number) => {
  const rad = (Math.abs(deg) * Math.PI) / 180;
  const ratio = Math.max(width / height, height / width);
  return Math.abs(Math.cos(rad)) + Math.abs(Math.sin(rad)) * ratio;
};

const FadeBox: React.FC<{
  spec: VideoOverlaySpec;
  lengthInFrames: number;
  children: React.ReactNode;
}> = ({ spec, lengthInFrames, children }) => {
  // Frame is relative to the enclosing <Sequence>.
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeIn = Math.round(spec.fadeInSeconds * fps);
  const fadeOut = Math.round(spec.fadeOutSeconds * fps);

  const edge =
    Math.min(
      fadeIn > 0 ? interpolate(frame, [0, fadeIn], [0, 1]) : 1,
      fadeOut > 0 ? interpolate(frame, [lengthInFrames - fadeOut, lengthInFrames], [1, 0]) : 1,
    );
  const opacity = spec.opacity * Math.max(0, Math.min(1, edge));

  return (
    <AbsoluteFill style={{ mixBlendMode: resolveBlend(spec), opacity }}>{children}</AbsoluteFill>
  );
};

// Renders one stock video overlay from its spec: placed at `startAtSeconds`,
// kept for `durationInSeconds` (or to the end), looped or cut at the clip's
// own length, blended per the asset manifest.
export const VideoOverlay: React.FC<{ spec: VideoOverlaySpec }> = ({ spec }) => {
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const asset = videoAssets[spec.asset as keyof typeof videoAssets];

  const nativeFrames = Math.max(1, Math.floor((asset.durationInSeconds * fps) / spec.speed));
  const startAt = Math.round(spec.startAtSeconds * fps);
  const requested = spec.durationInSeconds
    ? Math.round(spec.durationInSeconds * fps)
    : durationInFrames - startAt;
  const lengthInFrames = Math.max(1, spec.loop ? requested : Math.min(requested, nativeFrames));

  const scale = spec.fit === "cover" ? coverScaleForRotation(spec.rotate, width, height) : 1;

  const video = (
    <OffthreadVideo
      src={staticFile(asset.src)}
      playbackRate={spec.speed}
      muted={!(spec.sound && asset.hasAudio)}
      style={{
        width: "100%",
        height: "100%",
        objectFit: spec.fit,
        transform: spec.rotate ? `rotate(${spec.rotate}deg) scale(${scale})` : undefined,
        filter: spec.invert ? "invert(1)" : undefined,
      }}
    />
  );

  return (
    <Sequence from={startAt} durationInFrames={lengthInFrames} layout="none">
      <FadeBox spec={spec} lengthInFrames={lengthInFrames}>
        {spec.loop ? <Loop durationInFrames={nativeFrames}>{video}</Loop> : video}
      </FadeBox>
    </Sequence>
  );
};
