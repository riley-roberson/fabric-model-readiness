import type { Profile } from "../scanner/types";

interface FolderPickerProps {
  onSelect: (dir: FileSystemDirectoryHandle) => void;
  profile: Profile;
  onProfileChange: (p: Profile) => void;
}

const isSupported = typeof window !== "undefined" && "showDirectoryPicker" in window;

const PROFILE_OPTIONS: { value: Profile; label: string; desc: string }[] = [
  { value: "both", label: "All Checks", desc: "AI + Org standards" },
  { value: "ai", label: "AI Readiness", desc: "Prep for AI only" },
  { value: "org", label: "Org Standards", desc: "Power BI Standards only" },
];

export function FolderPicker({ onSelect, profile, onProfileChange }: FolderPickerProps) {
  const handleClick = async () => {
    try {
      const dir = await window.showDirectoryPicker({ mode: "read" });
      onSelect(dir);
    } catch (err) {
      // User cancelled the picker -- ignore AbortError
      if (err instanceof DOMException && err.name === "AbortError") return;
      console.error("Folder picker error:", err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="card p-8 max-w-md w-full text-center">
        <div className="mx-auto w-14 h-14 rounded-xl bg-brand-emerald/10 border border-brand-emerald/20 flex items-center justify-center mb-5">
          <svg width="28" height="28" className="text-brand-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
          </svg>
        </div>

        <h1 className="text-xl font-bold text-gray-900 mb-2">
          Fabric Model Scout
        </h1>
        <p className="text-sm text-gray-500 mb-6 leading-relaxed">
          Analyze your Power BI semantic model for AI readiness.
          Select a <code className="px-1.5 py-0.5 rounded bg-gray-100 text-brand-emerald text-xs">.SemanticModel</code> folder to begin.
        </p>

        {isSupported ? (
          <>
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-500 mb-2">Linting profile</p>
              <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
                {PROFILE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => onProfileChange(opt.value)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      profile === opt.value
                        ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                    title={opt.desc}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {PROFILE_OPTIONS.find((o) => o.value === profile)?.desc}
              </p>
            </div>
            <button
              className="btn-primary text-sm px-6 py-3 w-full"
              onClick={handleClick}
            >
              Select .SemanticModel Folder
            </button>
          </>
        ) : (
          <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
            <p className="text-sm text-amber-700 font-semibold mb-1">Browser not supported</p>
            <p className="text-xs text-amber-600 leading-relaxed">
              The File System Access API is required.
              Please use <strong>Chrome</strong> or <strong>Edge</strong> on desktop.
            </p>
          </div>
        )}

        <p className="text-xs text-gray-400 mt-4">
          All analysis runs locally in your browser. No data is uploaded.
        </p>
      </div>
    </div>
  );
}
