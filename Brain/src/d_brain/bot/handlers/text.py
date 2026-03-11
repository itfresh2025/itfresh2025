"""Text message handler with smart question detection."""

import asyncio
import logging
from datetime import datetime

from aiogram import Router
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.processor import ClaudeProcessor
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage

router = Router(name="text")
logger = logging.getLogger(__name__)

# Слова-триггеры вопроса/запроса
QUESTION_TRIGGERS = (
    "?",
)

COMMAND_TRIGGERS = (
    "покажи", "расскажи", "найди", "что у", "как у",
    "сколько", "когда", "перенеси", "создай", "добавь",
    "удали", "обнови", "напомни", "составь", "проанализируй",
    "сделай", "помоги", "можешь", "открой", "закрой",
    "покажи", "выведи", "список", "итого", "резюме",
    "суммируй", "объясни", "сравни", "проверь",
)


def is_question_or_request(text: str) -> bool:
    """Detect if message is a question or command, not a note."""
    lower = text.lower().strip()
    if "?" in text:
        return True
    for trigger in COMMAND_TRIGGERS:
        if lower.startswith(trigger) or f" {trigger}" in lower:
            return True
    return False


@router.message(lambda m: m.text is not None and not m.text.startswith("/"))
async def handle_text(message: Message) -> None:
    """Handle text messages — save notes or answer questions via Claude."""
    if not message.text or not message.from_user:
        return

    settings = get_settings()
    storage = VaultStorage(settings.vault_path)
    timestamp = datetime.fromtimestamp(message.date.timestamp())
    user_id = message.from_user.id

    if is_question_or_request(message.text):
        # Route to Claude for answer
        status_msg = await message.answer("🤔 Думаю...")
        processor = ClaudeProcessor(settings.vault_path, settings.todoist_api_key)

        async def run_with_progress() -> dict:
            task = asyncio.create_task(
                asyncio.to_thread(processor.execute_prompt, message.text, user_id)
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

        report = await run_with_progress()
        formatted = format_process_report(report)
        try:
            await status_msg.edit_text(formatted)
        except Exception:
            await status_msg.edit_text(formatted, parse_mode=None)

        # Also save question+answer to daily
        storage.append_to_daily(
            f"❓ {message.text}", timestamp, "[question]"
        )
        logger.info("Question answered: %d chars", len(message.text))

    else:
        # Save as note
        storage.append_to_daily(message.text, timestamp, "[text]")
        session = SessionStore(settings.vault_path)
        session.append(user_id, "text", text=message.text, msg_id=message.message_id)
        await message.answer("✓ Сохранено")
        logger.info("Text message saved: %d chars", len(message.text))
