"""News API client + Gemini categorical sentiment tagger.

Returns a list of NewsItem; the LLM produces ONLY a categorical
positive/neutral/negative tag — never a numeric score (anti-LLM-quant rule)."""
from __future__ import annotations

import logging

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.schemas import NewsItem
from app.core.config import settings
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

NEWS_API_URL = "https://newsapi.org/v2/everything"

SENTIMENT_SYSTEM = """\
You categorize a financial news headline as positive, neutral, or negative for
the named ticker. Respond with ONE word only: positive, neutral, or negative."""


def _tag_sentiment(headline: str, ticker: str) -> str:
    llm = get_chat_model()
    resp = llm.invoke([
        SystemMessage(content=SENTIMENT_SYSTEM),
        HumanMessage(content=f"Ticker: {ticker}\nHeadline: {headline}"),
    ])
    word = resp.content.strip().lower().split()[0] if resp.content else "neutral"
    return word if word in ("positive", "neutral", "negative") else "neutral"


def fetch_news(ticker: str, max_items: int = 5) -> list[NewsItem]:
    if not settings.NEWS_API_KEY:
        log.warning("news_client: NEWS_API_KEY unset, returning empty news list")
        return []

    try:
        resp = httpx.get(
            NEWS_API_URL,
            params={"q": ticker, "pageSize": max_items, "language": "en",
                    "sortBy": "publishedAt", "apiKey": settings.NEWS_API_KEY},
            timeout=10.0,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        log.error("news_client: fetch failed for %s: %s", ticker, exc)
        return []

    out: list[NewsItem] = []
    for art in articles[:max_items]:
        title = art.get("title", "")
        if not title:
            continue
        out.append(NewsItem(
            title=title,
            source=(art.get("source") or {}).get("name", "unknown"),
            published_at=art.get("publishedAt", ""),
            sentiment=_tag_sentiment(title, ticker),
        ))
    return out
