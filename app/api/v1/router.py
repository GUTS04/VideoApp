from fastapi import APIRouter

from app.api.v1.endpoints import auth, blocks, coins, config, health, reports, users, ws_info

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(ws_info.router)
api_router.include_router(users.router)
api_router.include_router(config.router)
api_router.include_router(coins.router)
api_router.include_router(blocks.router)
api_router.include_router(reports.router)
