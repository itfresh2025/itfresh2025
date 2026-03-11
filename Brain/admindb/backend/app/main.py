import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from .api.v1.router import api_router
from .config import settings
from .models import user, client, history  # register existing models
from .models import ping_history, tickets, ticket_comments  # register new models
from .models import ticket_events, ticket_relations, field_options  # register extended models
from .models import notification_channels  # register new model
from .core.security import get_password_hash
from .models.user import User, UserRole
from .core.ping_worker import ping_worker_loop

logger = logging.getLogger(__name__)

_ping_task = None
_bot_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ping_task, _bot_task

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Ensure admin user exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.FIRST_ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=settings.FIRST_ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Created admin user: {settings.FIRST_ADMIN_USERNAME}")
    finally:
        db.close()

    # Start ping worker
    _ping_task = asyncio.create_task(ping_worker_loop(SessionLocal, interval=60))
    logger.info("Ping worker task created")

    # Start Telegram bot (optional — skip if token not set)
    try:
        from .bot.telegram_bot import start_bot
        token = settings.TELEGRAM_BOT_TOKEN
        if token:
            _bot_task = asyncio.create_task(start_bot(token, SessionLocal))
            logger.info("Telegram bot task created")
        else:
            logger.info("TELEGRAM_BOT_TOKEN not set, bot disabled")
    except Exception as e:
        logger.warning(f"Telegram bot not started: {e}")

    yield

    # Shutdown
    if _ping_task:
        _ping_task.cancel()
        try:
            await _ping_task
        except asyncio.CancelledError:
            pass

    if _bot_task:
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.APP_NAME, version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "2.0.0"}
