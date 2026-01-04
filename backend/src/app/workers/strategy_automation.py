"""Autonomous strategy execution automation."""

import asyncio
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.events import event_bus
from app.models.strategy import Strategy
from app.services.execution import ExecutionService
from app.services.llm.grok_service import LLMService
from app.services.llm.tavily_service import TavilyService
from app.services.market import MarketDataService
from app.services.strategy_llm import LLMStrategyService
from app.services.llm.internet_service import InternetAccessService
from app.domain.risk.management import RiskManagementService

logger = structlog.get_logger(__name__)


async def execute_strategy_automation(strategy_id: int, symbol: str = "BTC/USDT"):
    """
    Automatically execute a strategy for a given symbol.
    
    This function:
    1. Checks if strategy is active
    2. Validates risk limits
    3. Analyzes market using LLM
    4. Executes trade if conditions are met
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get strategy
            strategy = await db.get(Strategy, strategy_id)
            if not strategy or not strategy.is_active:
                logger.info("Strategy not active, skipping automation", strategy_id=strategy_id)
                return {"status": "skipped", "reason": "strategy_not_active"}
            
            connection_id = strategy.exchange_connection_id
            
            # Check risk limits
            risk_service = RiskManagementService(db)
            daily_loss_status = await risk_service.check_daily_loss_limit(strategy_id)
            if daily_loss_status.get("limit_reached"):
                logger.warning("Daily loss limit reached, skipping automation", strategy_id=strategy_id)
                return {"status": "skipped", "reason": "daily_loss_limit_reached"}
            
            # Initialize services
            tavily_service = TavilyService()
            llm_service = LLMService(tavily_service=tavily_service)
            market_service = MarketDataService(db)
            internet_service = InternetAccessService()
            
            strategy_service = LLMStrategyService(
                llm_service=llm_service,
                market_service=market_service,
                internet_service=internet_service,
            )
            
            # Analyze market
            analysis_result = await strategy_service.analyze_and_decide(
                connection_id=connection_id,
                symbol=symbol,
                strategy_id=strategy_id,
            )
            
            # Get structured decision
            from app.schemas.llm import MarketAnalysis
            market_analysis = await llm_service.analyze_market_structured(
                market_data=analysis_result["market_data"],
                response_model=MarketAnalysis,
            )
            decision = market_analysis.trading_decision
            
            # Only execute if decision is BUY and confidence is high enough
            if decision.action != "BUY" or decision.confidence < 0.6:
                logger.info(
                    "Decision not suitable for execution",
                    strategy_id=strategy_id,
                    action=decision.action,
                    confidence=decision.confidence,
                )
                return {
                    "status": "skipped",
                    "reason": "low_confidence_or_hold",
                    "action": decision.action,
                    "confidence": decision.confidence,
                }
            
            # Execute trade
            execution_service = ExecutionService(db)
            ticker = await market_service.get_ticker(connection_id, symbol)
            current_price = ticker.get("price", 0)
            atr = analysis_result.get("market_data", {}).get("atr")
            
            execution_result = await execution_service.execute_llm_decision(
                connection_id=connection_id,
                strategy_id=strategy_id,
                symbol=symbol,
                decision=decision,
                current_price=current_price,
                atr=atr,
            )
            
            logger.info(
                "Autonomous trade executed",
                strategy_id=strategy_id,
                symbol=symbol,
                action=decision.action,
                confidence=decision.confidence,
            )
            
            return {
                "status": "executed",
                "execution_result": execution_result,
                "decision": decision.model_dump(),
            }
            
        except Exception as e:
            logger.error(
                "Error in strategy automation",
                strategy_id=strategy_id,
                symbol=symbol,
                error=str(e),
            )
            return {"status": "error", "error": str(e)}


async def run_automation_for_all_active_strategies():
    """Run automation for all active strategies."""
    async with AsyncSessionLocal() as db:
        try:
            # Get all active strategies
            stmt = select(Strategy).where(
                Strategy.is_active == True,
                Strategy.status == "active"
            )
            result = await db.execute(stmt)
            strategies = result.scalars().all()
            
            if not strategies:
                logger.debug("No active strategies found for automation")
                return
            
            # Default symbol (could be made configurable per strategy)
            default_symbol = "BTC/USDT"
            
            # Execute each strategy
            for strategy in strategies:
                try:
                    await execute_strategy_automation(strategy.id, default_symbol)
                except Exception as e:
                    logger.error(
                        "Failed to execute strategy automation",
                        strategy_id=strategy.id,
                        error=str(e),
                    )
                    continue
                    
        except Exception as e:
            logger.error("Error in automation loop", error=str(e))

