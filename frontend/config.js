/**
 * 前端配置文件
 * 同源部署（如 Docker 单容器）时用相对路径 /api；跨域时可按需改 PROD_API_BASE
 */
const DEV_API_BASE = "http://localhost:5000/api";
const PROD_API_BASE = "/api";  // 同源部署：相对路径，Docker/自建服务器通用
const API_BASE =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? DEV_API_BASE
        : PROD_API_BASE;
