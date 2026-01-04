"""Strategy schemas for API requests/responses."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_serializer


class StrategyCreate(BaseModel):
    """Schema for creating a strategy."""

    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    strategy_type: str = Field(
        default="llm_agent", description="Strategy type (e.g., 'llm_agent')"
    )
    config: dict[str, Any] = Field(
        default_factory=dict, description="Strategy configuration"
    )
    exchange_connection_id: int = Field(..., description="Exchange connection ID")
    is_active: bool = Field(default=False, description="Whether strategy is active")


class StrategyResponse(BaseModel):
    """Schema for strategy response."""

    id: int
    name: str
    description: Optional[str]
    strategy_type: str
    config: dict[str, Any]
    exchange_connection_id: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }

