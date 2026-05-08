from fastapi import APIRouter

from app.api.v1 import chat, health, legal

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
