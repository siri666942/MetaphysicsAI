#!/usr/bin/env bash
# 一键配置 Nginx 反向代理：安装 Nginx、启用站点，使可通过域名直接访问（80 端口）
# 首次在服务器上执行一次即可；之后改代码只需运行 ./deploy.sh
# 使用： DOMAIN=你的域名 ./setup-nginx.sh  或  ./setup-nginx.sh  （默认用配置文件里的域名）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOMAIN="${DOMAIN:-beingecho.tech}"
NGINX_CONF_SOURCE="$PROJECT_ROOT/nginx/beingecho.conf"
NGINX_SSL_SOURCE="$PROJECT_ROOT/nginx/beingecho-ssl.conf"
NGINX_AVAILABLE="/etc/nginx/sites-available/beingecho"
NGINX_ENABLED="/etc/nginx/sites-enabled/beingecho"
NGINX_SSL_AVAILABLE="/etc/nginx/sites-available/beingecho-ssl"

echo "=========================================="
echo "  Nginx 反向代理配置"
echo "=========================================="
echo "  域名: $DOMAIN"
echo "  后端: 127.0.0.1:5000"
echo "=========================================="

# 1. 安装 Nginx（若未安装）
if ! command -v nginx &>/dev/null; then
  echo ""
  echo "[1/4] 安装 Nginx..."
  sudo apt-get update -qq
  sudo apt-get install -y nginx
else
  echo ""
  echo "[1/4] 已安装 Nginx，跳过"
fi

# 2. 安装站点配置（80 + ACME；HTTPS 配置先安装不启用，由 setup-https.sh 启用）
echo ""
echo "[2/4] 安装站点配置..."
sudo sed "s/server_name .*;/server_name $DOMAIN www.$DOMAIN;/" "$NGINX_CONF_SOURCE" > /tmp/beingecho.conf
sudo mv /tmp/beingecho.conf "$NGINX_AVAILABLE"
sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED" 2>/dev/null || true
sudo cp "$NGINX_SSL_SOURCE" "$NGINX_SSL_AVAILABLE"
sudo mkdir -p /var/www/beingecho-acme
sudo chown www-data:www-data /var/www/beingecho-acme 2>/dev/null || true

# 3. 测试配置并重载
echo ""
echo "[3/4] 测试 Nginx 配置..."
sudo nginx -t

echo ""
echo "[4/4] 重载 Nginx..."
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "  配置完成。请确保："
echo "  1. 域名 $DOMAIN 已解析到本机 IP（DNS A 记录）"
echo "  2. 应用已运行：./deploy.sh"
echo "  用户访问： http://$DOMAIN  或  http://www.$DOMAIN"
echo "  启用 HTTPS：执行 backend/scripts/setup-https.sh"
echo "=========================================="
