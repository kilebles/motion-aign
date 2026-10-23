import "./index.css";
import { Composition, Folder, type CalculateMetadataFunction } from "remotion";
import { PersonalityCard, personalityCardSchema, type PersonalityCardProps } from "./PersonalityCard";
import { Scene } from "./Scene";
import { themeIds } from "./library/themes";
import { sceneSchema, type SceneProps } from "./schema";

// `schema` on <Composition> only drives the Studio props UI — it does not
// validate `--props` on `remotion render` by itself. Parsing here is what
// actually rejects a bad scenario (and fills in the schema's z.default()s),
// since calculateMetadata runs on every render, CLI included.
const calculateMetadata: CalculateMetadataFunction<SceneProps> = ({ props }) => {
  return { props: sceneSchema.parse(props) };
};

const calculatePersonalityCardMetadata: CalculateMetadataFunction<PersonalityCardProps> = ({
  props,
}) => {
  return { props: personalityCardSchema.parse(props) };
};

const personalityCardDefaults: PersonalityCardProps = {
  image: "personalities/9.1.jpg",
  name: "Edward the Confessor",
  years: "1003 — 1066",
  extraOverlays: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Scene"
        component={Scene}
        schema={sceneSchema}
        calculateMetadata={calculateMetadata}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          background: "background.png",
          backgroundEffect: "kenBurns",
          backgroundEffectParams: { to: 1.12, durationInFrames: 150 },
          blocks: [
            {
              id: "character",
              type: "image",
              at: 0,
              src: "character.png",
              effect: "fadeSlide",
              effectParams: { from: "bottom", distance: 200, durationInFrames: 25 },
              style: { bottom: 0, left: 40, height: "80%", width: "auto" },
            },
            {
              id: "stat",
              type: "counter",
              at: 30,
              value: 40,
              unit: "%",
              label: "Рост конверсии",
              effect: "fadeSlide",
              effectParams: { from: "left", distance: 100, durationInFrames: 20 },
              style: { bottom: 100, right: 40 },
            },
          ],
        }}
      />
      {/* The production composition: theme / choreography / accent are
          picked per seed unless pinned via props. */}
      <Composition
        id="PersonalityCard"
        component={PersonalityCard}
        schema={personalityCardSchema}
        calculateMetadata={calculatePersonalityCardMetadata}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={personalityCardDefaults}
      />
      {/* One pinned composition per theme, for eyeballing each look in Studio. */}
      <Folder name="Themes">
        {themeIds.map((themeId) => (
          <Composition
            key={themeId}
            id={`PersonalityCard-${themeId}`}
            component={PersonalityCard}
            schema={personalityCardSchema}
            calculateMetadata={calculatePersonalityCardMetadata}
            durationInFrames={300}
            fps={30}
            width={1920}
            height={1080}
            defaultProps={{ ...personalityCardDefaults, theme: themeId }}
          />
        ))}
      </Folder>
    </>
  );
};
