/**
 * Dev-mode launcher: starts Vite, waits for it, then launches Electron.
 * Assumes the Python backend is already running on port 8000.
 */
import { spawn, type ChildProcess } from "child_process";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(__dirname, "..");
const VITE_PORT = 5173;
const BACKEND_PORT = 8000;

function waitForServer(port: number, label: string): Promise<void> {
  return new Promise((resolve) => {
    const check = () => {
      const req = http.get(`http://localhost:${port}`, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => setTimeout(check, 500));
      req.setTimeout(2000, () => {
        req.destroy();
        setTimeout(check, 500);
      });
    };
    console.log(`Waiting for ${label} on port ${port}...`);
    check();
  });
}

async function main() {
  // Start Vite
  const vite: ChildProcess = spawn("npx", ["vite", "--config", "frontend/vite.config.ts"], {
    cwd: appRoot,
    stdio: "inherit",
    shell: true,
  });

  // Wait for Vite to be ready
  await waitForServer(VITE_PORT, "Vite");
  console.log("Vite is ready.");

  // Check if Python backend is up
  try {
    await waitForBackendWithTimeout();
    console.log("Python backend is ready.");
  } catch {
    console.error(
      "Python backend not found on port 8000. Start it first:\n" +
      "  cd fabric-model-readiness/src && py -m api.server --port 8000"
    );
    vite.kill();
    process.exit(1);
  }

  // Launch Electron
  const electron = spawn(
    "npx",
    ["electron", "."],
    {
      cwd: appRoot,
      stdio: "inherit",
      shell: true,
      env: {
        ...process.env,
        DEV_BACKEND_PORT: String(BACKEND_PORT),
        DEV_VITE_PORT: String(VITE_PORT),
      },
    }
  );

  electron.on("exit", (code) => {
    vite.kill();
    process.exit(code ?? 0);
  });

  process.on("SIGINT", () => {
    electron.kill();
    vite.kill();
  });
}

function waitForBackendWithTimeout(): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("timeout")), 5000);
    const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, (res) => {
      clearTimeout(timeout);
      res.resume();
      resolve();
    });
    req.on("error", () => {
      clearTimeout(timeout);
      reject(new Error("not running"));
    });
  });
}

main();
