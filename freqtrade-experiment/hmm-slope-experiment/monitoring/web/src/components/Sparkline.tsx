type Point = { ts: string; total_profit: number };

export function Sparkline({ points, height = 140 }: { points: Point[]; height?: number }) {
  if (points.length < 2) {
    return (
      <div
        className="text-muted text-xs mono flex items-center justify-center border border-dashed border-[var(--color-border)] rounded-md"
        style={{ height }}
      >
        accumulating data…
      </div>
    );
  }

  const ys = points.map((p) => p.total_profit);
  const min = Math.min(...ys, 0);
  const max = Math.max(...ys, 0);
  const range = max - min || 1;
  const w = 1000;
  const h = height;
  const pad = 6;

  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * (w - pad * 2) + pad;
      const y = h - pad - ((p.total_profit - min) / range) * (h - pad * 2);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const zeroY = h - pad - ((0 - min) / range) * (h - pad * 2);
  const last = points[points.length - 1].total_profit;
  const stroke = last >= 0 ? "var(--color-accent)" : "var(--color-loss)";

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none">
      <line
        x1={0}
        x2={w}
        y1={zeroY}
        y2={zeroY}
        stroke="var(--color-border)"
        strokeDasharray="4 4"
        strokeWidth={1}
      />
      <path d={path} fill="none" stroke={stroke} strokeWidth={2} />
    </svg>
  );
}
