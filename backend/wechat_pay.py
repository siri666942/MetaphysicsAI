"""
微信支付 APIv3 —— Native 下单、回调解密、查单。
环境变量见文件末尾说明。
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography import x509

API_BASE = "https://api.mch.weixin.qq.com"
NATIVE_PATH = "/v3/pay/transactions/native"
QUERY_PATH_TMPL = "/v3/pay/transactions/out-trade-no/{out_trade_no}"
CERTIFICATES_PATH = "/v3/certificates"

_platform_cert_cache: Dict[str, Any] = {"certs": None, "expires_at": 0.0}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def is_mock_mode() -> bool:
    return _env("WECHAT_PAY_MOCK", "").lower() in ("1", "true", "yes")


def is_configured() -> bool:
    if is_mock_mode():
        return True
    required = [
        _env("WECHAT_PAY_APPID"),
        _env("WECHAT_PAY_MCHID"),
        _env("WECHAT_PAY_CERT_SERIAL"),
        _env("WECHAT_PAY_API_V3_KEY"),
        _env("WECHAT_PAY_NOTIFY_URL"),
    ]
    if not all(required):
        return False
    return _load_merchant_private_key() is not None


def _load_merchant_private_key():
    path = _env("WECHAT_PAY_PRIVATE_KEY_PATH")
    raw = _env("WECHAT_PAY_PRIVATE_KEY")
    pem = None
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            pem = f.read()
    elif raw:
        pem = raw.replace("\\n", "\n")
    if not pem:
        return None
    return serialization.load_pem_private_key(
        pem.encode("utf-8"), password=None, backend=default_backend()
    )


def _build_authorization(method: str, url_path: str, body: str) -> str:
    mchid = _env("WECHAT_PAY_MCHID")
    serial = _env("WECHAT_PAY_CERT_SERIAL")
    private_key = _load_merchant_private_key()
    if not private_key or not mchid or not serial:
        raise RuntimeError("微信支付商户证书未配置完整")

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(signature).decode("ascii")
    token = (
        f'mchid="{mchid}",'
        f'nonce_str="{nonce}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{serial}",'
        f'signature="{sig_b64}"'
    )
    return f"WECHAPAY2-SHA256-RSA2048 {token}"


def _request_v3(method: str, url_path: str, body_dict: Optional[dict] = None) -> Tuple[int, dict]:
    body_str = "" if body_dict is None else json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False)
    auth = _build_authorization(method, url_path, body_str)
    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "beingecho-backend",
    }
    url = f"{API_BASE}{url_path}"
    if method.upper() == "GET":
        r = requests.get(url, headers=headers, timeout=30)
    else:
        r = requests.post(url, data=body_str.encode("utf-8"), headers=headers, timeout=30)
    try:
        data = r.json() if r.text else {}
    except json.JSONDecodeError:
        data = {"_raw": r.text}
    return r.status_code, data


def create_native_order(
    out_trade_no: str, description: str, total_fen: int, notify_url: str
) -> Tuple[bool, str, Optional[str]]:
    """
    返回 (ok, message_or_error, code_url)
    """
    if is_mock_mode():
        return True, "mock", "weixin://wxpay/bizpayurl?pr=MOCK_DEV"

    appid = _env("WECHAT_PAY_APPID")
    mchid = _env("WECHAT_PAY_MCHID")
    if not notify_url:
        notify_url = _env("WECHAT_PAY_NOTIFY_URL")
    body = {
        "appid": appid,
        "mchid": mchid,
        "description": description[:127],
        "out_trade_no": out_trade_no,
        "notify_url": notify_url,
        "amount": {"total": int(total_fen), "currency": "CNY"},
    }
    status, data = _request_v3("POST", NATIVE_PATH, body)
    if status == 200 and data.get("code_url"):
        return True, "ok", data["code_url"]
    err = data.get("message") or data.get("code") or str(data)
    return False, err, None


def _apiv3_key_bytes() -> bytes:
    key = _env("WECHAT_PAY_API_V3_KEY")
    if len(key) != 32:
        raise ValueError("WECHAT_PAY_API_V3_KEY 须为 32 字节字符串")
    return key.encode("utf-8")


def decrypt_callback_resource(resource: dict) -> dict:
    key = _apiv3_key_bytes()
    nonce = resource["nonce"]
    ad = resource.get("associated_data") or ""
    ct = base64.b64decode(resource["ciphertext"])
    aesgcm = AESGCM(key)
    plain = aesgcm.decrypt(nonce.encode("utf-8"), ct, ad.encode("utf-8"))
    return json.loads(plain.decode("utf-8"))


def _decrypt_wechat_cert_blob(blob: dict) -> str:
    """解密 /v3/certificates 返回的 encrypt_certificate"""
    key = _apiv3_key_bytes()
    nonce = blob["nonce"]
    ad = blob.get("associated_data") or ""
    ct = base64.b64decode(blob["ciphertext"])
    aesgcm = AESGCM(key)
    plain = aesgcm.decrypt(nonce.encode("utf-8"), ct, ad.encode("utf-8"))
    return plain.decode("utf-8")


def _get_platform_public_key(serial: str):
    global _platform_cert_cache
    now = time.time()
    if _platform_cert_cache["certs"] and now < _platform_cert_cache["expires_at"]:
        certs = _platform_cert_cache["certs"]
    else:
        status, data = _request_v3("GET", CERTIFICATES_PATH, None)
        if status != 200:
            raise RuntimeError(f"拉取微信平台证书失败: {data}")
        certs = []
        for item in data.get("data", []):
            enc = item.get("encrypt_certificate")
            if not enc:
                continue
            pem = _decrypt_wechat_cert_blob(enc)
            cert = x509.load_pem_x509_certificate(pem.encode("utf-8"), default_backend())
            certs.append((item.get("serial_no"), cert))
        _platform_cert_cache["certs"] = certs
        _platform_cert_cache["expires_at"] = now + 3600 * 11

    for sn, cert in _platform_cert_cache["certs"] or []:
        if sn == serial:
            return cert.public_key()
    raise RuntimeError(f"未找到微信平台证书 serial={serial}")


def verify_notification_signature(
    timestamp: str, nonce: str, body: str, signature_b64: str, serial: str
) -> bool:
    try:
        pubkey = _get_platform_public_key(serial)
    except Exception:
        return False
    message = f"{timestamp}\n{nonce}\n{body}\n"
    try:
        sig = base64.b64decode(signature_b64)
        pubkey.verify(
            sig,
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def query_order_by_out_trade_no(out_trade_no: str) -> Tuple[bool, Optional[dict]]:
    mchid = _env("WECHAT_PAY_MCHID")
    path = f"{QUERY_PATH_TMPL.format(out_trade_no=out_trade_no)}?mchid={mchid}"
    status, data = _request_v3("GET", path, None)
    if status == 200:
        return True, data
    return False, data


"""
.env 配置说明（生产请使用真实商户参数）：

WECHAT_PAY_APPID=           公众号/小程序/开放平台 AppID（与商户号绑定）
WECHAT_PAY_MCHID=           商户号
WECHAT_PAY_CERT_SERIAL=     商户 API 证书序列号
WECHAT_PAY_PRIVATE_KEY_PATH= apiclient_key.pem 路径（或改用 WECHAT_PAY_PRIVATE_KEY 多行 PEM）
WECHAT_PAY_API_V3_KEY=      APIv3 密钥（32 位）
WECHAT_PAY_NOTIFY_URL=      公网 HTTPS 回调地址，如 https://你的域名/api/pay/wechat/notify

开发跳过真实微信（仅本地联调 UI）：
WECHAT_PAY_MOCK=1

未配置上述变量时，下单接口会返回 503；匹配免费次数仍生效。
"""
