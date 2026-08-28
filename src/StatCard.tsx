import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

export type StatCardProps = {
  background: string;
  character: string;
  label: string;
  value: number;
};

export const StatCard: React.FC<StatCardProps> = ({
  background,
  character,
  label,
  value,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgScale = interpolate(frame, [0, 150], [1, 1.12], {
    extrapolateRight: "clamp",
  });

  const charY = spring({ frame, fps, from: 200, to: 0, durationInFrames: 25 });

  const cardProgress = spring({
    frame: frame - 30,
    fps,
    from: 0,
    to: 1,
    durationInFrames: 20,
  });
  const cardX = interpolate(cardProgress, [0, 1], [-100, 0]);
  const cardOpacity = interpolate(cardProgress, [0, 1], [0, 1]);

  const countValue = Math.round(
    interpolate(frame - 40, [0, 30], [0, value], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );

  return (
    <AbsoluteFill>
      <Img
        src={staticFile(background)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${bgScale})`,
        }}
      />
      <Img
        src={staticFile(character)}
        style={{
          position: "absolute",
          bottom: 0,
          left: 40,
          height: "80%",
          transform: `translateY(${charY}px)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 100,
          right: 40,
          opacity: cardOpacity,
          transform: `translateX(${cardX}px)`,
          background: "#1a1a1acc",
          padding: "24px 40px",
          borderRadius: 16,
        }}
      >
        <div style={{ fontSize: 64, color: "white", fontWeight: 700 }}>
          {countValue}%
        </div>
        <div style={{ fontSize: 28, color: "#aaa" }}>{label}</div>
      </div>
    </AbsoluteFill>
  );
};
