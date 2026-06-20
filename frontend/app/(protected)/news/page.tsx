"use client";
import { useEffect, useState } from "react";
import { Minus, Newspaper, TrendingDown, TrendingUp } from "lucide-react";
import { api, NewsArticle, NewsResponse } from "@/lib/api-client";

const TICKERS = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const SENTIMENT_ICON: Record<NewsArticle["sentiment"], React.ReactNode> = {
  positive: <TrendingUp className="h-3 w-3" />,
  neutral: <Minus className="h-3 w-3" />,
  negative: <TrendingDown className="h-3 w-3" />,
};

const SENTIMENT_CLASS: Record<NewsArticle["sentiment"], string> = {
  positive: "text-[#05b169] bg-[#05b16915] border-[#05b16930]",
  neutral: "text-[#a8acb3] bg-[#a8acb315] border-[#a8acb330]",
  negative: "text-[#cf202f] bg-[#cf202f15] border-[#cf202f30]",
};

export default function NewsPage() {
  const [selectedTicker, setSelectedTicker] = useState("BBCA.JK");
  const [news, setNews] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNews(null);
    api
      .getNews(selectedTicker)
      .then(setNews)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedTicker]);

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      {/* Header + ticker pills */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-white flex-1">External News</h1>
        <div className="flex gap-2">
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedTicker(t)}
              className={`px-3 py-1 text-xs rounded-full font-mono transition-colors ${
                selectedTicker === t
                  ? "bg-[#0052ff] text-white"
                  : "bg-[#16181c] text-[#a8acb3] border border-[#2a2d36] hover:text-white"
              }`}
            >
              {t.replace(".JK", "")}
            </button>
          ))}
        </div>
      </div>

      {/* Skeletons */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-[88px] rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && news && news.articles.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-[#5b616e]">
          <Newspaper className="h-9 w-9" />
          <p className="text-sm text-center">
            Tidak ada berita untuk {selectedTicker.replace(".JK", "")}.
            <br />
            Pastikan <code className="font-mono">NEWS_API_KEY</code> sudah dikonfigurasi di backend.
          </p>
        </div>
      )}

      {/* Article cards */}
      {!loading && news && news.articles.length > 0 && (
        <div className="space-y-3">
          {news.articles.map((article, i) => (
            <article
              key={i}
              className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-4 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-white font-medium leading-snug flex-1">
                  {article.title}
                </p>
                <span
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${SENTIMENT_CLASS[article.sentiment]}`}
                >
                  {SENTIMENT_ICON[article.sentiment]}
                  {article.sentiment}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#5b616e]">
                <span>{article.source}</span>
                <span>·</span>
                <span>
                  {new Date(article.published_at).toLocaleDateString("id-ID", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
