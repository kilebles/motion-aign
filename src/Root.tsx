import "./index.css";
import { Composition } from "remotion";
import { StatCard } from "./StatCard";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="StatCard"
        component={StatCard}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          background: "background.jpg",
          character: "character.png",
          label: "Рост конверсии",
          value: 40,
        }}
      />
    </>
  );
};
