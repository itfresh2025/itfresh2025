"""Centralized Telegram notification helpers."""
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_application = None  # Set by telegram_bot.py


def set_application(app):
    global _application
    _application = app


async def _send(chat_id: str, text: str, reply_markup=None):
    if not _application or not chat_id:
        return
    try:
        await _application.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.warning(f"Telegram notify failed (chat_id={chat_id}): {e}")


async def notify(text: str, chat_id: Optional[str] = None, reply_markup=None):
    """Send to specific chat_id or default NOTIFY_CHAT_ID."""
    from ..config import settings
    target = chat_id or settings.TELEGRAM_NOTIFY_CHAT_ID
    if target:
        await _send(target, text, reply_markup)


async def notify_channel(channel_id: int, text: str, db=None, reply_markup=None):
    """Send to a specific notification channel from DB."""
    if not db or not channel_id:
        return
    try:
        from ..models.notification_channels import NotificationChannel
        channel = db.query(NotificationChannel).filter(
            NotificationChannel.id == channel_id,
            NotificationChannel.is_active == True
        ).first()
        if channel and channel.chat_id:
            await _send(channel.chat_id, text, reply_markup)
    except Exception as e:
        logger.warning(f"notify_channel failed: {e}")


PRIORITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
STATUS_EMOJI = {"new": "🆕", "assigned": "👤", "in_progress": "🔄", "pending": "⏸", "resolved": "✅", "closed": "🔒"}


async def notify_offline(client, db=None):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Создать тикет", callback_data=f"ct_{client.id}")
    ]])
    group = getattr(client, 'group_name', '') or ''
    text = (
        f"🚨 *СЕРВЕР НЕДОСТУПЕН*\n"
        f"─────────────────────\n"
        f"🖥 {group + ' / ' if group else ''}{client.company}\n"
        f"📡 IP: `{client.ip_address}`\n"
        f"🕐 {datetime.now(timezone.utc).strftime('%H:%M')}"
    )
    await notify(text, reply_markup=keyboard)


async def notify_online(client, duration_str: str = "", db=None):
    group = getattr(client, 'group_name', '') or ''
    text = (
        f"✅ *Сервер восстановлен*\n"
        f"─────────────────────\n"
        f"🖥 {group + ' / ' if group else ''}{client.company}\n"
        f"📡 IP: `{client.ip_address}`\n"
        + (f"⏱ Недоступен: {duration_str}" if duration_str else "")
    )
    await notify(text)


async def notify_new_ticket(ticket, db=None):
    prio = ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority)
    emoji = PRIORITY_EMOJI.get(prio, "📋")
    client_name = ticket.client.company if ticket.client else "Без клиента"
    group = getattr(ticket.client, 'group_name', '') or '' if ticket.client else ''

    SLA = {"critical": "1 час", "high": "4 часа", "medium": "24 часа", "low": "72 часа"}

    text = (
        f"📩 *Новый тикет #{ticket.id}*\n"
        f"─────────────────────\n"
        f"🖥 {group + ' / ' if group else ''}{client_name}\n"
        f"{emoji} {prio.upper()} · {ticket.title}\n"
        f"⏱ SLA: {SLA.get(prio, '?')}\n\n"
        f"/ticket {ticket.id}"
    )

    target_chat = None
    if ticket.notify_channel_id and db:
        from ..models.notification_channels import NotificationChannel
        ch = db.query(NotificationChannel).filter(
            NotificationChannel.id == ticket.notify_channel_id,
            NotificationChannel.is_active == True
        ).first()
        if ch and ch.chat_id:
            target_chat = ch.chat_id

    await notify(text, chat_id=target_chat)


async def notify_sla_breach(ticket, elapsed_minutes: int, db=None):
    prio = ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority)
    emoji = PRIORITY_EMOJI.get(prio, "⚠️")
    client_name = ticket.client.company if ticket.client else "Без клиента"
    group = getattr(ticket.client, 'group_name', '') or '' if ticket.client else ''
    assigned = ticket.assigned_to.username if ticket.assigned_to else "Не назначен"

    hours, mins = divmod(elapsed_minutes, 60)
    duration = f"{hours}ч {mins}м" if hours else f"{mins}м"

    text = (
        f"⚠️ *SLA НАРУШЕН!*\n"
        f"─────────────────────\n"
        f"#{ticket.id} {emoji} {prio.upper()}\n"
        f"📝 {ticket.title}\n"
        f"🖥 {group + ' / ' if group else ''}{client_name}\n"
        f"👤 {assigned}\n"
        f"⏱ Просрочен: {duration}\n\n"
        f"/ticket {ticket.id}"
    )
    await notify(text)
