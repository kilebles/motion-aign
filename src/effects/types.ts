export type EffectStyle = {
  opacity?: number;
  transform?: string;
  filter?: string;
};

export type EffectArgs<P = Record<string, unknown>> = {
  frame: number;
  fps: number;
  params: P;
};

export type EffectFn<P = Record<string, unknown>> = (
  args: EffectArgs<P>,
) => EffectStyle;
