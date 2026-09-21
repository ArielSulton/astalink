"use client";
import { useEffect, useState } from "react";
import { Minus, Newspaper, TrendingDown, TrendingUp } from "lucide-react";
import { api, NewsArticle, NewsResponse } from "@/lib/api-client";
import { PageHeader } from "@/components/ui/page-header";

const TICKERS = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const SENTIMENT_ICON: Record<NewsArticle["sentiment"], React.ReactNode> = {
  positive: <TrendingUp className="h-3 w-3" />,
  neutral: <Minus className="h-3 w-3" />,
  negative: <TrendingDown className="h-3 w-3" />,
};

const SENTIMENT_CLASS: Record<NewsArticle["sentiment"], string> = {
  positive: "text-chart-2 bg-chart-2/10 border-chart-2/20 uppercase tracking-wider text-[9px] font-bold",
  neutral: "text-muted-foreground bg-secondary border-border uppercase tracking-wider text-[9px] font-bold",
  negative: "text-destructive bg-destructive/10 border-destructive/20 uppercase tracking-wider text-[9px] font-bold",
};

export default function NewsPage() {
  const [selectedTicker, setSelectedTicker] = useState("BBCA.JK");
  const [news, setNews] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let stale = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setNews(null);
      api
        .getNews(selectedTicker)
        .then((result) => {
          if (!stale) setNews(result);
        })
        .catch(() => {})
        .finally(() => {
          if (!stale) setLoading(false);
        });
    }, 0);
    return () => {
      stale = true;
      window.clearTimeout(timer);
    };
  }, [selectedTicker]);

  return (
    <div className="mx-auto min-h-screen w-full max-w-4xl space-y-6 bg-background p-4 text-foreground sm:p-6 lg:p-8">
      {/* Header + ticker pills */}
      <PageHeader eyebrow="Sentimen Pasar" title="Berita Pasar" className="border-b border-border pb-5">
        <div className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-secondary p-1">
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedTicker(t)}
              className={`min-h-11 rounded-lg px-3 text-xs font-mono font-bold transition-all duration-200 ${
                selectedTicker === t
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-card"
              }`}
            >
              {t.replace(".JK", "")}
            </button>
          ))}
        </div>
      </PageHeader>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-card animate-pulse ring-1 ring-foreground/10" />
          ))}
        </div>
      )}

      {!loading && news && news.articles.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-muted-foreground bg-card rounded-xl ring-1 ring-foreground/10 p-6">
          <Newspaper className="h-10 w-10 text-chart-2/75" />
          <p className="text-sm text-center leading-relaxed max-w-sm">
            Tidak ada berita untuk <span className="font-bold text-foreground">{selectedTicker.replace(".JK", "")}</span>.
            <br />
            <span className="mt-1 block text-xs text-muted-foreground/60">
              Coba lagi beberapa saat lagi atau pilih saham lain.
            </span>
          </p>
        </div>
      )}

      {!loading && news && news.articles.length > 0 && (
        <div className="space-y-3">
          {news.articles.map((article, i) => (
            <article
              key={i}
              className="rounded-xl bg-card ring-1 ring-foreground/10 hover:ring-foreground/20 hover:bg-secondary/30 p-5 space-y-3 transition-all duration-200 hover:-translate-y-0.5 flex flex-col justify-between"
            >
              <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:gap-4">
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
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-medium text-muted-foreground">
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
