#!/bin/bash

# RoboMaster Radar SDR 自动化环境配置脚本 (中文版)
# 本脚本需要 sudo 权限

set -e

echo "=== RoboMaster 雷达 SDR 环境配置 ==="

# 1. 检查 sudo 权限
if [ "$EUID" -ne 0 ]; then
  echo "请以 root 身份运行 (使用 sudo)"
  exit 1
fi

echo "[1/4] 更新系统软件包..."
apt-get update

# 2. 安装系统依赖
echo "[2/4] 安装系统依赖 (GNU Radio, IIO, Node.js)..."
# 安装 GNU Radio 和相关 SDR 库
apt-get install -y \
    gnuradio \
    gr-osmosdr \
    libiio-utils \
    libad9361-0 \
    libiio0 \
    python3-venv \
    python3-pip \
    curl \
    build-essential

# 安装 Node.js (使用 NodeSource)
if ! command -v node &> /dev/null; then
    echo "正在安装 Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
else
    echo "Node.js 已安装: $(node -v)"
fi

# 3. 配置 Python 环境
echo "[3/4] 配置 Python 后端环境..."
PROJECT_DIR=$(pwd)
BACKEND_DIR="$PROJECT_DIR/backend"

if [ ! -d "$BACKEND_DIR" ]; then
    echo "错误: 未找到 backend 目录: $BACKEND_DIR"
    exit 1
fi

cd "$BACKEND_DIR"

# 清理旧环境
if [ -d "venv" ]; then
    echo "正在移除旧的虚拟环境 venv..."
    rm -rf venv
fi

# 创建特定包含系统包的虚拟环境 (为了使用系统安装的 gnuradio)
echo "正在创建虚拟环境 (--system-site-packages)..."
python3 -m venv --system-site-packages venv

# 激活环境并安装依赖
# 注意: 在脚本中 source 仅对当前 shell 有效，这里直接调用 venv 中的 pip
./venv/bin/pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    echo "正在安装 Python 依赖..."
    ./venv/bin/pip install -r requirements.txt
fi

# 4. 配置前端环境
echo "[4/4] 配置前端环境..."
FRONTEND_DIR="$PROJECT_DIR/frontend"
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "错误: 未找到 frontend 目录: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"
echo "正在安装 Node.js 模块..."
# 此时应该以非 root 用户运行 npm install，避免权限问题
# 获取原始用户
ORIGINAL_USER=$(logname || echo $SUDO_USER)
if [ -n "$ORIGINAL_USER" ]; then
    echo "以用户身份运行 npm install: $ORIGINAL_USER"
    sudo -u "$ORIGINAL_USER" npm install
else
    npm install --unsafe-perm
fi

echo "=== 配置完成! ==="
echo "您现在可以运行 './start.sh' 来启动应用程序。"
