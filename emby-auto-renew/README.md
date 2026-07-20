# Emby 自动保号工具 (GitHub Actions 版)

> 结合 [Auto-Renew-AclClouds](https://github.com/cuooc/Auto-Renew-AclClouds) 的 sing-box 代理转发和 [emby-keeper](https://github.com/emby-keeper/emby-keeper) 的保号逻辑，实现轻量级 GitHub Actions 自动保号。

## ✨ 功能

- 🔄 **每日自动保号** — 北京时间 11:00 自动触发（带随机延迟 0-60 分钟）
- 🌐 **代理转发** — 通过 sing-box 支持 VLESS/VMess/Trojan/Hysteria2/TUIC/AnyTLS/SOCKS5 等协议
- 👥 **多账号管理** — 支持同时管理多个 Emby 服务器和账号
- 🎬 **模拟播放** — 随机选择视频，模拟真实客户端播放约 2 分钟
- 📱 **客户端伪装** — 模拟 Fileball/Filebar/Infuse iOS 客户端，随机设备名和 ID
- 🧹 **自动清理** — 运行后自动清理旧的工作流记录，保持仓库整洁

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角的 **Fork** 按钮，将本仓库 Fork 到你的 GitHub 账号下。

### 2. 设置 Secrets

进入你 Fork 后的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

需要设置以下 Secrets：

#### `EMBY_ACCOUNTS` (必填)

JSON 数组格式，包含所有 Emby 账号信息：

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

> **字段说明：**
> | 字段 | 说明 | 示例 |
> |------|------|------|
> | `name` | 服务器备注名（仅用于日志显示） | `"终点站"` |
> | `url` | Emby 服务器地址（含协议和端口） | `"https://emby.example.com:8096"` |
> | `username` | 登录用户名 | `"myuser"` |
> | `password` | 登录密码 | `"mypass"` |

#### `NODE_LINK` (可选)

代理节点链接，支持以下协议格式：

- `vless://uuid@server:port?...`
- `vmess://base64...`
- `trojan://password@server:port?...`
- `hysteria2://auth@server:port?...`
- `tuic://uuid:password@server:port?...`
- `socks5://user:pass@server:port`

> **不设置此项则使用 GitHub Actions 的 IP 直连。**

### 3. 启用 Actions

进入你 Fork 后的仓库 → **Actions** 标签页 → 点击 **I understand my workflows, go ahead and enable them**

### 4. 手动测试

进入 **Actions** → 选择 **Emby-Auto-Renew** → 点击 **Run workflow** → **Run workflow**

## 📋 工作流说明

### 执行流程

```
定时触发 (北京时间 11:00)
    ↓
随机延迟 0-60 分钟
    ↓
下载并配置 sing-box 代理 (如果设置了 NODE_LINK)
    ↓
依次处理每个 Emby 账号:
    ├── 模拟客户端 (Fileball/Filebar/Infuse)
    ├── 登录认证
    ├── 随机选择电影/剧集/视频
    ├── 模拟播放约 2 分钟 (含进度上报)
    └── 账号间随机间隔 10-30 秒
    ↓
清理旧的工作流运行记录
```

### 保号原理

通过 Emby API 模拟真实客户端的完整播放流程：

1. **登录认证** — `POST /emby/Users/AuthenticateByName`
2. **获取视频** — `GET /emby/Items` (随机排序)
3. **开始播放** — `POST /emby/Sessions/Playing`
4. **进度上报** — `POST /emby/Sessions/Playing/Progress` (每 25-35 秒)
5. **停止播放** — `POST /emby/Sessions/Playing/Stopped`

在 Emby 服务器的管理后台中，你的账号会显示为正常的播放活动。

## ⚠️ 注意事项

1. **GitHub Actions 免费额度** — 公开仓库无限制，私有仓库每月 2000 分钟免费
2. **建议使用私有仓库** — 避免账号信息泄露
3. **代理节点** — 如果 Emby 服务器有 IP 限制，建议配置代理
4. **不保证 100% 成功** — 如果 Emby 服务器有 Cloudflare 保护或其他反爬措施，可能需要额外处理
5. **合理使用** — 本项目仅供个人保号使用，请勿滥用

## 📁 文件结构

```
.
├── .github/
│   └── workflows/
│       └── emby-renew.yml    # GitHub Actions 工作流定义
├── emby_keeper.py             # Emby 保号核心脚本
└── README.md                  # 本文件
```

## 🙏 致谢

- [Auto-Renew-AclClouds](https://github.com/cuooc/Auto-Renew-AclClouds) — sing-box 代理转发方案
- [emby-keeper](https://github.com/emby-keeper/emby-keeper) — Emby 保号 API 逻辑参考

## 📝 许可证

MIT License
