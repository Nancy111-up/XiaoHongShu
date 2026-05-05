"""Kanban board API endpoint — 对齐 IMPLEMENTATION_PLAN §3"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.board import KanbanBoardResponse
from src.schemas.common import APIResponse
from src.services.board_service import get_kanban_board

router = APIRouter(prefix="/board", tags=["board"])


@router.get("")
async def board(db: AsyncSession = Depends(get_db)) -> APIResponse[KanbanBoardResponse]:
    board_data = await get_kanban_board(db)
    return APIResponse.ok(board_data)
