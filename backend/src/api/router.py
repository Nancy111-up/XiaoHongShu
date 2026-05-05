"""API router — 聚合所有子路由"""

from fastapi import APIRouter

from src.api.v1.agent import router as agent_router
from src.api.v1.board import router as board_router

router = APIRouter(prefix="/api/v1")
router.include_router(agent_router)
router.include_router(board_router)
