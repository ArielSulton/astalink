export function AllocationChart({ weights }: { weights: { ticker: string; weight: number }[] }) {
  return (
    <ul className="space-y-1">
      {weights.map((w) => (
        <li key={w.ticker} className="flex items-center gap-2">
          <span className="w-16 font-mono">{w.ticker}</span>
          <div className="flex-1 bg-gray-200 h-3 rounded overflow-hidden">
            <div className="bg-blue-500 h-full" style={{ width: `${w.weight * 100}%` }} />
          </div>
          <span className="w-16 text-right tabular-nums">{(w.weight * 100).toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  );
}
