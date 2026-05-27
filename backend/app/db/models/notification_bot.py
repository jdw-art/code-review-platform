from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class NotificationBot(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    """通知机器人配置表，保存 webhook 与模板设置。"""

    __tablename__ = "notification_bots"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_masked: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mention_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    template_config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    projects = relationship("Project", back_populates="default_bot")
