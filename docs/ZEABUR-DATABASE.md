# Zeabur 部署与数据库持久化说明

本文档说明在 **Zeabur（后端）+ Vercel（前端）** 部署时，如何避免重新部署导致**用户注册、对话记录**丢失。

---

## 一、Zeabur 与数据库相关能力概览

| 能力 | 说明 | 定价/备注 |
|------|------|-----------|
| **Volumes（持久化卷）** | 为某个服务挂载持久目录，重启/重新部署后数据保留 | **$0.20/GB/月**（[官方定价](https://zeabur.com/docs/en-US/billing/pricing)） |
| **Backup / Restore** | 对挂载了 Volume 的服务做备份与恢复 | 在「数据管理」中操作，Developer Plan 含自动备份 |
| **内置数据库服务** | 在项目中添加 MySQL / PostgreSQL 服务（独立于你的 Flask 服务） | 按该服务的 CPU/内存/存储计费，数据在数据库服务内持久化 |

**套餐简要**（仅作参考，以 [Zeabur 定价页](https://zeabur.com/pricing) 为准）：

- **Free Trial**：$0/月，约 $5 额度，仅适合体验。
- **Developer Plan**：约 $5/月，含 $5 额度 + 自动备份，适合个人/小项目。
- **Team Plan**：约 $80/月，更高配额与支持。

---

## 二、推荐方案：用 Volume 持久化 SQLite（当前项目零改库）

当前后端使用 **SQLite**，数据库文件在容器内，**不挂 Volume 时**每次重新部署都会换新容器，**用户和对话数据会丢失**。

### 做法：为 Flask 服务挂载 Volume + 环境变量

1. **在 Zeabur 控制台**
   - 打开你的 **后端服务**（Flask/Python 那一个）。
   - 进入 **「Volumes」** 选项卡。
   - 点击 **「Mount Volumes」**，新增一条挂载：
     - **Volume ID**：例如 `data`（仅作标识）。
     - **Mount Directory**：填 **`/data`**（容器内持久化目录）。

2. **设置环境变量**
   - 在同一服务的 **Variables** 里增加：
     - 键：`DATABASE_PATH`  
     - 值：`/data/chat_history.db`  
   - 这样 SQLite 文件会写在 Volume 挂载的 `/data` 下，重启/重新部署后仍会保留。

3. **重要说明（来自 Zeabur 文档）**
   - 挂载 Volume 后，该目录下**原有内容会被清空**，所以要在**首次挂载、且尚无重要数据时**配置。
   - 启用 Volume 后，该服务**不再支持零停机重启**，每次重启会有一小段停机时间。
   - Volume 计费：约 **$0.20/GB/月**，一个几十 MB 的 SQLite 几乎可忽略。

按上述配置后，**用户注册、对话与消息**都会保存在 `/data/chat_history.db`，重新部署也不会丢。

---

## 三、其他可选方案（避免重新部署丢数据）

### 方案 A：Zeabur 内置 MySQL / PostgreSQL（换库、需改代码）

- 在 Zeabur 同一项目中 **添加一个 MySQL 或 PostgreSQL 服务**（从模板/市场添加即可）。
- Zeabur 会为该服务注入连接相关环境变量（如 `MYSQL_URI`、`POSTGRES_CONNECTION_STRING` 等）。
- 数据保存在**数据库服务**里，与 Flask 是否重新部署无关，不会因重新部署而丢失。
- **代价**：需要把当前项目从 SQLite 改为 MySQL/PostgreSQL（改 `database.py` 与依赖），并配置连接；同时该数据库服务会单独计费（CPU/内存/存储）。

适合：打算长期用 Zeabur、且希望用户数据与应用完全解耦时。

### 方案 B：外部托管数据库（Turso / Neon / PlanetScale 等）

- 使用 [Turso](https://turso.tech/)（基于 SQLite）、[Neon](https://neon.tech/)（PostgreSQL）、[PlanetScale](https://planetscale.com/)（MySQL）等**外部托管数据库**。
- 在 Zeabur 的 Flask 服务里只配置连接串（环境变量），数据全部在第三方，**重新部署不会影响数据**。
- **代价**：同样需要把本项目的 SQLite 改为对应数据库（或兼容接口），并可能产生第三方服务的费用。

### 方案 C：定期备份 Volume 或导出 SQLite 文件

- 若已按「二」挂载 Volume，可在 Zeabur **数据管理 → Backup** 做备份，或通过「File Management」等途径定期把 `/data/chat_history.db` 下载到本地/其他存储。
- 这样即使误删 Volume 或需要迁移，也有备份可恢复。

---

## 四、小结

| 目标 | 建议 |
|------|------|
| **不丢用户注册与对话、且尽量少改代码** | 使用 **Zeabur Volume + `DATABASE_PATH=/data/chat_history.db`**（本文第二节）。 |
| **希望数据与应用完全分离、可接受改库** | 使用 **Zeabur 内置 MySQL/PostgreSQL** 或 **外部托管数据库**（第三节 A/B）。 |
| **定价与额度** | 以 [Zeabur 定价](https://zeabur.com/docs/en-US/billing/pricing) 与 [Plans](https://zeabur.com/docs/en-US/billing/plans) 为准；Volume 约 $0.20/GB/月。 |

本项目已支持通过环境变量 **`DATABASE_PATH`** 指定数据库路径，只需在 Zeabur 上挂载 Volume 并设置该变量即可实现持久化，无需改业务代码。

**官方文档直达**：
- [Volumes（持久化卷）](https://zeabur.com/docs/en-US/data-management/volumes)
- [Pricing（定价）](https://zeabur.com/docs/en-US/billing/pricing)
- [Backup / Restore](https://zeabur.com/docs/en-US/data-management/backup)
