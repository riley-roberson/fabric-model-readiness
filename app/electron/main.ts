import { app, BrowserWindow, ipcMain, dialog } from "electron";
import path from "path";
import { PythonBackend } from "./python";

let mainWindow: BrowserWindow | null = null;
let pythonBackend: PythonBackend | null = null;

const isDev = !app.isPackaged;
const devBackendPort = parseInt(process.env.DEV_BACKEND_PORT || "0", 10);
const devVitePort = parseInt(process.env.DEV_VITE_PORT || "5173", 10);

function createWindow(backendPort: number) {
  mainWindow = new BrowserWindow({
    width: 780,
    height: 540,
    minWidth: 600,
    minHeight: 400,
    title: "Fabric Model AI Readiness",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false, // Required for File.path on drag-and-drop
    },
  });

  if (isDev) {
    mainWindow.loadURL(`http://localhost:${devVitePort}?port=${backendPort}`);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist-frontend/index.html"), {
      query: { port: String(backendPort) },
    });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  let backendPort: number;

  if (devBackendPort > 0) {
    // Dev mode: backend already running externally
    backendPort = devBackendPort;
    console.log(`Using existing backend on port ${backendPort}`);
  } else {
    // Production: spawn Python backend
    pythonBackend = new PythonBackend();
    try {
      backendPort = await pythonBackend.start();
      console.log(`Python backend started on port ${backendPort}`);
    } catch (err) {
      console.error("Failed to start Python backend:", err);
      dialog.showErrorBox(
        "Backend Error",
        `Could not start the analysis backend.\n\n${err}`
      );
      app.quit();
      return;
    }
  }

  createWindow(backendPort);

  // IPC handlers
  ipcMain.handle("get-backend-port", () => backendPort);

  ipcMain.handle("select-folder", async () => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ["openDirectory"],
      title: "Select Semantic Model Folder",
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle("select-file", async () => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ["openFile"],
      title: "Select PBIX File",
      filters: [
        { name: "Power BI Files", extensions: ["pbix"] },
        { name: "All Files", extensions: ["*"] },
      ],
    });
    return result.canceled ? null : result.filePaths[0];
  });
});

app.on("window-all-closed", () => {
  pythonBackend?.stop();
  app.quit();
});

app.on("before-quit", () => {
  pythonBackend?.stop();
});
