#!/bin/bash
# 使用虚拟环境启动后端服务

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
    
    echo "📦 正在安装依赖..."
    ./venv/bin/pip install -r requirements.txt -q
    echo "✅ 依赖安装完成"
fi

echo "🔮 启动AI+玄学后端服务..."
./venv/bin/python backend/app.py
