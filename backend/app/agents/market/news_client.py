"""News API client + Gemini categorical sentiment tagger.

Returns a list of NewsItem; the LLM produces ONLY a categorical
positive/neutral/negative tag — never a numeric score (anti-LLM-quant rule).

Coverage & cost notes:
- IDX coverage is mostly Indonesian-language press, so we query NewsAPI in
  both `id` and `en` and merge/dedup the results.
- All headlines of one fetch are tagged in a SINGLE batched Gemini call
  (JSON array in/out) instead of one call per headline.
- Results are cached in-process per (ticker, max_items) for a short TTL so
  page flips don't burn the 100-requests/day NewsAPI free-tier quota."""
from __future__ import annotations

import json
import logging
import time

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.market.schemas import NewsItem
from app.core.config import settings
from app.core.gemini import extract_text, get_chat_model

log = logging.getLogger(__name__)

NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_LANGUAGES = ("id", "en")
CACHE_TTL_SECONDS = 600.0

_cache: dict[str, tuple[float, list[NewsItem]]] = {}

# NewsAPI's /everything does literal keyword matching against article text,
# and real articles almost never spell out a raw ticker — searching "BBCA.JK"
# returns 0 results, "BBCA" alone returns ~1-2, but the company name returns
# hundreds. Cover the tickers AstaLink actually surfaces by default; anything
# else falls back to the bare ticker code (suffix stripped).
_IDX_COMPANY_NAMES: dict[str, str] = {
    "BBCA": "Bank Central Asia",
    "TLKM": "Telkom Indonesia",
    "ASII": "Astra International",
    "BBRI": "Bank Rakyat Indonesia",
}

SENTIMENT_BATCH_SYSTEM = """\
You categorize financial news headlines as positive, neutral, or negative for
the named ticker. Respond with ONLY a JSON array of strings — one entry per
headline, same order, each exactly "positive", "neutral", or "negative".
No prose, no code fences. Example: ["positive","neutral","negative"]"""

_VALID_SENTIMENTS = ("positive", "neutral", "negative")


def _news_query(ticker: str) -> str:
    code = ticker.split(".")[0].upper()
    name = _IDX_COMPANY_NAMES.get(code)
    # Quote multi-word company names for exact-phrase matching — unquoted,
    # NewsAPI ORs the individual words and returns unrelated "Asia" / "Bank"
    # noise instead of articles actually about the company.
    return f'"{name}"' if name else code


def _tag_sentiments(headlines: list[str], ticker: str) -> list[str]:
    """One batched Gemini call for all headlines; degrades to all-neutral."""
    if not headlines:
        return []
    numbered = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
    try:
        resp = get_chat_model().invoke([
            SystemMessage(content=SENTIMENT_BATCH_SYSTEM),
            HumanMessage(content=f"Ticker: {ticker}\nHeadlines:\n{numbered}"),
        ])
        text = extract_text(resp.content).strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[4:] if text.startswith("json") else text
        tags = json.loads(text)
        if not isinstance(tags, list):
            raise ValueError(f"expected JSON array, got {type(tags).__name__}")
    except Exception as exc:  # noqa: BLE001 — sentiment is best-effort
        log.warning("news_client: batch sentiment failed (%s), defaulting to neutral", exc)
        return ["neutral"] * len(headlines)

    out: list[str] = []
    for i in range(len(headlines)):
        word = str(tags[i]).strip().lower() if i < len(tags) else "neutral"
        out.append(word if word in _VALID_SENTIMENTS else "neutral")
    return out


def _fetch_articles(query: str, language: str, page_size: int) -> list[dict]:
    resp = httpx.get(
        NEWS_API_URL,
        params={"q": query, "pageSize": page_size, "language": language,
                "sortBy": "publishedAt", "apiKey": settings.NEWS_API_KEY},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json().get("articles", [])


def fetch_news(ticker: str, max_items: int = 12) -> list[NewsItem]:
    if not settings.NEWS_API_KEY:
        log.warning("news_client: NEWS_API_KEY unset, returning empty news list")
        return []

    cache_key = f"{ticker.upper()}:{max_items}"
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    query = _news_query(ticker)
    raw: list[dict] = []
    for language in NEWS_LANGUAGES:
        try:
            raw.extend(_fetch_articles(query, language, max_items))
        except Exception as exc:  # noqa: BLE001 — one language failing shouldn't kill both
            log.error("news_client: fetch failed for %s (lang=%s): %s", ticker, language, exc)

    # Dedup across languages/syndication by normalized title, newest first.
    seen: set[str] = set()
    articles: list[dict] = []
    for art in sorted(raw, key=lambda a: a.get("publishedAt") or "", reverse=True):
        title = (art.get("title") or "").strip()
        title_key = title.lower()
        if not title or title_key in seen:
            continue
        seen.add(title_key)
        articles.append(art)
        if len(articles) >= max_items:
            break

    sentiments = _tag_sentiments([a["title"] for a in articles], ticker)

    out: list[NewsItem] = []
    for art, sentiment in zip(articles, sentiments):
        out.append(NewsItem(
            title=art["title"],
            source=(art.get("source") or {}).get("name", "unknown"),
            published_at=art.get("publishedAt", ""),
            sentiment=sentiment,
        ))

    _cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, out)
    return out
