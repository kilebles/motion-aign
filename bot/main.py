from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import BotSettings
from bot.jobs import (
    JOBS_DIR,
    StageError,
    load_active_jobs,
    make_archives,
    read_progress,
    run_pipeline,
    save_job,
)
from scenario.categories import CATEGORIES, CATEGORY_IDS

logger = logging.getLogger(__name__)

# One status message per job, edited in place — never a new message per
# tick — so a long job doesn't flood the chat or trip Telegram's flood limits.
_STATUS_INTERVAL_SECONDS = 60
# Renders are CPU-bound and the pipeline copies images into a shared public/
# folder, so jobs run strictly one at a time, in the order they arrived.
_MAX_QUEUED = 10

_CALLBACK_PREFIX = "cat:"
_CALLBACK_DONE = "cat:done"


class Form(StatesGroup):
    choosing = State()
    waiting_docx = State()


@dataclass
class Job:
    job_dir: Path
    record: dict
    """Extra status lines kept across edits (e.g. the "Найдено: ..." line)."""
    lines: list[str] = field(default_factory=list)

    @property
    def chat_id(self) -> int:
        return self.record["chat_id"]

    @property
    def docx_path(self) -> Path:
        return self.job_dir / self.record["docx"]

    def set_status(self, status: str, **extra) -> None:
        self.record.update(status=status, **extra)
        save_job(self.job_dir, self.record)


dp = Dispatcher()
_queue: list[Job] = []
_current: Job | None = None
_wakeup = asyncio.Event()


# --- status message ---------------------------------------------------------


def _title(job: Job) -> str:
    name = Path(job.record["docx"]).stem
    return name if len(name) <= 60 else name[:57] + "..."


async def _set_status(bot: Bot, job: Job, text: str) -> None:
    """Edits the job's single status message: file name on top, then the
    kept lines, then the current state."""
    body = "\n".join([_title(job), *job.lines, text])
    if body == job.record.get("status_text"):
        return
    try:
        await bot.edit_message_text(
            body, chat_id=job.chat_id, message_id=job.record["status_message_id"]
        )
        job.record["status_text"] = body
    except Exception:
        logger.debug("Status edit failed for %s", job.job_dir.name, exc_info=True)


def _queue_text(ahead: int) -> str:
    return f"В очереди, перед вами: {ahead}."


async def _refresh_positions(bot: Bot) -> None:
    running = 1 if _current else 0
    for index, job in enumerate(_queue):
        await _set_status(bot, job, _queue_text(index + running))


async def _report_progress(bot: Bot, job: Job) -> None:
    while True:
        await asyncio.sleep(_STATUS_INTERVAL_SECONDS)
        text = read_progress(job.job_dir / "log.txt")
        if text:
            await _set_status(bot, job, text)


# --- worker -----------------------------------------------------------------


async def _process(bot: Bot, job: Job) -> None:
    categories = job.record["categories"]
    reply_to = job.record.get("docx_message_id")
    reporter: asyncio.Task | None = None
    try:
        if job.record["status"] != "sending":
            job.set_status("running")
            await _set_status(bot, job, "Разбираю сценарий и ищу изображения.")
            reporter = asyncio.create_task(_report_progress(bot, job))

            async def on_stage(subjects: int, with_images: int, per_category: dict[str, int]) -> None:
                counts = ", ".join(
                    f"{CATEGORIES[cid].label}: {per_category.get(cid, 0)}" for cid in categories
                )
                job.lines = [f"Найдено: {subjects} ({counts}), с изображениями: {with_images}."]
                await _set_status(bot, job, f"Рендер: 0 из {with_images}.")

            result = await run_pipeline(job.docx_path, categories, on_stage=on_stage)
            reporter.cancel()
            archives = await asyncio.to_thread(
                make_archives, result, job.job_dir / "archives", job.docx_path.stem
            )
            job.set_status(
                "sending", clips=len(result.clips), archives=[a.name for a in archives], sent=0
            )

        # Delivery. `sent` is saved after every archive, so a bot restarted
        # mid-delivery continues with the next part instead of starting over.
        names: list[str] = job.record["archives"]
        total = len(names)
        for index in range(job.record.get("sent", 0), total):
            await _set_status(bot, job, f"Отправка: {index + 1} из {total}.")
            caption = f"Часть {index + 1} из {total}" if total > 1 else None
            await bot.send_document(
                job.chat_id,
                FSInputFile(job.job_dir / "archives" / names[index]),
                caption=caption,
                reply_to_message_id=reply_to,
                allow_sending_without_reply=True,
            )
            job.set_status("sending", sent=index + 1)

        job.set_status("done")
        await _set_status(bot, job, f"Готово: {job.record.get('clips', 0)} видео, архивов: {total}.")
    except StageError as error:
        logger.exception("Job failed in %s", job.job_dir)
        job.set_status("failed", error=error.stage)
        await _set_status(bot, job, f"Ошибка на этапе {error.stage}. Лог: {error.log_path.name}")
    except Exception:
        logger.exception("Job failed in %s", job.job_dir)
        job.set_status("failed", error="unexpected")
        await _set_status(bot, job, "Ошибка обработки.")
    finally:
        if reporter:
            reporter.cancel()


async def _worker(bot: Bot) -> None:
    global _current
    while True:
        while not _queue:
            _wakeup.clear()
            await _wakeup.wait()
        _current = _queue.pop(0)
        # Everyone still waiting moves up one; the next refresh happens when
        # the following job is taken, so nobody ever sees "перед вами: 0".
        await _refresh_positions(bot)
        try:
            await _process(bot, _current)
        finally:
            _current = None


@dp.startup()
async def _on_startup(bot: Bot) -> None:
    # Pick the queue back up: whatever was queued, running or being delivered
    # when the bot went down, oldest first.
    for job_dir, record in load_active_jobs():
        _queue.append(Job(job_dir, record))
    if _queue:
        logger.info("Resuming %d unfinished job(s)", len(_queue))
        _wakeup.set()
    asyncio.create_task(_worker(bot))


# --- handlers ---------------------------------------------------------------


def _keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if cid in selected else ''}{CATEGORIES[cid].label}",
                callback_data=f"{_CALLBACK_PREFIX}{cid}",
            )
        ]
        for cid in CATEGORY_IDS
    ]
    rows.append([InlineKeyboardButton(text="Далее", callback_data=_CALLBACK_DONE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    selected = list(CATEGORY_IDS)
    await state.set_state(Form.choosing)
    await state.update_data(categories=selected)
    await message.answer("Что искать в сценарии:", reply_markup=_keyboard(selected))


@dp.callback_query(StateFilter(Form.choosing), F.data.startswith(_CALLBACK_PREFIX))
async def choose(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = list(data.get("categories", CATEGORY_IDS))

    if callback.data == _CALLBACK_DONE:
        if not selected:
            await callback.answer("Выберите хотя бы одну категорию.")
            return
        await state.set_state(Form.waiting_docx)
        labels = ", ".join(CATEGORIES[cid].label for cid in CATEGORY_IDS if cid in selected)
        await callback.message.edit_text(f"Категории: {labels}.")
        await callback.message.answer("Отправьте сценарий в формате .docx. Можно несколько, встанут в очередь.")
        await callback.answer()
        return

    cid = callback.data.removeprefix(_CALLBACK_PREFIX)
    if cid not in CATEGORIES:
        await callback.answer()
        return
    if cid in selected:
        selected.remove(cid)
    else:
        selected.append(cid)
    await state.update_data(categories=selected)
    await callback.message.edit_reply_markup(reply_markup=_keyboard(selected))
    await callback.answer()


def _new_job_dir(chat_id: int) -> Path:
    base = f"{chat_id}-{datetime.now():%Y%m%d-%H%M%S}"
    job_dir = JOBS_DIR / base
    suffix = 1
    while job_dir.exists():  # two files in the same second
        suffix += 1
        job_dir = JOBS_DIR / f"{base}-{suffix}"
    job_dir.mkdir(parents=True)
    return job_dir


@dp.message(StateFilter(Form.waiting_docx, Form.choosing), F.document)
async def handle_docx(message: Message, state: FSMContext, bot: Bot) -> None:
    document = message.document
    if not document.file_name or not document.file_name.lower().endswith(".docx"):
        await message.answer("Нужен файл .docx.")
        return

    data = await state.get_data()
    categories = [cid for cid in CATEGORY_IDS if cid in data.get("categories", CATEGORY_IDS)]
    if not categories:
        await message.answer("Выберите хотя бы одну категорию.")
        return
    if len(_queue) >= _MAX_QUEUED:
        await message.answer("Очередь заполнена, попробуйте позже.")
        return

    await state.set_state(Form.waiting_docx)
    job_dir = _new_job_dir(message.chat.id)
    docx_name = Path(document.file_name).name
    await bot.download(document, destination=job_dir / docx_name)

    ahead = len(_queue) + (1 if _current else 0)
    job = Job(
        job_dir,
        {
            "chat_id": message.chat.id,
            "docx": docx_name,
            "docx_message_id": message.message_id,
            "categories": categories,
            "created": time.time(),
            "status": "queued",
        },
    )
    first_line = _queue_text(ahead) if ahead else "Файл принят."
    text = "\n".join([_title(job), first_line])
    status = await message.reply(text)
    job.record.update(status_message_id=status.message_id, status_text=text)
    save_job(job_dir, job.record)

    _queue.append(job)
    _wakeup.set()


@dp.message(StateFilter(Form.waiting_docx, Form.choosing))
async def not_a_file(message: Message) -> None:
    await message.answer("Нужен файл .docx.")


@dp.message()
async def no_state(message: Message) -> None:
    await message.answer("Отправьте /start.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = BotSettings()
    # Archives are up to 49 MB; the default 60s request timeout is too short
    # for an upload that size on a slow link.
    bot = Bot(settings.token, session=AiohttpSession(timeout=600))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
