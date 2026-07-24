from fastapi import APIRouter

from app.api.v1 import agent, allocation, audit, auth, business, chat, health, legal, market
from app.api.v1 import approvals as approvals_router
from app.api.v1 import pin as pin_router
from app.api.v1 import portfolio as portfolio_router
from app.api.v1 import whatsapp as wa_router
from app.api.v1 import workspaces as workspaces_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(workspaces_router.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(business.router, prefix="/business", tags=["business"])
api_router.include_router(allocation.router, prefix="/allocation", tags=["allocation"])
api_router.include_router(portfolio_router.router, prefix="/portfolio", tags=["portfolio"])
