interface ApplyButtonProps {
  acceptedCount: number;
  isApplying: boolean;
  onApply: () => void;
}

export function ApplyButton({ acceptedCount, isApplying, onApply }: ApplyButtonProps) {
  if (acceptedCount === 0) return null;

  return (
    <div className="sticky bottom-0 bg-gradient-to-t from-slate-950 via-slate-950 to-slate-950/80 pt-3 pb-3 mt-3">
      <button
        className="btn w-full py-3 text-sm font-bold rounded-lg
                   bg-gradient-to-r from-emerald-600 to-emerald-500
                   hover:from-emerald-500 hover:to-emerald-400
                   text-white shadow-lg shadow-emerald-600/20
                   focus:ring-emerald-500 focus:ring-2
                   disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={onApply}
        disabled={isApplying}
      >
        {isApplying ? (
          <>
            <svg width="16" height="16" className="animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Applying...
          </>
        ) : (
          <>Apply {acceptedCount} Change{acceptedCount !== 1 ? "s" : ""}</>
        )}
      </button>
    </div>
  );
}
