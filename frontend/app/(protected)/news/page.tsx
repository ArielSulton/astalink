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
  positive: "text-emerald-400 bg-emerald-500/10 border-emerald-500/15 uppercase tracking-wider text-[9px] font-bold",
  neutral: "text-muted-foreground bg-secondary border-border uppercase tracking-wider text-[9px] font-bold",
  negative: "text-rose-400 bg-rose-500/10 border-rose-500/15 uppercase tracking-wider text-[9px] font-bold",
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
    <div className="p-8 space-y-6 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground">
      {/* Header + ticker pills */}
      <div className="flex flex-wrap items-center gap-4 justify-between border-b border-border pb-5">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">Market Sentiment</p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">Market News</h1>
        </div>
        <div className="flex gap-1.5 bg-secondary p-1 border border-border rounded-xl">
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedTicker(t)}
              className={`px-3 py-1.5 text-xs rounded-lg font-mono font-bold transition-all duration-200 ${
                selectedTicker === t
                  ? "bg-primary text-primary-foreground shadow-[0_4px_12px_rgba(37,99,235,0.2)]"
                  : "text-muted-foreground hover:text-foreground hover:bg-card"
              }`}
            >
              {t.replace(".JK", "")}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-2xl bg-card animate-pulse border border-border" />
          ))}
        </div>
      )}

      {!loading && news && news.articles.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground bg-card border border-border rounded-2xl p-6">
          <Newspaper className="h-10 w-10 text-primary/75" />
          <p className="text-sm text-center leading-relaxed max-w-sm">
            Tidak ada berita untuk <span className="font-bold text-foreground">{selectedTicker.replace(".JK", "")}</span>.
            <br />
            <span className="text-xs text-muted-foreground/60 mt-1 block">
              Pastikan <code className="font-mono bg-secondary px-1.5 py-0.5 rounded text-[11px] text-foreground">NEWS_API_KEY</code> sudah dikonfigurasi di backend.
            </span>
          </p>
        </div>
      )}

      {!loading && news && news.articles.length > 0 && (
        <div className="space-y-3">
          {news.articles.map((article, i) => (
            <article
              key={i}
              className="rounded-2xl border border-border bg-card hover:border-border/60 hover:bg-secondary/30 p-5 space-y-3 transition-all duration-200 hover:-translate-y-0.5 flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-4">
                <p className="text-sm text-foreground font-bold leading-normal flex-1">
                  {article.title}
                </p>
                <span
                  className={`flex items-center gap-1 px-2.5 py-0.5 rounded-full border shrink-0 ${SENTIMENT_CLASS[article.sentiment]}`}
                >
                  {SENTIMENT_ICON[article.sentiment]}
                  <span className="font-bold font-mono">{article.sentiment}</span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-medium">
                <span className="bg-secondary px-2 py-0.5 rounded text-[9px] font-bold text-foreground uppercase tracking-wider border border-border">{article.source}</span>
                <span>·</span>
                <span className="font-mono">
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
