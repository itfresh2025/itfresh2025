from fastapi import APIRouter
from .endpoints import auth, clients, users, export, ping, tickets, field_options, updates
from .endpoints import notification_channels, downloads

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(ping.router, prefix="/ping", tags=["ping"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(field_options.router, prefix="/field-options", tags=["field-options"])
api_router.include_router(updates.router, prefix="/updates", tags=["updates"])
api_router.include_router(notification_channels.router, prefix="/notification-channels", tags=["notification-channels"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])
