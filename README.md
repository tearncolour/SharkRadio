# SharkRadio - RoboMaster 雷达 SDR 客户端

<p align="center">
  <strong>基于 ADI PLUTO SDR 的 RoboMaster 2026 雷达站无线解决方案</strong>
</p>

## ✨ 功能特性

- 🎯 **实时频谱分析** - 433MHz 频段实时 FFT 频谱监控
- 📡 **4-RRC-FSK 解调** - 支持比赛规定的调制协议
- 🖥️ **独立桌面客户端** - 基于 Electron 的跨平台应用
- 🎨 **现代化深色界面** - 毛玻璃效果与动态动画
- 🔌 **模拟模式支持** - 无硬件时可使用模拟数据开发

## 📦 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue3 + TypeScript + Ant Design Vue + ECharts |
| **桌面** | Electron |
| **后端** | Python + FastAPI + WebSocket |
| **SDR** | GNU Radio + PyADI-IIO + ADI PLUTO SDR |

## 🚀 快速开始

### 环境要求

- Ubuntu 22.04+ (推荐) 或其他 Debian 系发行版
- Node.js 18+
- Python 3.10+
- GNU Radio 3.10+ (系统安装)

### 自动安装

```bash
# 运行自动化配置脚本 (需要 sudo 权限)
sudo ./setup_env.sh
```

该脚本将自动完成：
1. 安装系统依赖 (GNU Radio, Node.js, libiio 等)
2. 配置 Python 虚拟环境
3. 安装前后端依赖

### 启动应用

```bash
./start.sh
```

启动后将自动打开 Electron 桌面客户端窗口。

### 手动启动 (可选)

```bash
# 后端
cd backend
source venv/bin/activate  # 如果使用 venv
python3 main.py

# 前端 (新终端)
cd frontend
npm run electron:dev
```

## 📁 项目结构

```
SharkRadio/
├── backend/                  # Python 后端
│   ├── api/                  # WebSocket API
│   ├── sdr/                  # SDR 驱动与信号处理
│   │   ├── pluto_driver.py   # PLUTO SDR 驱动
│   │   ├── demodulator.py    # 4-RRC-FSK 解调器
│   │   └── signal_processor.py # 频谱分析
│   ├── main.py               # 入口文件
│   └── requirements.txt
│
├── frontend/                 # Vue3 前端
│   ├── electron/             # Electron 主进程
│   ├── src/
│   │   ├── components/       # Vue 组件
│   │   ├── composables/      # 组合式函数
│   │   ├── stores/           # Pinia 状态管理
│   │   └── styles/           # 全局样式
│   └── package.json
│
├── setup_env.sh              # 自动化环境配置
├── start.sh                  # 一键启动脚本
└── README.md
```

## 🔧 开发指南

### 前端开发

```bash
cd frontend
npm run dev          # 仅启动 Vite 开发服务器
npm run electron:dev # 启动 Electron 开发模式
npm run electron:build # 构建生产包
```

### 后端开发

```bash
cd backend
python3 main.py      # 启动后端服务 (端口 8000)
```

### 硬件连接

1. 通过 USB 连接 ADI PLUTO SDR
2. 确保 `iio_info -s` 能检测到设备
3. 应用将自动连接 SDR 并开始串流

## ⚠️ 已知问题

- **NumPy 版本**: 系统 GNU Radio 需要 NumPy 1.x，请勿升级到 2.x
- **WebSocket 重连**: 开发模式下 WebSocket 可能频繁重连，这是正常现象
- **Electron 安全警告**: 开发模式下的 CSP 警告在打包后会消失

## 📄 许可证

MIT License © 2026 SharkRadio Team

---

<p align="center">
  为 RoboMaster 2026 机甲大师赛雷达站设计
</p>
