const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("gameBridge", {
  request: (command, payload = {}) =>
    ipcRenderer.invoke("game:request", { command, payload }),
});
