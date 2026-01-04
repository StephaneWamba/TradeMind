"""Grok LLM service with Instructor for structured outputs and Agent Tools."""

import json
import time
from typing import Any, Optional, TypeVar

import instructor
import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

logger = structlog.get_logger(__name__)


class LLMService:
    """Service for LLM operations with Grok 4.1 Fast and Agent Tools."""

    def __init__(self, tavily_service=None):
        """Initialize Grok client with Instructor for structured outputs."""
        self.client = AsyncOpenAI(
            api_key=settings.GROK_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        self.instructor_client = instructor.from_openai(self.client)
        self.model = settings.GROK_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.tavily_service = tavily_service

    async def analyze_market_structured(
        self,
        market_data: dict[str, Any],
        news_context: Optional[list[dict]] = None,
        sentiment: Optional[dict] = None,
        response_model: type[T] = None,
    ) -> T:
        """
        Analyze market with structured output using Instructor and Grok Agent Tools.

        Args:
            market_data: Current market data
            news_context: Recent news articles (optional)
            sentiment: Market sentiment data (optional)
            response_model: Pydantic model for structured output

        Returns:
            Structured trading decision
        """
        if response_model is None:
            from app.schemas.llm import MarketAnalysis

            response_model = MarketAnalysis

        start_time = time.time()
        context = self._build_context(market_data, news_context, sentiment)
        prompt = self._create_analysis_prompt_with_tools(
            context, market_data.get("symbol", "BTC"))

        try:
            result = await self.instructor_client.chat.completions.create(
                model=self.model,
                response_model=response_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency trading analyst with access to real-time data via Agent Tools. ALWAYS use x_search for Twitter/X sentiment. Use web_search for news and Reddit (with site:reddit.com queries). Analyze market conditions to make trading decisions.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=self._get_agent_tools(),
            )

            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Structured LLM analysis completed with Agent Tools", latency_ms=latency_ms)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Structured LLM analysis failed",
                         error=str(e), latency_ms=latency_ms)
            raise

    async def analyze_market(
        self,
        market_data: dict[str, Any],
        news_context: Optional[list[dict]] = None,
        sentiment: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Analyze market conditions using Grok Agent Tools for real-time data.

        Args:
            market_data: Current market data (price, indicators, etc.)
            news_context: Recent news articles (optional)
            sentiment: Market sentiment data (optional)

        Returns:
            Trading decision with reasoning
        """
        start_time = time.time()

        context = self._build_context(market_data, news_context, sentiment)
        symbol = market_data.get("symbol", "BTC")
        prompt = self._create_analysis_prompt_with_tools(context, symbol)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency trading analyst with access to real-time data. ALWAYS use x_search for Twitter/X sentiment when asked. Use web_search for news and Reddit (use site:reddit.com/r/cryptocurrency in queries).",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=self._get_agent_tools(),
                tool_choice="auto",
            )

            msg = response.choices[0].message
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency trading analyst with access to real-time data. ALWAYS use x_search for Twitter/X sentiment when asked. Use web_search for news and Reddit (use site:reddit.com/r/cryptocurrency in queries).",
                },
                {"role": "user", "content": prompt},
            ]

            tool_results = []
            max_tool_iterations = 3
            iteration = 0

            while msg.tool_calls and iteration < max_tool_iterations:
                iteration += 1
                logger.info(
                    "Tool calls detected, executing tools",
                    iteration=iteration,
                    tool_count=len(msg.tool_calls),
                    tool_names=[
                        tc.function.name for tc in msg.tool_calls if hasattr(tc, "function")],
                )

                messages.append(msg)

                for tool_call in msg.tool_calls:
                    tool_name = getattr(tool_call.function, "name", "unknown")
                    tool_args_str = getattr(
                        tool_call.function, "arguments", "{}")

                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse tool arguments",
                                     tool_name=tool_name, arguments=tool_args_str)
                        tool_args = {}

                    logger.debug(
                        "Executing tool",
                        tool_name=tool_name,
                        arguments=tool_args,
                    )

                    tool_result = None
                    if tool_name == "x_search" and self.tavily_service:
                        query = tool_args.get("query", "")
                        result = await self.tavily_service.x_search(query)
                        tool_result = json.dumps(result)
                    elif tool_name == "web_search" and self.tavily_service:
                        query = tool_args.get("query", "")
                        result = await self.tavily_service.web_search(query)
                        tool_result = json.dumps(result)
                    else:
                        logger.warning(
                            "Unknown tool or Tavily not available", tool_name=tool_name)
                        tool_result = json.dumps(
                            {"error": f"Tool {tool_name} not available"})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    })

                    tool_results.append({
                        "name": tool_name,
                        "arguments": tool_args,
                        "result_length": len(tool_result),
                    })

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    tools=self._get_agent_tools(),
                    tool_choice="auto",
                )

                msg = response.choices[0].message

            latency_ms = (time.time() - start_time) * 1000
            decision_text = msg.content or ""

            logger.info(
                "LLM analysis completed with Agent Tools",
                latency_ms=latency_ms,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                tools_used=len(tool_results),
                tool_results=tool_results,
                response_length=len(decision_text),
                iterations=iteration,
            )

            return {
                "decision": decision_text,
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "tools_used": len(tool_results),
                "tool_results": tool_results,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("LLM analysis failed",
                         error=str(e), latency_ms=latency_ms)
            raise

    def _build_context(
        self,
        market_data: dict[str, Any],
        news_context: Optional[list[dict]],
        sentiment: Optional[dict],
    ) -> str:
        """Build context string for LLM with enhanced risk and volatility context."""
        context_parts = []

        context_parts.append("## Market Data")
        context_parts.append(f"Symbol: {market_data.get('symbol', 'N/A')}")
        context_parts.append(
            f"Current Price: ${market_data.get('price', 0):,.2f}")

        context_parts.append("\n## Technical Indicators (Multi-Timeframe)")
        context_parts.append(f"RSI (1h): {market_data.get('rsi_1h', 'N/A')}")
        context_parts.append(f"RSI (4h): {market_data.get('rsi_4h', 'N/A')}")
        context_parts.append(f"RSI (1d): {market_data.get('rsi_1d', 'N/A')}")

        macd_1h = market_data.get('macd_1h')
        if macd_1h:
            context_parts.append(
                f"MACD 1h: {macd_1h.get('macd', 'N/A'):.2f} | Signal: {macd_1h.get('signal', 'N/A'):.2f} | Histogram: {macd_1h.get('histogram', 'N/A'):.2f}")

        atr = market_data.get('atr')
        volatility = market_data.get('volatility_percent')
        if atr and volatility:
            context_parts.append(
                f"\n## Volatility Analysis (CRITICAL FOR RISK)")
            context_parts.append(f"ATR (Average True Range): ${atr:,.2f}")
            context_parts.append(f"Volatility: {volatility:.2f}%")
            if volatility > 5:
                context_parts.append(
                    "⚠️ HIGH VOLATILITY - Use smaller position sizes and wider stop-loss")
            elif volatility < 1:
                context_parts.append(
                    "ℹ️ LOW VOLATILITY - Tighter stop-loss possible")

        bb = market_data.get('bollinger_bands_1h')
        if bb:
            context_parts.append(f"\n## Bollinger Bands (1h)")
            context_parts.append(f"Upper: ${bb.get('upper', 0):,.2f}")
            context_parts.append(f"Middle: ${bb.get('middle', 0):,.2f}")
            context_parts.append(f"Lower: ${bb.get('lower', 0):,.2f}")
            price = market_data.get('price', 0)
            if price > bb.get('upper', 0):
                context_parts.append(
                    "⚠️ Price above upper band - potential overbought")
            elif price < bb.get('lower', 0):
                context_parts.append(
                    "⚠️ Price below lower band - potential oversold")

        context_parts.append(f"\nVolume: {market_data.get('volume', 'N/A')}")

        if news_context:
            context_parts.append("\n## Recent News")
            for news in news_context[:5]:
                context_parts.append(f"- {news.get('title', 'N/A')}")

        if sentiment:
            context_parts.append("\n## Market Sentiment")
            context_parts.append(f"Twitter: {sentiment.get('twitter', 'N/A')}")
            context_parts.append(f"Reddit: {sentiment.get('reddit', 'N/A')}")

        return "\n".join(context_parts)

    def _create_analysis_prompt(self, context: str) -> str:
        """Create analysis prompt for LLM."""
        return f"""Analyze the following market data and provide a trading decision.

{context}

Provide your analysis in the following format:
1. Market Assessment: Brief summary of current market conditions
2. Technical Analysis: Interpretation of indicators
3. News/Sentiment Impact: How news and sentiment affect the market
4. Trading Decision: BUY, SELL, or HOLD
5. Reasoning: Detailed explanation for your decision
6. Confidence: Your confidence level (0.0 to 1.0)
7. Position Size Recommendation: Suggested position size as percentage of portfolio
8. Risk Factors: Key risks to consider

Be concise but thorough. Focus on actionable insights."""

    def _create_analysis_prompt_with_tools(self, context: str, symbol: str) -> str:
        """Create analysis prompt that encourages use of Agent Tools with enhanced risk context."""
        return f"""Analyze the cryptocurrency market for {symbol} and provide a trading decision.

Current Market Data:
{context}

CRITICAL RISK MANAGEMENT RULES:
1. ALWAYS calculate Risk/Reward ratio - minimum 1:2 (risk $1 to make $2)
2. If volatility is HIGH (>5%), use smaller position sizes (0.5-1% max) and wider stop-loss (3-5%)
3. If volatility is LOW (<1%), tighter stop-loss (1-2%) is acceptable
4. NEVER risk more than 2% of portfolio on a single trade
5. Stop-loss MUST be based on ATR or support/resistance levels, not arbitrary percentages
6. Take-profit should be at least 2x the stop-loss distance (1:2 R:R minimum)

IMPORTANT: Use your Agent Tools to gather real-time information:
1. Use x_search to get real-time Twitter/X sentiment about {symbol} - search for tweets discussing price and market sentiment
2. Use web_search to find the latest news about {symbol} and cryptocurrency markets
3. Use web_search with "site:reddit.com/r/cryptocurrency {symbol}" to get Reddit community sentiment
4. Search for any major events, regulations, or market-moving news

After gathering real-time data, provide your analysis in structured format:
1. Market Assessment: Brief summary of current market conditions (consider multi-timeframe alignment)
2. Technical Analysis: Interpretation of indicators across timeframes (1h, 4h, 1d)
3. Volatility Assessment: How current volatility affects position sizing and stop-loss placement
4. News/Sentiment Impact: How the latest news, Twitter sentiment, and Reddit discussions affect the market
5. Trading Decision: BUY, SELL, or HOLD
6. Reasoning: Detailed explanation referencing the real-time data you gathered
7. Confidence: Your confidence level (0.0 to 1.0) - be conservative if volatility is high
8. Position Size Recommendation: Suggested position size as percentage (consider volatility - smaller if high)
9. Stop-Loss: Recommended stop-loss percentage based on ATR/volatility (NOT arbitrary - use technical levels)
10. Take-Profit: Recommended take-profit percentage (MUST be at least 2x stop-loss for 1:2 R:R)
11. Risk/Reward Ratio: Calculate and state the R:R ratio (must be >= 1:2)
12. Risk Factors: Key risks identified from news, sentiment, and technical analysis

Be thorough, risk-aware, and use the Agent Tools to get the most current information. ALWAYS prioritize capital preservation."""

    def _get_agent_tools(self) -> list[dict]:
        """Get Grok Agent Tools configuration."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "x_search",
                    "description": "Search real-time X (Twitter) data for cryptocurrency sentiment, news, and discussions. Use this to get current market sentiment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for X/Twitter (e.g., 'BTC price', 'Bitcoin news')",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for latest cryptocurrency news, market analysis, and events. Use this to find breaking news and market updates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Web search query (e.g., 'Bitcoin price today', 'crypto market news')",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]
