"""Task ORM model — 创作任务卡片持久化，对齐 IMPLEMENTATION_PLAN §2.2"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_input: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(20), default="manual"
    )  # "inspiration_pool" | "manual"
    status: Mapped[str] = mapped_column(
        String(30), default="in_progress"
    )  # "in_progress" | "waiting_for_human" | "done" | "cancelled"
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 内容快照（JSON 字符串列）
    draft_copy: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_guidance_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_copy: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_history_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Kanban 列位置
    column: Mapped[str] = mapped_column(
        String(20), default="in_progress"
    )  # "inspiration" | "in_progress" | "pending_review" | "done"

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
