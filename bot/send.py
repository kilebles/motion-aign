"""Send files to a chat as the bot — for manual top-ups after a job.

    uv run python -m bot.send <chat_id> file1.zip [file2.zip ...] [--caption "text"]
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import FSInputFile

from bot.config import BotSettings


async def send(chat_id: int, files: list[Path], caption: str | None) -> None:
    bot = Bot(BotSettings().token, session=AiohttpSession(timeout=600))
    try:
        if caption:
            await bot.send_message(chat_id, caption)
        for index, path in enumerate(files, start=1):
            part = f"Часть {index} из {len(files)}" if len(files) > 1 else None
            await bot.send_document(chat_id, FSInputFile(path), caption=part)
    finally:
        await bot.session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chat_id", type=int)
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--caption")
    args = parser.parse_args()
    asyncio.run(send(args.chat_id, args.files, args.caption))


if __name__ == "__main__":
    main()
