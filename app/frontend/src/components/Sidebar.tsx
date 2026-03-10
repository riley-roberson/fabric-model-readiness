import type { AppScreen } from "@/types/scan";

interface SidebarProps {
  currentScreen: AppScreen;
  hasResults: boolean;
  onNavigate: (screen: AppScreen) => void;
}

const navItems: { screen: AppScreen; label: string; iconPath: string }[] = [
  { screen: "drop", label: "Scan", iconPath: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" },
  { screen: "results", label: "Results", iconPath: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" },
  { screen: "history", label: "History", iconPath: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" },
];

export function Sidebar({ currentScreen, hasResults, onNavigate }: SidebarProps) {
  return (
    <aside className="w-44 bg-slate-950 border-r border-slate-800 flex flex-col">
      <div className="px-4 py-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg width="14" height="14" className="text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
            </svg>
          </div>
          <div className="leading-none">
            <p className="font-bold text-white text-sm">Fabric</p>
            <p className="text-xs text-slate-500">AI Ready</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ screen, label, iconPath }) => {
          const enabled = screen === "results" ? hasResults : true;
          const active = currentScreen === screen;
          return (
            <button
              key={screen}
              disabled={!enabled}
              onClick={() => onNavigate(screen)}
              className={`
                w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2
                transition-colors duration-100
                ${active
                  ? "bg-blue-600/10 text-blue-400 font-semibold"
                  : enabled
                    ? "text-slate-400 hover:bg-slate-800/80 hover:text-slate-200"
                    : "text-slate-700 cursor-not-allowed"
                }
              `}
            >
              <svg width="16" height="16" className="flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
              </svg>
              {label}
            </button>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-700">v0.1.0</p>
      </div>
    </aside>
  );
}
