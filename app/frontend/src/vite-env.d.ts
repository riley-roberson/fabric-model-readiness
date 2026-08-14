/// <reference types="vite/client" />

/** Exposed by electron/preload.ts through contextBridge. */
interface ElectronAPI {
  getBackendPort: () => Promise<number>;
  selectFolder: () => Promise<string | null>;
  selectFile: () => Promise<string | null>;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
