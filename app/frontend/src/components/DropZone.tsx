import { useState, useCallback, DragEvent } from "react";

declare global {
  interface Window {
    electronAPI?: {
      selectFolder: () => Promise<string | null>;
      selectFile: () => Promise<string | null>;
    };
  }
}

interface DropZoneProps {
  onSelect: (path: string) => void;
  error?: string | null;
}

export function DropZone({ onSelect, error }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [manualPath, setManualPath] = useState("");

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        const filePath = (file as File & { path?: string }).path;
        if (filePath) { onSelect(filePath); return; }
      }
      const textPath = e.dataTransfer.getData("text/plain");
      if (textPath) onSelect(textPath);
    },
    [onSelect]
  );

  const handleBrowseFolder = useCallback(async () => {
    if (window.electronAPI) {
      const path = await window.electronAPI.selectFolder();
      if (path) onSelect(path);
    }
  }, [onSelect]);

  const handleBrowseFile = useCallback(async () => {
    if (window.electronAPI) {
      const path = await window.electronAPI.selectFile();
      if (path) onSelect(path);
    }
  }, [onSelect]);

  return (
    <div className="flex flex-col items-center justify-center h-full">
      {/* Drop area */}
      <div
        className={`
          w-full max-w-lg rounded-2xl border-2 border-dashed
          flex flex-col items-center justify-center
          transition-all duration-200 cursor-pointer
          py-16
          ${isDragOver
            ? "border-blue-400 bg-blue-500/10 scale-[1.02]"
            : "border-slate-600 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/60"
          }
        `}
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onClick={handleBrowseFile}
      >
        {/* Upload icon - explicit size to prevent blowup */}
        <svg
          width="48"
          height="48"
          className={`${isDragOver ? "text-blue-400" : "text-slate-500"} transition-colors mb-4`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
        <p className={`text-base font-semibold ${isDragOver ? "text-blue-300" : "text-slate-300"} transition-colors`}>
          Drop your .pbix or .pbip folder here
        </p>
        <p className="text-sm text-slate-500 mt-1">or click to browse</p>
      </div>

      {/* Browse buttons */}
      <div className="flex gap-3 mt-5">
        <button className="btn-primary text-sm px-5 py-2" onClick={handleBrowseFile}>
          Select .pbix File
        </button>
        <button className="btn-ghost text-sm px-5 py-2" onClick={handleBrowseFolder}>
          Select Folder
        </button>
      </div>

      {/* Manual path */}
      <form
        onSubmit={(e) => { e.preventDefault(); if (manualPath.trim()) onSelect(manualPath.trim()); }}
        className="flex gap-2 mt-4 w-full max-w-lg"
      >
        <input
          type="text"
          value={manualPath}
          onChange={(e) => setManualPath(e.target.value)}
          placeholder="Or paste a file path..."
          className="flex-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-300
                     placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        <button type="submit" className="btn-primary text-sm px-4 py-2" disabled={!manualPath.trim()}>
          Go
        </button>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm w-full max-w-lg">
          {error}
        </div>
      )}
    </div>
  );
}
