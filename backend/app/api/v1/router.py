from fastapi import APIRouter

from app.api.v1 import agent, chat, health, legal
from app.api.v1 import pin as pin_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
