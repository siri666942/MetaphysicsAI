/**
 * 前端配置文件
 * 部署到生产环境前，请修改这里的 API_BASE 为你的 Railway 后端地址
 */

// 开发环境：本地后端
const DEV_API_BASE = "http://localhost:5000/api";

// 生产环境：Railway 后端地址（请替换为你的实际域名）
// 在 Railway Settings -> Networking -> Public Domain 中获取
const PROD_API_BASE = "https://metaphysicsai-production.up.railway.app/api";

// 自动判断环境
const API_BASE = 
    window.location.hostname === "localhost" || 
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === ""
        ? DEV_API_BASE
        : PROD_API_BASE;
