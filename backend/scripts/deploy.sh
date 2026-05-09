#!/usr/bin/env bash
# beingecho.tech 一键部署：改完功能 → 构建 → 发布，用户可访问网站
# 在 Linux 上使用： chmod +x deploy.sh && ./deploy.sh

set -e

# 项目根目录（Dockerfile 所在目录：脚本在 backend/scripts/，根目录为上两级）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CONTAINER_NAME="beingecho-app"
IMAGE_NAME="beingecho"
PORT="${PORT:-5000}"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
DATA_DIR="${DATA_DIR:-$ROOT/data}"
# 若已把域名解析到本机 IP，可设置 DOMAIN=你的域名，部署成功后会提示用域名访问
DOMAIN="${DOMAIN:-}"

echo "=========================================="
echo "  beingecho.tech 一键部署"
echo "=========================================="
echo "  项目目录: $ROOT"
echo "  容器名:   $CONTAINER_NAME"
echo "  端口:     $PORT"
echo "  环境变量: $ENV_FILE"
echo "  数据目录: $DATA_DIR"
[[ -n "$DOMAIN" ]] && echo "  域名:     $DOMAIN"
echo "=========================================="

# 1. 停止并删除旧容器（若存在）
echo ""
echo "[1/4] 停止并删除旧容器..."
sudo docker stop "$CONTAINER_NAME" 2>/dev/null || true
sudo docker rm "$CONTAINER_NAME" 2>/dev/null || true

# 2. 构建镜像
echo ""
echo "[2/4] 构建 Docker 镜像..."
sudo docker build -t "$IMAGE_NAME" .

# 3. 准备数据目录并启动新容器
echo ""
echo "[3/4] 启动新容器（挂载数据目录，持久化数据库）..."
mkdir -p "$DATA_DIR"
# 容器时区（影响 get_current_time、起卦用「当前时间」等），默认东八区
TZ="${TZ:-Asia/Shanghai}"
if [[ -f "$ENV_FILE" ]]; then
  sudo docker run -d -p "${PORT}:5000" --name "$CONTAINER_NAME" \
    -v "$DATA_DIR:/app/data" \
    -e DATABASE_PATH=/app/data/chat_history.db \
    -e TZ="$TZ" \
    --env-file "$ENV_FILE" \
    "$IMAGE_NAME"
else
  echo "  警告: 未找到 .env，使用空环境变量启动（登录/对话可能不可用）"
  sudo docker run -d -p "${PORT}:5000" --name "$CONTAINER_NAME" \
    -v "$DATA_DIR:/app/data" \
    -e DATABASE_PATH=/app/data/chat_history.db \
    -e TZ="$TZ" \
    -e JWT_SECRET=dev-secret \
    -e SOPHNET_API_KEY=placeholder \
    -e SOPHNET_BASE_URL=https://placeholder \
    "$IMAGE_NAME"
fi

# 4. 等待服务就绪并验证
echo ""
echo "[4/4] 等待服务启动并验证..."
sleep 4
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/" || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  echo ""
  echo "=========================================="
  echo "  部署完成。用户可访问："
  echo "  http://本机IP:${PORT}  或  http://localhost:${PORT}"
  if [[ -n "$DOMAIN" ]]; then
    echo "  或  http://${DOMAIN}:${PORT}  （需已将域名解析到本机 IP）"
  else
    echo "  若用域名访问：先把域名解析到本机 IP，再设 DOMAIN=你的域名 重新执行，或直接访问 http://你的域名:${PORT}"
  fi
  if [[ -f /etc/nginx/sites-enabled/beingecho ]]; then
    echo "  已配置 Nginx：用户通过域名（如 http://你的域名）访问即可看到本次更新。"
    sudo nginx -t &>/dev/null && sudo systemctl reload nginx 2>/dev/null || true
  else
    echo "  用域名直连 80 端口：首次执行 ./setup-nginx.sh，见 DOCKER.md"
  fi
  echo "=========================================="
else
  echo ""
  echo "  警告: 首页返回 HTTP $HTTP_CODE，可能仍在启动或配置有误。"
  echo "  查看日志: sudo docker logs -f $CONTAINER_NAME"
  exit 1
fi
