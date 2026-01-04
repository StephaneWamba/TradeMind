"""LLM-powered strategy endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.llm import MarketAnalysis
from app.services.llm.internet_service import InternetAccessService
from app.services.llm.grok_service import LLMService
from app.services.market import MarketDataService
from app.services.strategy_llm import LLMStrategyService
from app.services.llm.tavily_service import TavilyService

router = APIRouter()


@router.post("/analyze")
async def analyze_market(
    connection_id: int,
    symbol: str,
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Analyze market and get LLM-powered trading decision."""
    try:
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

        # Run analysis
        result = await strategy_service.analyze_and_decide(
            connection_id=connection_id,
            symbol=symbol,
            strategy_id=strategy_id,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-structured")
async def analyze_market_structured(
    connection_id: int,
    symbol: str,
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Analyze market with structured output using Instructor."""
    try:
        # Initialize services
        tavily_service = TavilyService()
        llm_service = LLMService(tavily_service=tavily_service)
        market_service = MarketDataService(db)
        internet_service = InternetAccessService()

        # Get market data
        ticker = await market_service.get_ticker(connection_id, symbol)
        news = await internet_service.fetch_crypto_news(symbol.split("/")[0])
        sentiment = await internet_service.get_sentiment(symbol.split("/")[0])

        market_data = {
            "symbol": symbol,
            "price": ticker.get("price", 0),
            "volume": ticker.get("volume", 0),
        }

        # Get structured analysis
        analysis: MarketAnalysis = await llm_service.analyze_market_structured(
            market_data=market_data,
            news_context=news,
            sentiment=sentiment,
        )

        return {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "analysis": analysis.model_dump(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
