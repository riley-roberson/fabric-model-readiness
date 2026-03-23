import type { ScanSummary } from "../scanner/types";

interface ScoreCardProps {
  score: number;
  rating: string;
  summary: ScanSummary;
}

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-600";
  if (score >= 75) return "text-lime-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

function barGradient(score: number): string {
  if (score >= 90) return "from-emerald-500 to-emerald-400";
  if (score >= 75) return "from-lime-500 to-lime-400";
  if (score >= 50) return "from-amber-500 to-amber-400";
  return "from-red-500 to-red-400";
}

function ratingBadge(score: number): string {
  if (score >= 90) return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (score >= 75) return "bg-lime-50 text-lime-700 border-lime-200";
  if (score >= 50) return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-red-50 text-red-700 border-red-200";
}

export function ScoreCard({ score, rating, summary }: ScoreCardProps) {
  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-black tabular-nums ${scoreColor(score)}`}>{score}</span>
          <span className="text-sm text-gray-400">/ 100</span>
        </div>
        <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${ratingBadge(score)}`}>
          {rating}
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2 mb-4 overflow-hidden">
        <div
          className={`h-2 rounded-full bg-gradient-to-r ${barGradient(score)} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>

      <div className="flex gap-2">
        {([
          { label: "Critical", count: summary.critical, color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
          { label: "High", count: summary.high, color: "text-orange-600", bg: "bg-orange-50", border: "border-orange-200" },
          { label: "Medium", count: summary.medium, color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200" },
          { label: "Low", count: summary.low, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200" },
          { label: "Info", count: summary.info, color: "text-gray-500", bg: "bg-gray-50", border: "border-gray-200" },
        ] as const).map(({ label, count, color, bg, border }) => (
          <div key={label} className={`${bg} ${border} border rounded-lg px-3 py-2 text-center flex-1`}>
            <p className={`text-lg font-bold tabular-nums leading-none ${color}`}>{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
