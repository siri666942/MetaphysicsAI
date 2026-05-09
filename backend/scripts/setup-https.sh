#!/usr/bin/env bash
# 申请 Let's Encrypt 证书并启用 HTTPS（443）
# 前置：1. 已执行 setup-nginx.sh  2. 域名 beingecho.tech 与 www.beingecho.tech 已解析到本机
# 使用：LETSENCRYPT_EMAIL=你的邮箱 ./setup-https.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="${DOMAIN:-beingecho.tech}"
EMAIL="${LETSENCRYPT_EMAIL:-}"

echo "=========================================="
echo "  HTTPS 配置（Let's Encrypt）"
echo "=========================================="
echo "  域名: $DOMAIN, www.$DOMAIN"
echo "=========================================="

if [[ -z "$EMAIL" ]]; then
  echo "  请设置邮箱（用于证书通知）：LETSENCRYPT_EMAIL=your@email.com $0"
  exit 1
fi

# 1. 安装 certbot
if ! command -v certbot &>/dev/null; then
  echo ""
  echo "[1/4] 安装 certbot..."
  sudo apt-get update -qq
  sudo apt-get install -y certbot
else
  echo ""
  echo "[1/4] certbot 已安装，跳过"
fi

# 2. 申请证书（webroot 方式，不占 80 端口）
echo ""
echo "[2/4] 申请证书..."
sudo certbot certonly --webroot \
  -w /var/www/beingecho-acme \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --non-interactive --agree-tos -m "$EMAIL"

# 3. 启用 HTTPS 站点（证书路径按当前域名）
echo ""
echo "[3/4] 启用 HTTPS 站点..."
sudo sed "s|/etc/letsencrypt/live/beingecho.tech/|/etc/letsencrypt/live/$DOMAIN/|g" \
  /etc/nginx/sites-available/beingecho-ssl > /tmp/beingecho-ssl.conf
sudo mv /tmp/beingecho-ssl.conf /etc/nginx/sites-available/beingecho-ssl
sudo ln -sf /etc/nginx/sites-available/beingecho-ssl /etc/nginx/sites-enabled/beingecho-ssl 2>/dev/null || true

echo ""
echo "[4/4] 测试并重载 Nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "  HTTPS 已启用。可访问："
echo "  https://$DOMAIN  与  https://www.$DOMAIN"
echo "  证书约 90 天有效，续期：sudo certbot renew"
echo "=========================================="
