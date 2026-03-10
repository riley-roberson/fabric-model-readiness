import type { AppScreen } from "@/types/scan";

interface NavBarProps {
  currentScreen: AppScreen;
  hasResults: boolean;
  onNavigate: (screen: AppScreen) => void;
}

const navItems: { screen: AppScreen; label: string; description: string; iconPath: string }[] = [
  {
    screen: "drop",
    label: "Scan",
    description: "Analyze a model",
    iconPath: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z",
  },
  {
    screen: "results",
    label: "Results",
    description: "View findings",
    iconPath: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
  },
  {
    screen: "history",
    label: "History",
    description: "Change log",
    iconPath: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

export function NavBar({ currentScreen, hasResults, onNavigate }: NavBarProps) {
  return (
    <div className="flex items-stretch gap-3 px-6 pb-4 pt-2 shrink-0">
      {navItems.map(({ screen, label, description, iconPath }) => {
        const enabled = screen === "results" ? hasResults : true;
        const active = currentScreen === screen;
        return (
          <button
            key={screen}
            disabled={!enabled}
            onClick={() => onNavigate(screen)}
            className={`
              flex-1 flex flex-col items-center justify-center gap-1.5 py-4 rounded-xl border
              transition-all duration-150
              ${active
                ? "bg-blue-600/10 border-blue-500/40 text-blue-400 shadow-lg shadow-blue-500/5"
                : enabled
                  ? "bg-slate-900/80 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 hover:bg-slate-800/80"
                  : "bg-slate-900/30 border-slate-800 text-slate-700 cursor-not-allowed"
              }
            `}
          >
            <svg
              width="20"
              height="20"
              className="shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
            </svg>
            <span className="text-sm font-semibold">{label}</span>
            <span className={`text-xs ${active ? "text-blue-500/70" : "text-slate-600"}`}>
              {description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
