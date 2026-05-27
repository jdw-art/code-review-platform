from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LlmModelResponse(BaseModel):
    """大模型配置接口统一响应模型，敏感 API Key 仅返回掩码。"""

    model_config = ConfigDict(protected_namespaces=())

    id: int
    name: str
    provider: str
    model_code: str
    base_url: str | None = None
    api_key_masked: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    prompt_template: str | None = None
    is_default: bool
    is_active: bool
    last_test_status: str | None = None
    last_test_message: str | None = None
    last_test_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LlmModelCreateRequest(BaseModel):
    """创建大模型配置请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True, protected_namespaces=())

    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_code: str = Field(min_length=1, max_length=100)
    base_url: str | None = None
    api_key: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0, le=1)
    prompt_template: str | None = None
    is_default: bool = False
    is_active: bool = True


class LlmModelUpdateRequest(BaseModel):
    """更新大模型配置请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True, protected_namespaces=())

    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_code: str = Field(min_length=1, max_length=100)
    base_url: str | None = None
    api_key: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0, le=1)
    prompt_template: str | None = None
    is_default: bool = False
    is_active: bool = True


class LlmModelStatusUpdateRequest(BaseModel):
    """大模型启停状态更新请求体。"""

    is_active: bool
