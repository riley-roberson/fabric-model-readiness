import { spawn, ChildProcess } from "child_process";
import { app } from "electron";
import path from "path";
import http from "http";

const HEALTH_CHECK_INTERVAL = 300;
const HEALTH_CHECK_TIMEOUT = 30_000;

export class PythonBackend {
  private process: ChildProcess | null = null;
  port: number = 0;

  async start(): Promise<number> {
    return new Promise((resolve, reject) => {
      const isDev = !app.isPackaged;

      let command: string;
      let args: string[];

      if (isDev) {
        // In dev mode, run the Python server directly
        // Use "py" on Windows (Python Launcher), fall back to "python"
        command = process.platform === "win32" ? "py" : "python";
        args = ["-m", "api.server", "--port", "0"];
      } else {
        // In production, run the PyInstaller-bundled executable
        const resourcesPath = process.resourcesPath;
        command = path.join(resourcesPath, "backend", "api-server.exe");
        args = ["--port", "0"];
      }

      const cwd = isDev
        ? path.resolve(__dirname, "../../fabric-model-readiness/src")
        : undefined;

      this.process = spawn(command, args, {
        cwd,
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env },
      });

      let portDetected = false;

      this.process.stdout?.on("data", (data: Buffer) => {
        const output = data.toString();
        console.log("[python]", output.trim());

        // Parse the port from the backend's stdout
        const match = output.match(/BACKEND_PORT=(\d+)/);
        if (match && !portDetected) {
          portDetected = true;
          this.port = parseInt(match[1], 10);
          this.waitForHealth().then(() => resolve(this.port)).catch(reject);
        }
      });

      this.process.stderr?.on("data", (data: Buffer) => {
        console.error("[python:err]", data.toString().trim());
      });

      this.process.on("error", (err) => {
        if (!portDetected) {
          reject(new Error(`Failed to spawn Python backend: ${err.message}`));
        }
      });

      this.process.on("exit", (code) => {
        console.log(`Python backend exited with code ${code}`);
        if (!portDetected) {
          reject(new Error(`Python backend exited before starting (code ${code})`));
        }
      });

      // Timeout if we never detect the port
      setTimeout(() => {
        if (!portDetected) {
          this.stop();
          reject(new Error("Timed out waiting for Python backend to report its port"));
        }
      }, HEALTH_CHECK_TIMEOUT);
    });
  }

  private async waitForHealth(): Promise<void> {
    const deadline = Date.now() + HEALTH_CHECK_TIMEOUT;

    while (Date.now() < deadline) {
      try {
        await this.healthCheck();
        return;
      } catch {
        await new Promise((r) => setTimeout(r, HEALTH_CHECK_INTERVAL));
      }
    }
    throw new Error("Health check timed out");
  }

  private healthCheck(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = http.get(
        `http://127.0.0.1:${this.port}/api/health`,
        (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            reject(new Error(`Health check returned ${res.statusCode}`));
          }
        }
      );
      req.on("error", reject);
      req.setTimeout(2000, () => {
        req.destroy();
        reject(new Error("Health check timed out"));
      });
    });
  }

  stop() {
    if (this.process) {
      this.process.kill("SIGTERM");
      this.process = null;
    }
  }
}
