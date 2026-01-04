"""Pydantic schemas for LLM structured outputs using Instructor."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TradingDecision(BaseModel):
    """Structured trading decision from LLM."""

    action: Literal["BUY", "SELL", "HOLD"] = Field(description="Trading action to take")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence level from 0.0 to 1.0"
    )
    reasoning: str = Field(description="Detailed reasoning for the decision")
    position_size_percent: float = Field(
        ge=0.0, le=0.02, description="Recommended position size as percentage (max 2%)"
    )
    stop_loss_percent: Optional[float] = Field(
        default=None, ge=0.0, le=0.10, description="Stop loss percentage (optional)"
    )
    take_profit_percent: Optional[float] = Field(
        default=None, ge=0.0, le=0.20, description="Take profit percentage (optional)"
    )
    risk_factors: list[str] = Field(
        default_factory=list, description="Key risk factors to consider"
    )


class MarketAnalysis(BaseModel):
    """Structured market analysis from LLM."""

    market_assessment: str = Field(description="Brief summary of market conditions")
    technical_analysis: str = Field(description="Interpretation of technical indicators")
    news_impact: str = Field(description="Impact of news and sentiment on market")
    trading_decision: TradingDecision = Field(description="Trading decision")

