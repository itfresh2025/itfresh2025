"""Document handler — .docx, .doc, .xlsx, .xls, .txt, .pdf, .md"""

import io
import logging
from datetime import datetime

from aiogram import Bot, Router
from aiogram.types import Message

from d_brain.config import get_settings
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage

router = Router(name="document")
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".pdf"}


def extract_text_from_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_xlsx(data: bytes) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for sheet in wb.worksheets:
        lines.append(f"=== Лист: {sheet.title} ===")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(
        p.extract_text().strip() for p in reader.pages if p.extract_text()
    )


def extract_text_from_txt(data: bytes) -> str:
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


@router.message(lambda m: m.document is not None)
async def handle_document(message: Message, bot: Bot) -> None:
    if not message.document or not message.from_user:
        return

    doc = message.document
    filename = doc.file_name or "document"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in SUPPORTED_EXTENSIONS:
        await message.answer(
            f"📎 Формат <b>{ext}</b> не поддерживается.\n"
            f"Поддерживаются: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        return

    await message.chat.do(action="typing")
    settings = get_settings()
    storage = VaultStorage(settings.vault_path)

    try:
        file = await bot.get_file(doc.file_id)
        if not file.file_path:
            await message.answer("Не удалось скачать файл")
            return
        file_bytes = await bot.download_file(file.file_path)
        if not file_bytes:
            await message.answer("Не удалось скачать файл")
            return

        data = file_bytes.read()

        if ext in (".docx", ".doc"):
            text = extract_text_from_docx(data)
        elif ext in (".xlsx", ".xls"):
            text = extract_text_from_xlsx(data)
        elif ext == ".pdf":
            text = extract_text_from_pdf(data)
        else:
            text = extract_text_from_txt(data)

        if not text.strip():
            await message.answer("📄 Файл пустой или не удалось извлечь текст")
            return

        timestamp = datetime.fromtimestamp(message.date.timestamp())
        caption = f"📄 **{filename}**\n\n{text}"
        if message.caption:
            caption = f"📄 **{filename}** ({message.caption})\n\n{text}"

        storage.append_to_daily(caption, timestamp, f"[document: {filename}]")
        SessionStore(settings.vault_path).append(
            message.from_user.id, "document",
            filename=filename, chars=len(text), msg_id=message.message_id,
        )

        preview = text[:200] + "..." if len(text) > 200 else text
        await message.answer(
            f"📄 <b>{filename}</b>\n\n{preview}\n\n✓ Сохранено ({len(text)} символов)"
        )
        logger.info("Document saved: %s (%d chars)", filename, len(text))

    except Exception as e:
        logger.exception("Error processing document")
        await message.answer(f"Ошибка: {e}")
