"""Telegram Bot for AdminDB — python-telegram-bot 21.x"""
import asyncio
import logging
import platform
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Will be set after Application is created
_application = None
_db_factory = None
_notify_chat_id: Optional[str] = None

PRIORITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

STATUS_EMOJI = {
    "new": "🆕",
    "open": "📭",
    "assigned": "👤",
    "in_progress": "🔄",
    "pending": "⏸",
    "resolved": "✅",
    "closed": "🔒",
}

SLA_MINUTES = {
    "critical": 60,
    "high": 240,
    "medium": 1440,
    "low": 4320,
}

# ConversationHandler states
(
    NEW_CLIENT,
    NEW_TITLE,
    NEW_DESC,
    NEW_PRIORITY,
    RESOLVE_COMMENT,
) = range(5)


# ─── DB helpers ───────────────────────────────────────────────────────────────

def _get_db():
    db = _db_factory()
    try:
        return db
    except Exception:
        db.close()
        raise


def _format_ago(dt: datetime) -> str:
    if not dt:
        return "неизвестно"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    mins = int(delta.total_seconds() // 60)
    if mins < 60:
        return f"{mins} мин назад"
    hours = mins // 60
    if hours < 24:
        return f"{hours}ч назад"
    return f"{hours // 24}д назад"


def _sla_remaining_minutes(ticket) -> Optional[int]:
    """Returns minutes remaining (negative = overdue). None if N/A."""
    from ..models.tickets import TicketStatus
    if ticket.status.value in ("resolved", "closed"):
        return None
    limit = SLA_MINUTES.get(ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority)
    if limit is None:
        return None
    now = datetime.now(timezone.utc)
    created = ticket.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = int((now - created).total_seconds() // 60)
    return limit - elapsed


def _sla_overdue(ticket) -> bool:
    rem = _sla_remaining_minutes(ticket)
    return rem is not None and rem < 0


# ─── Commands ─────────────────────────────────────────────────────────────────

async def cmd_start(update, context):
    chat_id = update.effective_chat.id
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📊 Статус"), KeyboardButton("📋 Тикеты")],
            [KeyboardButton("⚠️ Просроченные"), KeyboardButton("📈 Статистика")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    await update.message.reply_text(
        f"👋 Привет! Я *AdminDB Bot* от ITfresh.\n"
        f"Управляю тикетами и слежу за серверами.\n\n"
        f"ℹ️ Ваш chat\\_id: `{chat_id}`\n"
        f"_(для уведомлений: добавьте в .env `TELEGRAM_NOTIFY_CHAT_ID={chat_id}`)_\n\n"
        f"/help — список команд",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def cmd_help(update, context):
    await update.message.reply_text(
        "📖 *Команды бота:*\n\n"
        "/status — мониторинг серверов\n"
        "/tickets — открытые тикеты\n"
        "/ticket <id> — детали тикета\n"
        "/resolve <id> — закрыть тикет\n"
        "/overdue — просроченные тикеты\n"
        "/mystats — статистика по тикетам\n"
        "/new — создать тикет\n"
        "/ping <ip> — проверить IP прямо сейчас",
        parse_mode="Markdown"
    )


async def cmd_status(update, context):
    from ..core.ping_worker import get_all_statuses
    cache = get_all_statuses()

    if not cache:
        await update.message.reply_text("⏳ Пинг-воркер ещё не запустился. Подождите 60 секунд.")
        return

    online = [v for v in cache.values() if v.get("online")]
    offline = [v for v in cache.values() if not v.get("online")]

    text = f"🖥 *Мониторинг серверов*\n✅ Онлайн: {len(online)}\n❌ Оффлайн: {len(offline)}\n"

    if offline:
        text += "\n*Оффлайн клиенты:*\n"
        for v in offline[:20]:
            text += f"• {v.get('client_name', '?')} ({v.get('ip', '?')})\n"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status"),
    ]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def cmd_tickets(update, context):
    from ..models.tickets import Ticket, TicketStatus
    db = _db_factory()
    try:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.status.in_([
                TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress
            ]))
            .order_by(Ticket.priority.desc(), Ticket.created_at.asc())
            .limit(10)
            .all()
        )

        if not tickets:
            await update.message.reply_text("✅ Нет открытых тикетов!")
            return

        text = f"📋 *Открытые тикеты ({len(tickets)}):*\n\n"
        for t in tickets:
            emoji = PRIORITY_EMOJI.get(t.priority.value, "⚪")
            overdue = " ⚠️ ПРОСРОЧЕН" if _sla_overdue(t) else ""
            client_name = t.client.company if t.client else "Общий"
            text += (
                f"#{t.id} {emoji} {t.priority.value.upper()} — {client_name}\n"
                f"{t.title}\n"
                f"Создан: {_format_ago(t.created_at)}{overdue}\n\n"
            )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for t in tickets[:5]:
            keyboard.append([
                InlineKeyboardButton(f"#{t.id} Взять", callback_data=f"take_{t.id}"),
                InlineKeyboardButton(f"#{t.id} Закрыть", callback_data=f"close_{t.id}"),
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    finally:
        db.close()


async def cmd_overdue(update, context):
    """Show overdue tickets sorted by urgency."""
    from ..models.tickets import Ticket, TicketStatus
    db = _db_factory()
    try:
        active_statuses = [TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress]
        tickets = (
            db.query(Ticket)
            .filter(Ticket.status.in_(active_statuses))
            .order_by(Ticket.priority.desc(), Ticket.created_at.asc())
            .all()
        )
        overdue = [t for t in tickets if _sla_overdue(t)]

        if not overdue:
            await update.message.reply_text("✅ Нет просроченных тикетов!")
            return

        text = f"⚠️ *Просроченные тикеты ({len(overdue)}):*\n\n"
        for t in overdue[:15]:
            rem = _sla_remaining_minutes(t)
            overdue_mins = abs(rem) if rem is not None else 0
            if overdue_mins >= 60:
                overdue_str = f"{overdue_mins // 60}ч {overdue_mins % 60}м"
            else:
                overdue_str = f"{overdue_mins}м"
            emoji = PRIORITY_EMOJI.get(t.priority.value, "⚪")
            client_name = t.client.company if t.client else "Общий"
            text += (
                f"#{t.id} {emoji} — {client_name}\n"
                f"{t.title}\n"
                f"Просрочен на: {overdue_str}\n\n"
            )

        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def cmd_mystats(update, context):
    """Show ticket statistics."""
    from ..models.tickets import Ticket, TicketStatus, TicketPriority
    db = _db_factory()
    try:
        total = db.query(Ticket).count()
        open_count = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress])
        ).count()
        resolved_today = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed]),
            Ticket.resolved_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        ).count()
        critical_open = db.query(Ticket).filter(
            Ticket.priority == TicketPriority.critical,
            Ticket.status.in_([TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress]),
        ).count()

        active_tickets = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress])
        ).all()
        overdue_count = sum(1 for t in active_tickets if _sla_overdue(t))

        text = (
            f"📈 *Статистика тикетов*\n\n"
            f"Всего тикетов: *{total}*\n"
            f"Открытых: *{open_count}*\n"
            f"🔴 Critical открытых: *{critical_open}*\n"
            f"⚠️ Просрочено SLA: *{overdue_count}*\n"
            f"✅ Решено сегодня: *{resolved_today}*\n"
        )

        from ..core.ping_worker import get_all_statuses
        cache = get_all_statuses()
        if cache:
            online = sum(1 for v in cache.values() if v.get("online"))
            offline = len(cache) - online
            text += f"\n🖥 Серверов онлайн: *{online}* / оффлайн: *{offline}*"

        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def cmd_ticket(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /ticket <id>")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Неверный ID тикета")
        return

    from ..models.tickets import Ticket
    db = _db_factory()
    try:
        t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not t:
            await update.message.reply_text(f"Тикет #{ticket_id} не найден")
            return

        emoji = PRIORITY_EMOJI.get(t.priority.value, "⚪")
        status_e = STATUS_EMOJI.get(t.status.value, "📋")
        client_name = t.client.company if t.client else "Без клиента"
        assigned = t.assigned_to.username if t.assigned_to else "Никому"
        overdue = " ⚠️ ПРОСРОЧЕН" if _sla_overdue(t) else ""
        rem = _sla_remaining_minutes(t)
        if rem is not None:
            if rem < 0:
                sla_str = f"Просрочен на {abs(rem)} мин"
            else:
                sla_str = f"Осталось {rem} мин"
        else:
            sla_str = "N/A"

        text = (
            f"*Тикет #{t.id}*{overdue}\n"
            f"Клиент: {client_name}\n"
            f"Статус: {status_e} {t.status.value}\n"
            f"Приоритет: {emoji} {t.priority.value.upper()}\n"
            f"Назначен: {assigned}\n"
            f"SLA: {sla_str}\n"
            f"Создан: {_format_ago(t.created_at)}\n\n"
            f"*{t.title}*\n"
            f"{t.description or ''}"
        )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import json as _json
        _shared = _json.loads(getattr(t, 'shared_fields', None) or '[]')
        keyboard = [
            [
                InlineKeyboardButton("🔄 В работу", callback_data=f"inprog_{t.id}"),
                InlineKeyboardButton("✅ Решён", callback_data=f"resolve_{t.id}"),
            ],
            [
                InlineKeyboardButton("🔒 Закрыть", callback_data=f"close_{t.id}"),
            ],
        ]
        if _shared:
            keyboard.append([
                InlineKeyboardButton("🔑 Данные клиента", callback_data=f"cdata_{t.id}"),
            ])
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    finally:
        db.close()


async def cmd_resolve(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /resolve <id>")
        return
    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Неверный ID")
        return

    context.user_data["resolve_ticket_id"] = ticket_id
    await update.message.reply_text(
        f"Введите комментарий к решению тикета #{ticket_id} (или /skip чтобы пропустить):"
    )
    return RESOLVE_COMMENT


async def resolve_comment_handler(update, context):
    ticket_id = context.user_data.get("resolve_ticket_id")
    comment_text = update.message.text

    from ..models.tickets import Ticket, TicketStatus
    from ..models.ticket_comments import TicketComment
    db = _db_factory()
    try:
        t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not t:
            await update.message.reply_text(f"Тикет #{ticket_id} не найден")
            return -1

        t.status = TicketStatus.resolved
        if not t.resolved_at:
            t.resolved_at = datetime.now(timezone.utc)

        if comment_text and comment_text != "/skip":
            from ..models.user import User
            admin = db.query(User).filter(User.username == "admin").first()
            if admin:
                comment = TicketComment(
                    ticket_id=ticket_id,
                    author_id=admin.id,
                    text=f"[Telegram] {comment_text}",
                )
                db.add(comment)

        db.commit()
        await update.message.reply_text(f"✅ Тикет #{ticket_id} закрыт как решённый!")
    finally:
        db.close()

    return -1  # ConversationHandler.END


# ─── /new conversation ─────────────────────────────────────────────────────────

async def new_start(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "Название клиента или IP (или напишите 'общий' если без клиента):"
    )
    return NEW_CLIENT


async def new_client(update, context):
    text = update.message.text.strip()
    if text.lower() in ("общий", "общее", "general", "-"):
        context.user_data["client_id"] = None
        context.user_data["client_name"] = "Общий"
    else:
        from ..models.client import Client
        db = _db_factory()
        try:
            client = db.query(Client).filter(
                (Client.company.ilike(f"%{text}%")) | (Client.ip_address == text)
            ).first()
            if client:
                context.user_data["client_id"] = client.id
                context.user_data["client_name"] = client.company
            else:
                context.user_data["client_id"] = None
                context.user_data["client_name"] = text
        finally:
            db.close()

    await update.message.reply_text("Заголовок проблемы:")
    return NEW_TITLE


async def new_title(update, context):
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("Описание (или /skip чтобы пропустить):")
    return NEW_DESC


async def new_desc(update, context):
    text = update.message.text.strip()
    context.user_data["description"] = None if text == "/skip" else text

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("🔴 Critical", callback_data="prio_critical"),
            InlineKeyboardButton("🟠 High", callback_data="prio_high"),
        ],
        [
            InlineKeyboardButton("🟡 Medium", callback_data="prio_medium"),
            InlineKeyboardButton("🟢 Low", callback_data="prio_low"),
        ],
    ]
    await update.message.reply_text(
        "Приоритет?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return NEW_PRIORITY


async def new_priority_callback(update, context):
    query = update.callback_query
    await query.answer()

    priority = query.data.replace("prio_", "")
    context.user_data["priority"] = priority

    from ..models.tickets import Ticket, TicketPriority, TicketSource, TicketStatus
    from ..models.user import User
    db = _db_factory()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            await query.edit_message_text("Ошибка: не найден пользователь admin")
            return -1

        ticket = Ticket(
            client_id=context.user_data.get("client_id"),
            title=context.user_data["title"],
            description=context.user_data.get("description"),
            priority=TicketPriority(priority),
            status=TicketStatus.new,
            created_by_id=admin.id,
            source=TicketSource.telegram,
            telegram_chat_id=str(query.message.chat_id),
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        await query.edit_message_text(
            f"✅ Тикет #{ticket.id} создан!\n"
            f"Клиент: {context.user_data.get('client_name', 'Без клиента')}\n"
            f"{PRIORITY_EMOJI.get(priority, '')} {priority.upper()}: {ticket.title}"
        )

        await _send_new_ticket_notification(ticket)
    finally:
        db.close()

    return -1  # END


# ─── Voice message handler ───────────────────────────────────────────────────

async def voice_handler(update, context):
    """Handle incoming voice messages — transcribe and create ticket."""
    msg = await update.message.reply_text("🎤 Распознаю речь...")
    try:
        import os
        import tempfile
        # Download voice file (OGG OPUS)
        voice = update.message.voice
        tg_file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_ogg:
            ogg_path = tmp_ogg.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name
        try:
            await tg_file.download_to_drive(ogg_path)
            # Convert OGG → WAV
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_ogg(ogg_path)
                audio.export(wav_path, format="wav")
            except Exception as e:
                await msg.edit_text(f"❌ Ошибка конвертации аудио: {e}\nНапишите тикет текстом: /new")
                return
            # Transcribe with SpeechRecognition
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                transcript = recognizer.recognize_google(audio_data, language="ru-RU")
            except Exception as e:
                await msg.edit_text(f"❌ Ошибка распознавания речи: {e}\nНапишите тикет текстом: /new")
                return
        finally:
            try:
                os.unlink(ogg_path)
                os.unlink(wav_path)
            except Exception:
                pass

        if not transcript.strip():
            await msg.edit_text("🎤 Не удалось распознать речь. Пожалуйста, напишите текстом: /new")
            return

        # Create ticket from transcript
        from ..models.tickets import Ticket, TicketPriority, TicketSource, TicketStatus
        from ..models.user import User
        db = _db_factory()
        try:
            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                await msg.edit_text("Ошибка: не найден пользователь admin")
                return
            ticket = Ticket(
                title=f"[Голос] {transcript[:100]}",
                description=f"🎤 Голосовое сообщение:\n\n{transcript}",
                priority=TicketPriority.medium,
                status=TicketStatus.new,
                created_by_id=admin.id,
                source=TicketSource.telegram,
                telegram_chat_id=str(update.effective_chat.id),
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            await msg.edit_text(
                f"✅ *Тикет #{ticket.id} создан по голосовому сообщению*\n\n"
                f"📝 {transcript[:200]}\n\n"
                f"Используйте /ticket {ticket.id} для управления",
                parse_mode="Markdown",
            )
            await _send_new_ticket_notification(ticket)
        finally:
            db.close()

    except Exception as e:
        logger.error(f"voice_handler error: {e}")
        await msg.edit_text(f"❌ Ошибка обработки голосового сообщения: {e}\nНапишите текстом: /new")


# ─── /ping command ──────────────────────────────────────────────────────────

async def cmd_ping(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /ping <ip>")
        return

    ip = context.args[0]
    await update.message.reply_text(f"📡 Пинг {ip}...")

    from ..core.ping_worker import _ping_host
    is_online, ms = await _ping_host(ip)

    if is_online:
        await update.message.reply_text(f"✅ Онлайн — {ms}ms" if ms else "✅ Онлайн")
    else:
        await update.message.reply_text("❌ Недоступен")


# ─── Reply keyboard text handler ──────────────────────────────────────────────

async def text_handler(update, context):
    """Handle Reply keyboard button presses."""
    text = update.message.text
    if text == "📊 Статус":
        await cmd_status(update, context)
    elif text == "📋 Тикеты":
        await cmd_tickets(update, context)
    elif text == "⚠️ Просроченные":
        await cmd_overdue(update, context)
    elif text == "📈 Статистика":
        await cmd_mystats(update, context)


# ─── Callback query handler ───────────────────────────────────────────────────

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Refresh status inline button
    if data == "refresh_status":
        from ..core.ping_worker import get_all_statuses
        cache = get_all_statuses()
        online = [v for v in cache.values() if v.get("online")]
        offline = [v for v in cache.values() if not v.get("online")]
        text = f"🖥 *Мониторинг серверов* _(обновлено {datetime.now().strftime('%H:%M')})_\n✅ Онлайн: {len(online)}\n❌ Оффлайн: {len(offline)}\n"
        if offline:
            text += "\n*Оффлайн клиенты:*\n"
            for v in offline[:20]:
                text += f"• {v.get('client_name', '?')} ({v.get('ip', '?')})\n"
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        try:
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status"),
                ]])
            )
        except Exception:
            pass
        return

    from ..models.tickets import Ticket, TicketStatus
    db = _db_factory()
    try:
        if data.startswith("take_"):
            ticket_id = int(data.split("_")[1])
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if t:
                t.status = TicketStatus.in_progress
                db.commit()
                await query.edit_message_text(
                    f"🔄 Тикет #{ticket_id} взят в работу",
                    reply_markup=None,
                )

        elif data.startswith("close_"):
            ticket_id = int(data.split("_")[1])
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if t:
                t.status = TicketStatus.closed
                if not t.resolved_at:
                    t.resolved_at = datetime.now(timezone.utc)
                db.commit()
                await query.edit_message_text(
                    f"🔒 Тикет #{ticket_id} закрыт",
                    reply_markup=None,
                )

        elif data.startswith("resolve_"):
            ticket_id = int(data.split("_")[1])
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if t:
                t.status = TicketStatus.resolved
                if not t.resolved_at:
                    t.resolved_at = datetime.now(timezone.utc)
                db.commit()
                await query.edit_message_text(
                    f"✅ Тикет #{ticket_id} решён",
                    reply_markup=None,
                )

        elif data.startswith("inprog_"):
            ticket_id = int(data.split("_")[1])
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if t:
                t.status = TicketStatus.in_progress
                db.commit()
                await query.edit_message_text(
                    f"🔄 Тикет #{ticket_id} в работе",
                    reply_markup=None,
                )

        elif data.startswith("newtkt_"):
            client_id = int(data.split("_")[1])
            from ..models.client import Client
            from ..models.tickets import TicketPriority, TicketSource
            from ..models.user import User
            client = db.query(Client).filter(Client.id == client_id).first()
            admin = db.query(User).filter(User.username == "admin").first()
            if client and admin:
                ticket = Ticket(
                    client_id=client_id,
                    title=f"Клиент {client.company} недоступен",
                    description=f"IP: {client.ip_address}\nАвтоматически создан при уходе в оффлайн",
                    priority=TicketPriority.high,
                    status=TicketStatus.new,
                    created_by_id=admin.id,
                    source=TicketSource.telegram,
                )
                db.add(ticket)
                db.commit()
                db.refresh(ticket)
                await query.edit_message_text(
                    f"📋 Тикет #{ticket.id} создан для {client.company}\n/ticket {ticket.id}",
                )
                await _send_new_ticket_notification(ticket)
            else:
                await query.answer("Клиент не найден", show_alert=True)

        elif data.startswith("cdata_"):
            ticket_id = int(data.split("_")[1])
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not t:
                await query.answer("Тикет не найден", show_alert=True)
                return

            import json
            shared = json.loads(getattr(t, 'shared_fields', None) or '[]')
            if not shared or not t.client:
                await query.answer("Данные клиента недоступны для этого тикета", show_alert=True)
                return

            client = t.client
            field_map = {
                'ip_address': ('🖥 IP', client.ip_address),
                'login': ('👤 Логин', client.login),
                'password': ('🔐 Пароль', '***скрыт***'),
                'anydesk_id': ('📱 AnyDesk', getattr(client, 'anydesk_id', None)),
                'rudesktop_id': ('🖥 RuDesktop', getattr(client, 'rudesktop_id', None)),
                'notes': ('📝 Примечания', client.notes),
            }

            lines = [f"🔑 *Данные клиента — #{ticket_id}*\n─────────────────────"]
            for field_key in shared:
                if field_key in field_map:
                    label, value = field_map[field_key]
                    if value:
                        if field_key == 'password':
                            try:
                                from ..core.encryption import decrypt
                                value = decrypt(client.password_encrypted)
                            except Exception:
                                value = '(ошибка дешифровки)'
                        lines.append(f"{label}: `{value}`")

            if len(lines) == 1:
                text = "🔒 Нет доступных данных клиента."
            else:
                text = "\n".join(lines)

            await query.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


# ─── SLA breach job ───────────────────────────────────────────────────────────

async def _check_sla_breaches(context):
    """JobQueue callback — check for newly breached SLA tickets."""
    if not _notify_chat_id:
        return
    from ..models.tickets import Ticket, TicketStatus
    db = _db_factory()
    try:
        active = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.new, TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress])
        ).all()

        for t in active:
            rem = _sla_remaining_minutes(t)
            if rem is None:
                continue
            # Notify when SLA just breached (between -5 and 0 minutes)
            if -5 <= rem <= 0 and not getattr(t, "_notified_sla", False):
                emoji = PRIORITY_EMOJI.get(t.priority.value, "⚪")
                client_name = t.client.company if t.client else "Без клиента"
                try:
                    await context.bot.send_message(
                        chat_id=_notify_chat_id,
                        text=(
                            f"🚨 *SLA нарушен!*\n"
                            f"#{t.id} {emoji} {t.priority.value.upper()}\n"
                            f"Клиент: {client_name}\n"
                            f"{t.title}\n\n"
                            f"/ticket {t.id}"
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(f"SLA breach notification failed: {e}")
    finally:
        db.close()


# ─── Notifications ────────────────────────────────────────────────────────────

async def _send_new_ticket_notification(ticket):
    global _notify_chat_id
    if not _application:
        return

    # Determine target chat_id: from notify_channel or default
    target_chat = _notify_chat_id
    if getattr(ticket, 'notify_channel_id', None):
        try:
            from ..models.notification_channels import NotificationChannel
            db = _db_factory()
            try:
                ch = db.query(NotificationChannel).filter(
                    NotificationChannel.id == ticket.notify_channel_id,
                    NotificationChannel.is_active.is_(True),
                ).first()
                if ch and ch.chat_id:
                    target_chat = ch.chat_id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to resolve notify_channel_id: {e}")

    if not target_chat:
        return

    try:
        pv = ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority
        emoji = PRIORITY_EMOJI.get(pv, "📋")
        client_name = ticket.client.company if ticket.client else "Без клиента"
        text = (
            f"📩 *Новый тикет #{ticket.id}*\n"
            f"Клиент: {client_name}\n"
            f"Приоритет: {emoji} {pv.upper()}\n"
            f"{ticket.title}\n\n"
            f"/ticket {ticket.id}"
        )
        await _application.bot.send_message(
            chat_id=target_chat,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Failed to send new ticket notification: {e}")


async def notify_new_ticket(ticket_id: int):
    """Called from tickets endpoint when a new ticket is created."""
    if not _application or not _notify_chat_id:
        return
    from ..models.tickets import Ticket
    db = _db_factory()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            await _send_new_ticket_notification(ticket)
    finally:
        db.close()


async def notify_ping_change(
    client_id: int,
    client_name: str,
    ip: str,
    is_online: bool,
    now: datetime,
    old_status: dict,
):
    """Called by ping_worker when client goes online/offline."""
    if not _application or not _notify_chat_id:
        return
    try:
        if is_online:
            text = (
                f"✅ *Клиент снова ОНЛАЙН*\n"
                f"Клиент: {client_name} ({ip})\n"
                f"Время: {now.strftime('%H:%M')}"
            )
        else:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Создать тикет", callback_data=f"newtkt_{client_id}"),
            ]])
            text = (
                f"🚨 *Клиент ОФФЛАЙН*\n"
                f"Клиент: {client_name} ({ip})\n"
                f"Время: {now.strftime('%H:%M')}"
            )
            await _application.bot.send_message(
                chat_id=_notify_chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=kb,
            )
            return

        await _application.bot.send_message(
            chat_id=_notify_chat_id,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Failed to send ping notification: {e}")


# ─── Bot startup ──────────────────────────────────────────────────────────────

async def start_bot(token: str, db_factory):
    global _application, _db_factory, _notify_chat_id

    _db_factory = db_factory

    from ..config import settings
    _notify_chat_id = settings.TELEGRAM_NOTIFY_CHAT_ID or None

    from ..core.ping_worker import set_notify_callback
    set_notify_callback(notify_ping_change)

    try:
        from telegram.ext import (
            Application,
            CommandHandler,
            CallbackQueryHandler,
            ConversationHandler,
            MessageHandler,
            filters,
        )
        from telegram import BotCommand
    except ImportError:
        logger.error("python-telegram-bot not installed. Run: pip install 'python-telegram-bot[job-queue]==21.3'")
        return

    app = Application.builder().token(token).build()
    _application = app

    # Register bot commands in Telegram UI
    commands = [
        BotCommand("start",   "Главное меню"),
        BotCommand("status",  "Мониторинг серверов"),
        BotCommand("tickets", "Открытые тикеты"),
        BotCommand("overdue", "Просроченные тикеты"),
        BotCommand("mystats", "Статистика"),
        BotCommand("new",     "Создать тикет"),
        BotCommand("ticket",  "Детали тикета (/ticket <id>)"),
        BotCommand("resolve", "Закрыть тикет (/resolve <id>)"),
        BotCommand("ping",    "Проверить IP (/ping <ip>)"),
        BotCommand("help",    "Список команд"),
    ]
    try:
        await app.bot.set_my_commands(commands)
        logger.info("Bot commands registered")
    except Exception as e:
        logger.warning(f"set_my_commands failed: {e}")

    # /new conversation
    new_conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_start)],
        states={
            NEW_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_client)],
            NEW_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_title)],
            NEW_DESC: [MessageHandler(filters.TEXT, new_desc)],
            NEW_PRIORITY: [CallbackQueryHandler(new_priority_callback, pattern=r"^prio_")],
        },
        fallbacks=[],
    )

    # /resolve conversation
    resolve_conv = ConversationHandler(
        entry_points=[CommandHandler("resolve", cmd_resolve)],
        states={
            RESOLVE_COMMENT: [MessageHandler(filters.TEXT, resolve_comment_handler)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("ticket", cmd_ticket))
    app.add_handler(CommandHandler("overdue", cmd_overdue))
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(new_conv)
    app.add_handler(resolve_conv)
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # SLA breach check every 5 minutes via JobQueue
    if app.job_queue:
        app.job_queue.run_repeating(_check_sla_breaches, interval=300, first=60)
        logger.info("SLA breach job scheduled (every 5 min)")

    logger.info("Starting Telegram bot polling...")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            await app.updater.stop()
            await app.stop()
