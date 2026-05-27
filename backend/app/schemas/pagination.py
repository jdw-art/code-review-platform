from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class PageQuery(BaseModel):
    """后台列表接口统一使用的分页查询参数。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """返回 SQL 查询所需的偏移量。"""
        return (self.page - 1) * self.page_size


class PageResponse(BaseModel, Generic[ItemT]):
    """后台管理列表接口统一响应结构。"""

    items: list[ItemT] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        *,
        items: list[ItemT],
        total: int,
        page: int,
        page_size: int,
    ) -> "PageResponse[ItemT]":
        """根据分页参数构造统一响应。"""
        total_pages = ceil(total / page_size) if total else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
