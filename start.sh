#!/bin/bash

# RoboMaster 雷达 SDR 客户端启动脚本 (中文版)

echo "=== RoboMaster 雷达 SDR 客户端 ==="
echo "系统启动中..."

# Ensure we are in the script directory
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

# 清理旧进程
echo "正在清理旧进程..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "electron.*SharkRadio" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
# 杀掉占用 8000 端口的进程
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null
# 等待进程完全退出
sleep 2


# 1. Start Backend
echo "[1/2] 正在启动 Python 后端..."
cd backend
# 检查是否存在 venv，如果不存在则假设使用系统 python
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# pip install -r requirements.txt > /dev/null 2>&1
# 确保使用用户安装的 numpy (1.26.4) 而不是可能存在的系统 numpy 2.x
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"
python3 main.py &
BACKEND_PID=$!
echo "后端已启动 (PID: $BACKEND_PID)"
cd ..

# 2. Start Frontend
echo "[2/2] 正在启动前端..."
cd frontend
npm install > /dev/null 2>&1
npm run electron:dev &
FRONTEND_PID=$!
echo "前端已启动 (PID: $FRONTEND_PID)"
cd ..

echo "=== 系统运行中 ==="
echo "前端访问地址: http://localhost:5173"
echo "后端访问地址: http://localhost:8000"
echo "按 Ctrl+C 停止运行"

# Cleanup function
cleanup() {
    echo "正在停止..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

trap cleanup SIGINT

wait
