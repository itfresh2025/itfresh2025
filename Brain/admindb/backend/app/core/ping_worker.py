"""Background ping worker — runs as asyncio task in FastAPI lifespan."""
import asyncio
import platform
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Current ping status cache: {client_id: {online, ms, checked_at}}
_status_cache: Dict[int, Dict[str, Any]] = {}

# Telegram notification callback (set by telegram_bot.py)
_notify_callback = None


def set_notify_callback(cb):
    """Register async callback for Telegram offline/online alerts."""
    global _notify_callback
    _notify_callback = cb


def get_status(client_id: int) -> Optional[Dict[str, Any]]:
    return _status_cache.get(client_id)


def get_all_statuses() -> Dict[int, Dict[str, Any]]:
    return dict(_status_cache)


async def _ping_host(ip: str) -> tuple[bool, Optional[int]]:
    """Ping a single IP. Returns (is_online, response_ms)."""
    if not ip or ip.strip() == "":
        return False, None

    try:
        if platform.system() == "Windows":
            cmd = ["ping", "-n", "1", "-w", "1000", ip.strip()]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip.strip()]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        except asyncio.TimeoutError:
            proc.kill()
            return False, None

        output = stdout.decode("utf-8", errors="ignore")

        # Parse response time
        ms = None
        # Windows: "time=25ms" or "время=25мс"
        match = re.search(r"(?:time|время)[=<](\d+)", output, re.IGNORECASE)
        if match:
            ms = int(match.group(1))

        is_online = proc.returncode == 0
        return is_online, ms

    except Exception as e:
        logger.debug(f"Ping error for {ip}: {e}")
        return False, None


async def _run_ping_cycle(db_factory):
    """Single ping cycle: ping all clients and save results."""
    from ..models.client import Client
    from ..models.ping_history import PingHistory

    db = db_factory()
    try:
        clients = db.query(Client).filter(
            Client.is_active == True,
            Client.ip_address != None,
            Client.ip_address != "",
        ).all()

        now = datetime.now(timezone.utc)

        for client in clients:
            old_status = _status_cache.get(client.id)
            old_online = old_status["online"] if old_status else None

            is_online, ms = await _ping_host(client.ip_address)

            _status_cache[client.id] = {
                "online": is_online,
                "ms": ms,
                "checked_at": now.isoformat(),
                "client_name": client.company,
                "ip": client.ip_address,
            }

            # Save to history
            history = PingHistory(
                client_id=client.id,
                checked_at=now,
                is_online=is_online,
                response_ms=ms,
            )
            db.add(history)

            # Telegram notification on status change
            if _notify_callback and old_online is not None and old_online != is_online:
                try:
                    asyncio.create_task(
                        _notify_callback(
                            client_id=client.id,
                            client_name=client.company,
                            ip=client.ip_address,
                            is_online=is_online,
                            now=now,
                            old_status=old_status,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Notify callback error: {e}")

        db.commit()

        # Cleanup old history (keep 30 days)
        cutoff = now - timedelta(days=30)
        db.query(PingHistory).filter(PingHistory.checked_at < cutoff).delete()
        db.commit()

    except Exception as e:
        logger.error(f"Ping cycle error: {e}")
        db.rollback()
    finally:
        db.close()


async def ping_worker_loop(db_factory, interval: int = 60):
    """Main loop — runs forever, pings every `interval` seconds."""
    logger.info(f"Ping worker started (interval={interval}s)")
    while True:
        try:
            await _run_ping_cycle(db_factory)
        except Exception as e:
            logger.error(f"Ping worker unhandled error: {e}")
        await asyncio.sleep(interval)
