import { app, BrowserWindow, protocol } from 'electron';
import path from 'path';

// Disable GPU Acceleration for now to avoid potential issues on some linux systems
// app.disableHardwareAcceleration();

let mainWindow: BrowserWindow | undefined;

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    // Dark theme frame
    backgroundColor: '#141414',
    title: 'SharkRadio - RoboMaster Radar Client'
  });

  const isDev = process.env.NODE_ENV === 'development';

  if (isDev) {
    // In dev mode, load from Vite dev server
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load from the built index.html
    // Use relative path handling or custom protocol if needed
    // Typically vite builds to dist/, so we load dist/index.html
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
};

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
