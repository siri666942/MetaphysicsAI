# 把 beingecho.tech 打成 Docker 的教程

---

## 一、下次执行：全流程命令（从零到跑起来）

按顺序复制执行即可。若某步已做过（例如镜像已构建），可从对应步开始。

### 步骤 0：确认 Docker 已安装（只做一次）

```bash
docker --version
```

若提示 `command not found`，先装：

```bash
sudo apt update && sudo apt install -y docker.io
```

### 步骤 1：进入项目根目录

```bash
cd /root/sites/beingecho.tech
```

**必须**和 `Dockerfile` 在同一目录，否则 `docker build` 会找不到文件。

### 步骤 2：准备环境变量（若还没有 .env）

```bash
# 没有 .env 就建一个空文件，再编辑填入 JWT_SECRET、SOPHNET_API_KEY、SOPHNET_BASE_URL
touch .env
# 编辑：nano .env 或 vim .env
```

没有 `.env` 也可以先跑起来，但登录、对话等会缺配置。

### 步骤 3：构建镜像

```bash
sudo docker build -t beingecho .
```

**发生的事**：Docker 按 `Dockerfile` 在当前目录（`.`）建一层层“快照”，最后打成一个名叫 `beingecho`、标签为 `latest` 的镜像。构建成功后，本机就有一份可重复使用的镜像。

### 步骤 4：后台运行容器

```bash
sudo docker run -d -p 5000:5000 --name beingecho-app --env-file .env beingecho
```

**发生的事**：用镜像 `beingecho` 启动一个**后台**容器，名字叫 `beingecho-app`；容器内服务监听 5000，你本机 5000 会转到容器里；环境变量从 `.env` 读入。

### 步骤 5：验证是否在跑

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/
```

输出 `200` 表示首页正常。浏览器打开：**http://本机IP:5000** 或 **http://localhost:5000**。

---

## 二、参数详解：每条命令在干什么

### 2.1 `docker build -t beingecho .`

| 参数 | 含义 | 实际发生的事 |
|------|------|----------------|
| `build` | 根据 Dockerfile 构建镜像 | 读取当前目录的 Dockerfile，按指令装系统、装依赖、拷代码，生成只读的“镜像”文件 |
| `-t beingecho` | 给镜像起名（tag） | 镜像名叫 `beingecho`，标签默认 `latest`；后面 `docker run beingecho` 就是用这个镜像 |
| `.` | 构建上下文目录 | 把**当前目录**交给 Docker；Dockerfile 里的 `COPY` 都是相对这个目录的，所以必须在项目根目录执行 |

### 2.2 `docker run -d -p 5000:5000 --name beingecho-app --env-file .env beingecho`

| 参数 | 含义 | 实际发生的事 |
|------|------|----------------|
| `run` | 用某个镜像启动一个**新容器** | 从镜像“开机”出一个独立进程空间，在里面跑 CMD（咱们是 gunicorn） |
| `-d` | 后台运行（detach） | 容器在后台跑，终端不占着；不加 `-d` 则前台跑，关终端或 Ctrl+C 容器就停 |
| `-p 5000:5000` | 端口映射 | **左边**是宿主机端口，**右边**是容器内端口；访问本机 `5000` 的流量会转到容器里的 `5000` |
| `--name beingecho-app` | 给容器起名 | 以后用 `docker stop beingecho-app`、`docker logs beingecho-app` 时不用记一长串 ID |
| `--env-file .env` | 从文件读环境变量 | 把 `.env` 里每一行 `KEY=VALUE` 注入到容器里，相当于在容器里 export 了这些变量；应用用 `os.getenv("SOPHNET_API_KEY")` 等就能读到 |
| `beingecho` | 用的镜像名 | 用刚才 `docker build -t beingecho` 建出来的镜像跑这个容器 |

### 2.3 其他常见参数（用到时查）

| 参数 | 含义 | 实际发生的事 |
|------|------|----------------|
| `-e PORT=8000` | 传单个环境变量 | 容器内 `PORT=8000`；可多次写 `-e KEY=VALUE` |
| `-v 宿主机路径:容器内路径` | 挂载目录 | 容器里访问某路径时，实际读写的是你本机目录；删容器数据还在 |
| `--rm` | 退出时自动删容器 | 适合临时跑一把测试；长期后台跑一般不用，方便用名字再 `start` |

---

## 三、常用排查命令（每个都解释在干啥）

### 看容器有没有在跑

```bash
sudo docker ps
```

- **发生的事**：列出当前**正在运行**的容器；能看到名字、镜像、端口映射、状态。
- 若看不到 `beingecho-app`，说明已退出；用 `sudo docker ps -a` 能看到“已退出”的容器。

### 看容器为什么挂了 / 最近日志

```bash
sudo docker logs beingecho-app
```

- **发生的事**：打印该容器里**标准输出 + 标准错误**（即 gunicorn/Flask 打的日志）。
- 容器启动就崩时，这里能看到 Python 报错（例如缺模块、缺环境变量）。

### 实时跟日志（像 tail -f）

```bash
sudo docker logs -f beingecho-app
```

- **发生的事**：持续输出新日志；Ctrl+C 只退出看日志，**不会**停容器。

### 看最近 100 行日志

```bash
sudo docker logs --tail 100 beingecho-app
```

### 停止容器

```bash
sudo docker stop beingecho-app
```

- **发生的事**：给容器里的主进程发“优雅退出”信号，进程结束后容器状态变为“已停止”；容器还在，可以之后 `docker start beingecho-app` 再起来。

### 停止后再次启动（不重新建容器）

```bash
sudo docker start beingecho-app
```

- **发生的事**：用**同一份容器**再跑一遍，之前的 `-p`、`--env-file` 等沿用创建时的设置；不会重新 `docker run`。

### 删除已停止的容器（释放名字）

```bash
sudo docker rm beingecho-app
```

- **发生的事**：删掉这个容器（必须先 `docker stop`）；名字 `beingecho-app` 空出来，下次可以再 `docker run --name beingecho-app ...`。

### 本机端口被谁占用

```bash
sudo ss -tlnp | grep 5000
# 或
sudo lsof -i :5000
```

- **发生的事**：看 5000 端口是哪个进程在听；若已被别的程序占用，要么关掉那个程序，要么换端口如 `-p 8080:5000`。

### 进容器里敲命令（高级排查）

```bash
sudo docker exec -it beingecho-app sh
```

- **发生的事**：在**正在运行**的容器里开一个 shell（`sh`），可以 `ls`、`cat .env`（若没挂载则看不到）、`ps` 等；输入 `exit` 退出，容器继续跑。
- **注意**：镜像若没有 `bash` 就用 `sh`。

### 看镜像占了多少空间

```bash
sudo docker images beingecho
```

---

## 四、一键操作速查（复制即用）

### 一键部署脚本（改完功能到发布全流程）

项目根目录下 `deploy.sh`：从停旧容器 → 构建镜像 → 启动新容器 → 验证，一条命令跑完。

```bash
cd /root/sites/beingecho.tech
./deploy.sh
```

可选环境变量：`PORT=8080` 换端口；`ENV_FILE=/其他路径/.env` 指定 .env；`DOMAIN=你的域名` 部署成功后会提示用域名访问。

**用域名直接访问（推荐）**：
1. **首次**：在服务器上执行一次 `./setup-nginx.sh`（可选 `DOMAIN=你的域名`），会安装 Nginx 并配置反向代理（80 → 本机 5000）。请先把域名解析到本机 IP。
2. **日常**：改完代码后只消执行 `./deploy.sh`，用户通过域名访问即可看到更新；脚本会顺带重载 Nginx（若已配置）。
3. **HTTPS**：在服务器上执行一次 `LETSENCRYPT_EMAIL=你的邮箱 ./backend/scripts/setup-https.sh`，会申请 Let's Encrypt 证书并启用 443，即可用 `https://你的域名` 与 `https://www.你的域名` 访问。证书约 90 天有效，续期：`sudo certbot renew`。
4. 配置文件在 `nginx/beingecho.conf`（80）、`nginx/beingecho-ssl.conf`（443），可自行改 `server_name`。

**仅带端口访问**：不跑 setup-nginx 时，把域名解析到服务器后访问 `http://你的域名:5000` 即可。

**反向代理 / 域名 / Docker / 代码之间的关系**：见 [docs/部署与架构说明.md](docs/部署与架构说明.md)。

### 构建镜像

```bash
cd /root/sites/beingecho.tech
sudo docker build -t beingecho .
```

### 后台运行（推荐）

```bash
sudo docker run -d -p 5000:5000 --name beingecho-app --env-file /root/sites/beingecho.tech/.env beingecho
```

### 前台运行（看启动报错时用）

```bash
sudo docker run --rm -p 5000:5000 --env-file .env beingecho
```

### 验证首页

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5000/
```

### 看日志 → 停止 → 再启动

```bash
sudo docker logs -f beingecho-app   # 看日志，Ctrl+C 退出
sudo docker stop beingecho-app     # 停止
sudo docker start beingecho-app    # 再启动
```

### 持久化数据库（SQLite）时的一次性运行示例

```bash
mkdir -p /root/sites/beingecho.tech/data
sudo docker run -d -p 5000:5000 --name beingecho-app \
  -v /root/sites/beingecho.tech/data:/app/data \
  -e DATABASE_PATH=/app/data/chat_history.db \
  --env-file /root/sites/beingecho.tech/.env beingecho
```

---

## 五、导师大白话：镜像里到底发生了什么？

- **镜像** ≈ 一个“快照好的小系统”：里面已经装好 Python、你的代码和依赖，**没有**把你的 `.env` 打进去（用 `.dockerignore` 排除了）。
- **容器** = 用这个镜像“开机”跑起来的一个进程。`-p 5000:5000` 表示：你访问本机的 5000 端口，就相当于访问容器里的 5000 端口。
- **同源部署**：现在前端页面和接口都在同一个地址（例如 `http://你的服务器:5000`），前端请求用相对路径 `/api`，所以无论你换域名还是换端口，都不用再改前端配置。

---

## 六、业务安全确认

- **公司定制逻辑**：只做了几处“加一点、改一点”的改动，没有删任何业务代码：
  - **Dockerfile**：新建，只负责构建和启动方式；并设置 `PYTHONPATH` 以便 backend 内 import 正常。
  - **backend/app.py**：增加了两条路由（`/` 和 `/<path:path>`）用于同源部署时提供前端；未配置 API key 时用占位符避免启动即崩；所有原有 `/api/*` 接口未动。
  - **frontend/config.js**：生产环境接口改为相对路径 `/api`，Docker/自建服务器通用。
- 原来在 Zeabur/Railway 上“前端单独、后端单独”的部署方式仍然可以保留；只是**同一个项目**现在也可以选择“一个 Docker 容器里前后端一起跑”。

---

## 七、环境变量说明（必看）

建议放在 `.env` 里，用 `--env-file .env` 传给容器（不要提交到 Git）：

| 变量名 | 说明 |
|--------|------|
| `JWT_SECRET` | 登录 Token 的密钥，生产环境务必改掉默认值 |
| `SOPHNET_API_KEY` | 大模型 API Key |
| `SOPHNET_BASE_URL` | 大模型 API 地址 |
| `PORT` | 可选，容器内监听端口，默认 5000 |
| `DATABASE_PATH` | 可选，SQLite 路径；做持久化时设为如 `/app/data/chat_history.db` |

---

## 八、导师锦囊

- 构建时报错 `no such file or directory`：多半是没在**项目根目录**执行 `docker build`（必须和 `Dockerfile` 同级）。
- 运行后浏览器访问不到：先在本机执行 `curl http://localhost:5000`，能通再查防火墙/云安全组是否放了 5000 端口。
- 提示端口被占用：换映射如 `-p 8080:5000`，然后访问 `http://localhost:8080`。
- 容器一起就退：用 `sudo docker logs beingecho-app`（或创建时用的名字）看报错；常见是缺环境变量或 Python 报错。
- 不想把 `.env` 放在当前目录：可用 `--env-file /其他路径/.env`，或用 `-e JWT_SECRET=xxx -e SOPHNET_API_KEY=yyy` 逐个传。
- **「现在几点」显示不对**：应用已固定用东八区。若仍错，多半是**服务器系统时间**不对。在服务器上执行 `date` 查看；若不对，用 `sudo timedatectl set-ntp true` 同步网络时间，或 `sudo timedatectl set-time "2025-03-01 13:00:00"` 手动校正。改完后重启容器或重新 `./backend/scripts/deploy.sh`。
