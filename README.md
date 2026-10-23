# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

Welcome to your Remotion project!

## Commands

**Install Dependencies**

```console
npm i
```

**Start Preview**

```console
npm run dev
```

**Render video**

```console
npx remotion render
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Scenario pipeline

```console
uv sync
uv run python -m scenario.main path/to/scenario.docx --output-dir out/ --categories people,places,artifacts
uv run python -m scenario.render_cards out/scenario.json --output-dir out/videos
```

`--categories` picks the niches to extract (default `people`): `people` are
historical figures, `places` are battles, institutions and landmark sites,
`artifacts` are families, coats of arms, dynasties, books, laws and other
cultural monuments. Rules per category live in `scenario/categories.py`.
`.env` needs `GOOGLE_API_KEY` (see `.env.example`).

## Telegram bot

```console
uv run python -m bot
```

Polling, one command: `/start` shows category toggles (Люди, Битвы, Гербы),
`Далее` confirms, then send one or more `.docx` scenarios; the bot replies
with zip archives of the rendered clips (split under Telegram's 50 MB upload
cap). Files are processed one at a time in arrival order. Each file gets a
single status message that is edited in place: queue position, image search
and render progress, delivery, done. The queue survives a restart: every job
directory has a `job.json`, and an interrupted job resumes where it stopped,
including an archive delivery cut off halfway. Needs `BOT_TOKEN` in `.env`. Each job lives in `jobs/<chat>-<time>/`
with the uploaded docx, scenario output, clips, archives and `log.txt`.

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).
