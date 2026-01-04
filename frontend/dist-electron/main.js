"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path_1 = __importDefault(require("path"));
// Disable GPU Acceleration for now to avoid potential issues on some linux systems
// app.disableHardwareAcceleration();
let mainWindow;
const createWindow = () => {
    mainWindow = new electron_1.BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            preload: path_1.default.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
        // Dark theme frame
        backgroundColor: '#141414',
        title: 'SharkRadio - RoboMaster Radar Client',
        frame: false, // Remove native frame
        titleBarStyle: 'hidden', // Required for some environments to respect frame: false completely
        autoHideMenuBar: true, // Hide menu bar
    });
    const isDev = process.env.NODE_ENV === 'development';
    if (isDev) {
        // In dev mode, load from Vite dev server
        mainWindow.loadURL('http://localhost:5173');
        // Open DevTools
        mainWindow.webContents.openDevTools();
    }
    else {
        // In production, load from the built index.html
        // Use relative path handling or custom protocol if needed
        // Typically vite builds to dist/, so we load dist/index.html
        mainWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'));
    }
};
electron_1.app.whenReady().then(() => {
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0)
            createWindow();
    });
});
const electron_2 = require("electron");
electron_2.ipcMain.on('window-minimize', () => {
    mainWindow?.minimize();
});
electron_2.ipcMain.on('window-maximize', () => {
    if (mainWindow?.isMaximized()) {
        mainWindow.unmaximize();
    }
    else {
        mainWindow?.maximize();
    }
});
electron_2.ipcMain.on('window-close', () => {
    mainWindow?.close();
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin')
        electron_1.app.quit();
});
