"""Voice message handler with conversation mode (text responses only)."""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Router
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.processor import ClaudeProcessor
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage
from d_brain.services.transcription import DeepgramTranscriber

router = Router(name="voice")
logger = logging.getLogger(__name__)

QUESTION_TRIGGERS = (
    "?", "расскажи", "покажи", "найди", "что у", "как у",
    "сколько", "когда", "перенеси", "создай", "добавь",
    "сделай", "помоги", "можешь", "выведи", "список",
    "итого", "резюме", "суммируй", "объясни", "проверь",
    "напомни", "составь", "проанализируй",
)


def is_question_or_request(text: str) -> bool:
    lower = text.lower().strip()
    if "?" in text:
        return True
    for trigger in QUESTION_TRIGGERS:
        if lower.startswith(trigger) or f" {trigger}" in lower:
            return True
    return False


@router.message(lambda m: m.voice is not None)
async def handle_voice(message: Message, bot: Bot) -> None:
    if not message.voice or not message.from_user:
        return

    await message.chat.do(action="typing")
    settings = get_settings()
    storage = VaultStorage(settings.vault_path)
    transcriber = DeepgramTranscriber(settings.deepgram_api_key)

    try:
        file = await bot.get_file(message.voice.file_id)
        if not file.file_path:
            await message.answer("Не удалось скачать голосовое")
            return
        file_bytes = await bot.download_file(file.file_path)
        if not file_bytes:
            await message.answer("Не удалось скачать голосовое")
            return

        audio_bytes = file_bytes.read()
        transcript = await transcriber.transcribe(audio_bytes)

        if not transcript:
            await message.answer("Не удалось распознать речь")
            return

        timestamp = datetime.fromtimestamp(message.date.timestamp())
        user_id = message.from_user.id

        await message.answer(f"🎤 <i>{transcript}</i>")

        if is_question_or_request(transcript):
            status_msg = await message.answer("🤔 Думаю...")
            processor = ClaudeProcessor(settings.vault_path, settings.todoist_api_key)

            async def run_claude() -> dict:
                task = asyncio.create_task(
                    asyncio.to_thread(processor.execute_prompt, transcript, user_id)
                )
                elapsed = 0
                while not task.done():
                    await asyncio.sleep(30)
                    elapsed += 30
                    if not task.done():
                        try:
                            await status_msg.edit_text(f"🤔 Думаю... ({elapsed}с)")
                        except Exception:
                            pass
                return await task

            report = await run_claude()
            formatted = format_process_report(report)
            try:
                await status_msg.edit_text(formatted)
            except Exception:
                await status_msg.edit_text(formatted, parse_mode=None)

            storage.append_to_daily(f"❓ {transcript}", timestamp, "[voice-question]")

        else:
            storage.append_to_daily(transcript, timestamp, "[voice]")
            SessionStore(settings.vault_path).append(
                user_id, "voice", text=transcript,
                duration=message.voice.duration, msg_id=message.message_id
            )
            await message.answer("✓ Сохранено")

        logger.info("Voice processed: %d chars", len(transcript))

    except Exception as e:
        logger.exception("Error processing voice message")
        await message.answer(f"Ошибка: {e}")
