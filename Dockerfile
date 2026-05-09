# beingecho.tech —— 单容器：Flask 后端 + 静态前端
# 使用方式见文档 DOCKER.md

FROM python:3.11-slim

# 避免交互式提示（如 tzdata）；默认东八区，run 时可用 -e TZ=xxx 覆盖
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
RUN apt-get update -qq && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 Docker 缓存：代码变了再重装）
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 再复制整份代码
COPY backend/   ./backend/
COPY frontend/   ./frontend/
COPY main.py    ./

# 默认端口（可被 docker run -p 覆盖）
EXPOSE 5000

# 用 gunicorn 跑：工作目录为 backend，模块为 app，便于 import database 等
# PORT 可由环境变量传入（如云平台）
ENV PORT=5000
WORKDIR /app/backend
# SQLite 仅适合单 worker 多线程，否则易 database is locked；timeout 覆盖慢 LLM 请求
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 120 --graceful-timeout 30
