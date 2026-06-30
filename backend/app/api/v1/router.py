from fastapi import APIRouter

from app.api.v1 import game, leaderboard, session

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(game.router, tags=["game"])
api_router.include_router(session.router, tags=["session"])
api_router.include_router(leaderboard.router, tags=["leaderboard"])
