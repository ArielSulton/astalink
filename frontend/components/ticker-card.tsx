"use client";

interface TickerCardProps {
  ticker: string;
  lastClose: number | null;
  priceChangePct: number | null;
  rsi14: number | null;
  selected?: boolean;
  onClick: () => void;
}

export function TickerCard({
  ticker,
  lastClose,
  priceChangePct,
  rsi14,
  selected = false,
  onClick,
}: TickerCardProps) {
  const symbol = ticker.replace(".JK", "");
  const isUp = (priceChangePct ?? 0) >= 0;
  const rsiLabel =
    rsi14 != null ? (rsi14 > 70 ? "OB" : rsi14 < 30 ? "OS" : null) : null;

  return (
    <button
      onClick={onClick}
      type="button"
      className={`rounded-xl p-4 text-left w-full transition-all border ${
        selected
          ? "border-[#0052ff] bg-[#0a1a3a]"
          : "border-[#2a2d36] bg-[#16181c] hover:border-[#0052ff]/50 hover:bg-[#1a1c22]"
      }`}
    >
      <div className="font-mono font-semibold text-white text-sm">{symbol}</div>
      <div className="mt-1 font-mono text-base text-white leading-none">
        {lastClose != null ? (
          `Rp ${lastClose.toLocaleString("id-ID")}`
        ) : (
          <span className="text-[#a8acb3]">—</span>
        )}
      </div>
      <div
        className="font-mono text-xs mt-1"
        style={{ color: isUp ? "#05b169" : "#cf202f" }}
      >
        {priceChangePct != null
          ? `${isUp ? "+" : ""}${priceChangePct.toFixed(2)}%`
          : "—"}
      </div>
      {rsiLabel && (
        <span className="mt-1.5 inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#2a2d36] text-[#a8acb3]">
          {rsiLabel}
        </span>
      )}
    </button>
  );
}
