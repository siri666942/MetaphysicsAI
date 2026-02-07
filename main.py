# Zeabur 入口文件 —— 从 backend 目录导入 Flask app
import sys
import os

# 将 backend 目录加入 Python 路径，这样 import 能找到 backend 下的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
