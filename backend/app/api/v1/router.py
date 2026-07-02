from fastapi import APIRouter

from app.api.v1 import agent, chat, health, legal, market
from app.api.v1 import approvals as approvals_router
from app.api.v1 import pin as pin_router
from app.api.v1 import whatsapp as wa_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
