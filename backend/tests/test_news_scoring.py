"""A1 news scoring: credibility ladder, priced-in, amplification."""
from __future__ import annotations

from app.agents.market.news_scoring import (
    classify_credibility,
    detect_amplification,
    detect_priced_in,
    enrich_news,
    score_news,
)
from app.agents.market.schemas import NewsItem


def _item(title="Laba naik", source="Kontan", published="2026-07-10T09:00:00Z",
          sentiment="positive", **kw) -> NewsItem:
    return NewsItem(title=title, source=source, published_at=published,
                    sentiment=sentiment, **kw)


def test_credibility_classification():
    assert classify_credibility("IDX.co.id Keterbukaan") == "primary"
    assert classify_credibility("Kontan") == "secondary"
    assert classify_credibility("Bloomberg") == "secondary"
    assert classify_credibility("Forum Saham Rakyat") == "rumor"
    assert classify_credibility("") == "rumor"


def test_priced_in_detects_pre_publication_move():
    closes = [("2026-07-06T00:00:00", 100.0), ("2026-07-07T00:00:00", 105.0),
              ("2026-07-08T00:00:00", 112.0), ("2026-07-09T00:00:00", 115.0)]
    assert detect_priced_in("2026-07-09T12:00:00Z", closes) is True   # +15%
    flat = [(d, 100.0) for d, _ in closes]
    assert detect_priced_in("2026-07-09T12:00:00Z", flat) is False


def test_priced_in_unparseable_date_is_false_not_crash():
    assert detect_priced_in("not-a-date", [("2026-07-08", 1.0)]) is False


def test_amplification_marks_copies_not_original():
    items = [
        _item(title="Emiten ABCD raih kontrak besar tambang emas",
              source="Blog Saham A", published="2026-07-10T09:00:00Z"),
        _item(title="Emiten ABCD raih kontrak besar proyek tambang emas",
              source="Blog Saham B", published="2026-07-10T11:00:00Z"),
        _item(title="ABCD emiten raih kontrak tambang emas besar sekali",
              source="Forum C", published="2026-07-10T15:00:00Z"),
        _item(title="IHSG ditutup menguat tipis", source="Kontan",
              sentiment="neutral"),
    ]
    marked = detect_amplification(items)
    assert 0 not in marked          # original survives
    assert {1, 2} <= marked         # echoes marked


def test_negative_news_never_amplification_flagged():
    items = [_item(title="Emiten ABCD digugat pailit kreditur besar",
                   sentiment="negative", source=f"Blog {i}",
                   published="2026-07-10T09:00:00Z") for i in range(4)]
    assert detect_amplification(items) == set()


def test_score_weights_primary_over_rumor():
    primary_neg = _item(source="IDX.co.id", sentiment="negative",
                        credibility="primary")
    rumor_pos = [_item(source=f"Forum {i}", sentiment="positive",
                       credibility="rumor",
                       title=f"Cerita berbeda nomor {i} tentang topik unik {i}")
                 for i in range(3)]
    res = score_news([primary_neg, *rumor_pos])
    # 6*(-1) + 3*1 = -3 over weight 9 → below neutral
    assert res.score is not None and res.score < 50


def test_priced_in_and_amplified_items_excluded_from_score():
    items = [
        _item(sentiment="positive", already_priced_in=True),
        _item(sentiment="positive", coordinated_amplification=True),
        _item(sentiment="negative", source="Kontan", credibility="secondary"),
    ]
    res = score_news(items)
    assert res.n_priced_in == 1
    assert res.n_amplified == 1
    assert res.score == 0.0   # only the negative secondary item counts


def test_no_scorable_news_is_none_not_neutral():
    res = score_news([_item(already_priced_in=True)])
    assert res.score is None


def test_enrich_fills_all_fields():
    items = [_item(source="Kontan")]
    out = enrich_news(items, [("2026-07-08T00:00:00", 100.0),
                              ("2026-07-09T00:00:00", 101.0)])
    assert out[0].credibility == "secondary"
    assert out[0].already_priced_in is False
