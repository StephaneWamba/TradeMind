"""Order execution endpoints for LLM-powered trading."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.schemas.llm import TradingDecision
from app.services.execution import ExecutionService
from app.services.llm.grok_service import LLMService
from app.services.llm.tavily_service import TavilyService
from app.services.market import MarketDataService
from app.services.strategy_llm import LLMStrategyService
from app.services.llm.internet_service import InternetAccessService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/execute")
async def execute_llm_decision(
    connection_id: int,
    strategy_id: int,
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute LLM-powered trading decision.

    This endpoint:
    1. Analyzes market using LLM
    2. Gets structured trading decision
    3. Validates decision
    4. Executes order
    5. Creates trade and position records
    6. Places stop-loss/take-profit if specified
    """
    try:
        # Step 1: Get LLM decision
        tavily_service = TavilyService()
        llm_service = LLMService(tavily_service=tavily_service)
        market_service = MarketDataService(db)
        internet_service = InternetAccessService()

        strategy_service = LLMStrategyService(
            llm_service=llm_service,
            market_service=market_service,
            internet_service=internet_service,
        )

        # Analyze and get structured decision
        analysis_result = await strategy_service.analyze_and_decide(
            connection_id=connection_id,
            symbol=symbol,
            strategy_id=strategy_id,
        )

        # Get structured decision from LLM
        from app.schemas.llm import MarketAnalysis

        market_analysis = await llm_service.analyze_market_structured(
            market_data=analysis_result["market_data"],
            response_model=MarketAnalysis,
        )
        decision_result = market_analysis.trading_decision

        # Step 2: Get current price
        ticker = await market_service.get_ticker(connection_id, symbol)
        current_price = ticker.get("price", 0)

        if current_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current price",
            )

        # Step 3: Execute decision (pass ATR from analysis for volatility-based sizing)
        execution_service = ExecutionService(db)
        atr = analysis_result.get("market_data", {}).get("atr")
        execution_result = await execution_service.execute_llm_decision(
            connection_id=connection_id,
            strategy_id=strategy_id,
            symbol=symbol,
            decision=decision_result,
            current_price=current_price,
            atr=atr,  # Pass ATR for volatility-based position sizing
        )

        return {
            "analysis": analysis_result,
            "decision": decision_result.model_dump(),
            "execution": execution_result,
        }

    except Exception as e:
        logger.error("Execution failed", error=str(
            e), strategy_id=strategy_id, symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
