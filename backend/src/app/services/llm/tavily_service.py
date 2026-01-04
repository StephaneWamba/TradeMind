"""Tavily search service for web and Twitter/X search."""

import json
from typing import Any, Optional

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class TavilyService:
    """Service for Tavily search API integration."""

    def __init__(self):
        """Initialize Tavily client."""
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.enabled = self.api_key is not None

        if not self.enabled:
            logger.warning("Tavily API key not configured - search disabled")

    async def web_search(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """
        Perform web search using Tavily.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            Search results with articles, titles, URLs, and content
        """
        if not self.enabled:
            logger.warning("Tavily not enabled, returning empty results")
            return {"results": [], "query": query}

        try:
            response = await self.client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": max_results,
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                })

            answer = data.get("answer", "")

            logger.info(
                "Tavily web search completed",
                query=query,
                results_count=len(results),
                has_answer=bool(answer),
            )

            return {
                "results": results,
                "answer": answer,
                "query": query,
            }

        except Exception as e:
            logger.error("Tavily web search failed", query=query, error=str(e))
            return {"results": [], "query": query, "error": str(e)}

    async def x_search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """
        Search Twitter/X using Tavily.

        Args:
            query: Search query for Twitter/X
            max_results: Maximum number of tweets to return

        Returns:
            Twitter/X search results with tweets and sentiment
        """
        if not self.enabled:
            logger.warning("Tavily not enabled, returning empty results")
            return {"tweets": [], "query": query, "sentiment": "neutral"}

        try:
            twitter_query = f"site:x.com OR site:twitter.com {query}"

            response = await self.client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": twitter_query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": max_results,
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            tweets = []
            for item in data.get("results", []):
                tweets.append({
                    "text": item.get("content", ""),
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                })

            content_text = " ".join([t.get("text", "")
                                    for t in tweets]).lower()
            positive_words = ["bullish", "buy",
                              "moon", "pump", "up", "rise", "gains"]
            negative_words = ["bearish", "sell",
                              "dump", "crash", "down", "fall", "loss"]

            positive_count = sum(
                1 for word in positive_words if word in content_text)
            negative_count = sum(
                1 for word in negative_words if word in content_text)

            if positive_count > negative_count:
                sentiment = "bullish"
            elif negative_count > positive_count:
                sentiment = "bearish"
            else:
                sentiment = "neutral"

            logger.info(
                "Tavily X search completed",
                query=query,
                tweets_count=len(tweets),
                sentiment=sentiment,
            )

            return {
                "tweets": tweets,
                "sentiment": sentiment,
                "query": query,
            }

        except Exception as e:
            logger.error("Tavily X search failed", query=query, error=str(e))
            return {
                "tweets": [],
                "query": query,
                "sentiment": "neutral",
                "error": str(e),
            }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
