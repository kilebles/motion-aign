import { z } from "zod";

const effectRef = z.union([z.string(), z.array(z.string())]);

const blockBase = {
  id: z.string(),
  at: z.number().default(0),
  effect: effectRef.default("fadeSlide"),
  effectParams: z.record(z.string(), z.any()).default({}),
  style: z.record(z.string(), z.any()).default({}),
};

export const imageBlockSchema = z.object({
  ...blockBase,
  type: z.literal("image"),
  src: z.string(),
});

export const textBlockSchema = z.object({
  ...blockBase,
  type: z.literal("text"),
  text: z.string(),
});

export const counterBlockSchema = z.object({
  ...blockBase,
  type: z.literal("counter"),
  value: z.number(),
  unit: z.string().default("%"),
  label: z.string().optional(),
});

export const blockSchema = z.discriminatedUnion("type", [
  imageBlockSchema,
  textBlockSchema,
  counterBlockSchema,
]);

export const sceneSchema = z.object({
  background: z.string().optional(),
  backgroundEffect: z.string().default("kenBurns"),
  backgroundEffectParams: z.record(z.string(), z.any()).default({}),
  blocks: z.array(blockSchema).default([]),
});

export type Block = z.infer<typeof blockSchema>;
export type SceneProps = z.infer<typeof sceneSchema>;
