# 🎬 Emby 自动保号工具 (GitHub Actions 版)

> 结合 [Auto-Renew-AclClouds](https://github.com/cuooc/Auto-Renew-AclClouds) 的 sing-box 代理转发和 [emby-keeper](https://github.com/emby-keeper/emby-keeper) 的保号逻辑，实现轻量级 GitHub Actions 自动保号。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔄 **每日自动保号** | 北京时间 11:00 自动触发，带随机延迟 0~60 分钟，防止固定时间被检测 |
| 🌐 **代理转发** | 通过 sing-box 支持 VLESS / VMess / Trojan / Hysteria2 / TUIC / AnyTLS / SOCKS5 等协议 |
| 👥 **多账号管理** | 支持同时管理多个 Emby 服务器和账号，依次处理 |
| 🎬 **模拟播放** | 随机选择电影/剧集/视频，从随机位置开始模拟播放约 2 分钟 |
| 📱 **客户端伪装** | 模拟 Fileball / Filebar / Infuse iOS 客户端，随机生成设备名和设备 ID |
| 📬 **Telegram 通知** | 每日保号完成后自动推送结果到 Telegram，成功/失败一目了然 |
| 🧹 **自动清理** | 运行后自动清理旧的工作流记录，仅保留最近一条，保持仓库整洁 |
| 🔒 **安全可靠** | 账号密码通过 GitHub Secrets 加密存储，不会泄露在代码中 |

---

## 🚀 快速开始

### 第一步：Fork 本仓库

点击页面右上角的 **Fork** 按钮，将本仓库 Fork 到你的 GitHub 账号下。

> ⚠️ **建议设为私有仓库**：Fork 后进入 **Settings** → **General** → **Danger Zone** → **Change repository visibility** → 改为 **Private**，避免你的配置信息泄露。

---

### 第二步：设置 Secrets（密钥）

进入你 Fork 后的仓库 → **Settings** → **Secrets and variables** → **Actions** → 点击 **New repository secret**

#### 🔑 `EMBY_ACCOUNTS`（必填）

这是你的 Emby 账号配置，格式为 **JSON 数组**。

**单账号示例：**

```json
[
  {
    "name": "服务器A",
    "url": "https://emby.example.com",
    "username": "your_username",
    "password": "your_password"
  }
]
```

**多账号示例：**

```json
[
  {
    "name": "服务器A",
    "url": "https://emby.example1.com",
    "username": "your_username1",
    "password": "your_password1"
  },
  {
    "name": "服务器B",
    "url": "https://emby.example2.com:8096",
    "username": "your_username2",
    "password": "your_password2"
  }
]
```

**字段说明：**

| 字段 | 是否必填 | 说明 | 示例 |
|------|---------|------|------|
| `name` | 必填 | 服务器备注名（仅用于日志和通知显示） | `"终点站"` |
| `url` | 必填 | Emby 服务器地址（含协议，如有非标准端口需加端口号） | `"https://emby.example.com:8096"` |
| `username` | 必填 | Emby 登录用户名 | `"myuser"` |
| `password` | 必填 | Emby 登录密码 | `"mypass"` |

> ⚠️ **注意 JSON 格式**：最外层必须是 `[ ]` 数组，即使只有一个账号也要用数组包裹。复制粘贴后请检查是否有多余的逗号或缺少引号。

---

#### 🌐 `NODE_LINK`（可选 — 代理节点）

如果你的 Emby 服务器对 IP 有限制（例如仅允许特定地区访问），可以配置代理节点。

**支持的协议格式：**

| 协议 | 链接格式 |
|------|---------|
| VLESS | `vless://uuid@server:port?type=tcp&security=tls...` |
| VMess | `vmess://base64编码的配置...` |
| Trojan | `trojan://password@server:port?...` |
| Hysteria2 | `hysteria2://auth@server:port?...` |
| TUIC | `tuic://uuid:password@server:port?...` |
| SOCKS5 | `socks5://user:pass@server:port` |

> 💡 **不设置此项则使用 GitHub Actions 的 IP 直连。** 如果你的 Emby 服务器没有 IP 限制，可以不配置此项。

---

#### 📬 `TELEGRAM_BOT_TOKEN`（可选 — Telegram 通知）

Telegram Bot 的 Token，用于每日推送保号结果通知。

**获取方式：**

1. 打开 Telegram，搜索 **@BotFather**
2. 发送 `/newbot`，按提示设置 Bot 名称
3. 创建完成后，BotFather 会回复你一个 Token，格式如：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
4. 复制这个 Token，添加为 Secret

---

#### 💬 `TELEGRAM_CHAT_ID`（可选 — Telegram 通知）

你的 Telegram 用户 ID，用于指定通知发送目标。

**获取方式：**

1. 打开 Telegram，搜索 **@userinfobot**
2. 向它发送任意一条消息
3. 它会回复你的用户信息，其中 `Id` 就是你的 Chat ID（一串数字，如 `123456789`）
4. 复制这个数字，添加为 Secret

> 💡 **配置好后，你每天会收到这样的通知：**
> - ✅ 成功：`✅ Emby 保号成功 | 📅 时间: 2025-01-01 11:30:00`
> - ❌ 失败：`❌ Emby 保号失败 | 📅 时间: 2025-01-01 11:30:00 | 请检查日志排查问题`
>
> 如果不配置 Telegram 相关的 Secrets，通知功能会自动跳过，不影响保号正常运行。

---

### 第三步：启用 GitHub Actions

进入你 Fork 后的仓库 → 点击顶部 **Actions** 标签页 → 点击绿色按钮 **I understand my workflows, go ahead and enable them**

---

### 第四步：手动测试一次

1. 进入 **Actions** 标签页
2. 在左侧选择 **Emby-Auto-Renew**
3. 点击右侧 **Run workflow** → 再点 **Run workflow** 确认
4. 等待运行完成，点击运行记录查看日志，确认是否成功

> 💡 **测试时注意**：工作流中有一个 0~60 分钟的随机延迟步骤，首次测试时可能需要等待较长时间。如果想跳过延迟快速测试，可以临时注释掉 `emby-renew.yml` 中的随机延迟步骤。

---

## 📋 工作流详解

### 执行流程

```
⏰ 定时触发 (每天北京时间 11:00)
    │
    ▼
⏳ 随机延迟 0~60 分钟 (防检测)
    │
    ▼
🌐 下载并配置 sing-box 代理 (如设置了 NODE_LINK)
    │
    ▼
🔄 依次处理每个 Emby 账号:
    ├── 📱 生成随机客户端信息 (Fileball/Filebar/Infuse)
    ├── 🔑 登录认证 (用户名 + 密码)
    ├── 🎲 随机选择电影/剧集/视频
    ├── ▶️  上报播放开始
    ├── 🎬 模拟播放约 2 分钟 (每 25~35 秒上报进度)
    ├── ⏹️  上报播放停止
    └── ⏳ 账号间随机间隔 10~30 秒
    │
    ▼
📬 发送 Telegram 通知 (成功/失败)
    │
    ▼
🧹 清理旧的工作流运行记录 (仅保留最近 1 条)
```

### 保号原理

通过 Emby API 模拟真实客户端的完整播放流程，让 Emby 服务器认为你是一个活跃用户：

| 步骤 | API 请求 | 说明 |
|------|---------|------|
| 1. 登录认证 | `POST /emby/Users/AuthenticateByName` | 使用用户名和密码获取 Access Token |
| 2. 获取视频列表 | `GET /emby/Items` | 随机排序获取电影/剧集/视频 |
| 3. 开始播放 | `POST /emby/Sessions/Playing` | 通知服务器客户端开始播放 |
| 4. 进度上报 | `POST /emby/Sessions/Playing/Progress` | 每 25~35 秒上报一次播放进度 |
| 5. 停止播放 | `POST /emby/Sessions/Playing/Stopped` | 通知服务器播放结束 |

在 Emby 服务器的管理后台中，你的账号会显示为正常的播放活动记录。

### 客户端伪装细节

脚本会随机生成以下信息，每次运行都不同：

- **客户端类型**：Fileball / Filebar / Infuse（随机版本号）
- **设备名称**：随机中文名或英文名 + iPhone/iPad（如 `王芳的iPhone`、`Alex's iPad`）
- **设备 ID**：随机 UUID
- **播放起始位置**：视频的随机位置（避免每次从头开始）
- **播放速度**：0.98x ~ 1.02x 微小波动（模拟真实播放）

---

## ⚙️ 自定义配置

### 修改触发时间

编辑 `.github/workflows/emby-renew.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 3 * * *'  # UTC 3:00 = 北京时间 11:00
```

常用时间对照：

| 北京时间 | UTC 时间 | Cron 表达式 |
|---------|---------|------------|
| 每天 08:00 | 00:00 | `0 0 * * *` |
| 每天 11:00 | 03:00 | `0 3 * * *` |
| 每天 14:00 | 06:00 | `0 6 * * *` |
| 每天 20:00 | 12:00 | `0 12 * * *` |
| 每天 23:00 | 15:00 | `0 15 * * *` |

> ⚠️ GitHub Actions 的 cron 使用 **UTC 时区**，北京时间 = UTC + 8 小时。

---

## 📁 文件结构

```
.
├── .github/
│   └── workflows/
│       └── emby-renew.yml    # GitHub Actions 工作流配置
├── emby_keeper.py             # Emby 保号核心 Python 脚本
└── README.md                  # 项目说明文档（本文件）
```

---

## ❓ 常见问题 (FAQ)

### Q: 如何确认保号是否成功？

**方法一**：配置 Telegram 通知（推荐），每天自动推送结果。

**方法二**：进入仓库 → **Actions** 标签页 → 查看最近的运行记录，✅ 为成功，❌ 为失败。点击可查看详细日志。

---

### Q: 运行失败怎么办？

常见失败原因及解决方法：

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 登录失败 | 用户名/密码错误 | 检查 `EMBY_ACCOUNTS` 中的凭据是否正确 |
| 连接超时 | 服务器不可达或被墙 | 配置 `NODE_LINK` 使用代理 |
| 未找到视频 | 服务器媒体库为空 | 确认账号有权限访问媒体库 |
| JSON 解析失败 | Secrets 格式错误 | 检查 JSON 格式，确认引号和逗号正确 |

---

### Q: `.github` 文件夹上传不了怎么办？

通过网页上传时，浏览器会自动忽略以 `.` 开头的隐藏文件夹。解决方法：

**方法一（推荐）**：使用 Git 命令行：
```bash
git add .github/ -f
git commit -m "Add .github folder"
git push origin main
```

**方法二**：在 GitHub 网页上手动创建文件：
1. 点击 **Add file** → **Create new file**
2. 文件名输入 `.github/workflows/emby-renew.yml`（输入 `/` 时会自动创建文件夹）
3. 粘贴 workflow 文件内容并提交

---

### Q: 私有仓库会消耗 Actions 额度吗？

是的，私有仓库每月有 **2000 分钟** 的免费额度。本工作流每次运行约 3~5 分钟（含随机延迟），每月消耗约 90~150 分钟，远低于免费额度。公开仓库则不限制。

---

### Q: 可以手动触发运行吗？

可以。进入 **Actions** → 选择 **Emby-Auto-Renew** → 点击 **Run workflow** → 确认即可。

---

### Q: 如何添加/修改/删除 Emby 账号？

进入仓库 → **Settings** → **Secrets and variables** → **Actions** → 找到 `EMBY_ACCOUNTS` → 点击 **Update** → 修改 JSON 内容并保存。

---

## ⚠️ 注意事项

1. **建议使用私有仓库** — 避免账号密码等敏感信息泄露
2. **GitHub Actions 免费额度** — 公开仓库无限制；私有仓库每月 2000 分钟免费
3. **代理节点** — 如果 Emby 服务器有 IP/地区限制，请务必配置 `NODE_LINK`
4. **不保证 100% 成功** — 如果 Emby 服务器有 Cloudflare 保护或其他反爬措施，可能需要额外处理
5. **合理使用** — 本项目仅供个人保号使用，请勿滥用

---

## 🙏 致谢

- [Auto-Renew-AclClouds](https://github.com/cuooc/Auto-Renew-AclClouds) — sing-box 代理转发方案
- [emby-keeper](https://github.com/emby-keeper/emby-keeper) — Emby 保号 API 逻辑参考

---

## 📝 许可证

MIT License
