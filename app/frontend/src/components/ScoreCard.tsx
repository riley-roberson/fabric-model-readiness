import type { ScanSummary } from "@/types/findings";

interface ScoreCardProps {
  score: number;
  rating: string;
  summary: ScanSummary;
}

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-lime-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function barGradient(score: number): string {
  if (score >= 90) return "from-emerald-600 to-emerald-400";
  if (score >= 75) return "from-lime-600 to-lime-400";
  if (score >= 50) return "from-amber-600 to-amber-400";
  return "from-red-600 to-red-400";
}

function ratingBadge(score: number): string {
  if (score >= 90) return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  if (score >= 75) return "bg-lime-500/15 text-lime-400 border-lime-500/30";
  if (score >= 50) return "bg-amber-500/15 text-amber-400 border-amber-500/30";
  return "bg-red-500/15 text-red-400 border-red-500/30";
}

export function ScoreCard({ score, rating, summary }: ScoreCardProps) {
  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-black tabular-nums ${scoreColor(score)}`}>{score}</span>
          <span className="text-sm text-slate-500">/ 100</span>
        </div>
        <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${ratingBadge(score)}`}>
          {rating}
        </span>
      </div>

      <div className="w-full bg-slate-800 rounded-full h-2 mb-4 overflow-hidden">
        <div
          className={`h-2 rounded-full bg-gradient-to-r ${barGradient(score)} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>

      <div className="flex gap-2">
        {[
          { label: "Critical", count: summary.critical, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
          { label: "High", count: summary.high, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20" },
          { label: "Medium", count: summary.medium, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
          { label: "Low", count: summary.low, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
          { label: "Info", count: summary.info, color: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/20" },
        ].map(({ label, count, color, bg, border }) => (
          <div key={label} className={`${bg} ${border} border rounded-lg px-3 py-2 text-center flex-1`}>
            <p className={`text-lg font-bold tabular-nums leading-none ${color}`}>{count}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
