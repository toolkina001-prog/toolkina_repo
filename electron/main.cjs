const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const readline = require("node:readline");

let pythonProcess;
let requestId = 0;
const pendingRequests = new Map();

function startPythonBridge() {
  const executable = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  pythonProcess = spawn(executable, ["-u", "-m", "bottle_game.bridge"], {
    cwd: app.getAppPath(),
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });

  const output = readline.createInterface({ input: pythonProcess.stdout });
  output.on("line", (line) => {
    let response;
    try {
      response = JSON.parse(line);
    } catch (error) {
      console.error("Invalid response from Python game engine:", error);
      return;
    }
    const pending = pendingRequests.get(response.id);
    if (!pending) return;
    pendingRequests.delete(response.id);
    if (response.ok) pending.resolve(response.result);
    else pending.reject(new Error(response.error || "Python game engine error."));
  });

  pythonProcess.stderr.on("data", (chunk) => {
    console.error(`[python] ${chunk.toString().trimEnd()}`);
  });
  pythonProcess.on("error", (error) => rejectPending(error));
  pythonProcess.on("close", (code) => {
    rejectPending(new Error(`Python game engine stopped${code === null ? "" : ` (${code})`}.`));
  });
}

function rejectPending(error) {
  for (const pending of pendingRequests.values()) pending.reject(error);
  pendingRequests.clear();
}

function requestPython(command, payload) {
  if (!pythonProcess || pythonProcess.killed || !pythonProcess.stdin.writable) {
    return Promise.reject(new Error("Python game engine is not running."));
  }
  const id = ++requestId;
  return new Promise((resolve, reject) => {
    pendingRequests.set(id, { resolve, reject });
    pythonProcess.stdin.write(`${JSON.stringify({ id, command, payload })}\n`, (error) => {
      if (!error) return;
      pendingRequests.delete(id);
      reject(error);
    });
  });
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 850,
    minHeight: 620,
    backgroundColor: "#edf4f5",
    title: "Bottle Sort",
    webPreferences: {
      preload: path.join(app.getAppPath(), "electron", "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.loadFile(path.join(app.getAppPath(), "web", "index.html"));
}

app.whenReady().then(() => {
  startPythonBridge();
  ipcMain.handle("game:request", (_event, { command, payload }) =>
    requestPython(command, payload)
  );
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  if (pythonProcess && !pythonProcess.killed) pythonProcess.kill();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
