# Emby 自动保号与账号管理系统 (Cloudflare Worker 驱动版)

本工具为 Emby 账号自动保号/签到解决方案，现已全面升级：
1. **真实固定设备名**：使用真实 iOS 设备标识（默认 `Lisa's iPhone` / `Lisa's iPad`），避免随机设备名导致的封号风险。
2. **零重复定时调度**：彻底删除了 GitHub Actions 的每日定时任务，改为完全由 Cloudflare Worker 独立触发，解决一天跑两次的重复问题。
3. **Cloudflare Worker 账号管理后台**：内置暗黑风可视化 Web 控制台，支持随时添加、删除、编辑、禁用 Emby 账号，保号数据实时存入 Cloudflare KV 数据库。后续增删账号**无需再次修改 GitHub Secrets**！

---

## 📁 目录结构

```text
.
├── main.py                     # Python 自动保号脚本 (支持批量账号及固定设备名)
├── .github/workflows/renew.yml # GitHub Actions 工作流 (仅保留 repository_dispatch)
├── worker.js                   # Cloudflare Worker 单文件源码 (包含 GUI 后台 + API + Cron)
└── README.md                   # 部署使用指南
```

---

## 🛠️ 第一步：更新 GitHub 仓库文件

1. 将本仓库中的 `main.py` 和 `.github/workflows/renew.yml` 覆盖更新到你的 GitHub 仓库 `lisalee23042605/emby-autorenew-singbox` 中。
2. 提交通告 (Commit & Push)。

---

## ☁️ 第二步：部署 Cloudflare Worker 与 KV 绑定

### 1. 创建 Cloudflare Worker
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)，在左侧菜单点击 **Workers & Pages** -> **Create application** -> **Create Worker**。
2. 命名 Worker（例如 `emby-manager`），点击 **Deploy**。
3. 点击 **Edit code**，将本项目中的 `worker.js` 内容全选复制粘贴进去，点击右上角的 **Save and deploy**。

### 2. 创建并绑定 KV 数据库
1. 在 Cloudflare 左侧菜单点击 **Workers & Pages** -> **KV** -> 点击 **Create a namespace**。
2. Namespace 名称填写 `EMBY_ACCOUNTS_KV`，点击 **Add**。
3. 返回你的 Worker 设置页面 (点击你的 Worker -> **Settings** -> **Variables**)。
4. 找到 **KV Namespace Bindings** 区域，点击 **Add binding**：
   - **Variable name**: `EMBY_KV` (必须完全一致)
   - **KV namespace**: 选择刚刚创建的 `EMBY_ACCOUNTS_KV`
5. 点击 **Save and deploy**。

### 3. 配置定时触发器 (Cron Triggers)
1. 在 Worker 设置页面中，点击 **Triggers** -> **Cron Triggers** -> **Add Cron Trigger**。
2. 设置为你期望的每天运行时间，例如 `0 1 * * *` (即每天 UTC 时间 01:00 运行一次)。
3. 点击 **Save**。

---

## 🔑 第三步：获取 GitHub PAT Token 并登录管理后台

### 1. 生成 GitHub PAT Token
1. 打开 GitHub -> **Settings** -> **Developer Settings** -> **Personal Access Tokens** -> **Tokens (classic)**。
2. 点击 **Generate new token (classic)**。
3. Note 填写 `emby-worker-trigger`，勾选 **`repo`** 完整权限。
4. 生成并复制保存这个 Token (如 `ghp_xxxxxxxxxxxx`)。

### 2. 登录 Web 管理后台配置
1. 在浏览器打开你的 Cloudflare Worker 网址 (例如 `https://emby-manager.xxx.workers.dev`)。
2. 点击右上角 **⚙️ GitHub 设置**：
   - **GitHub 用户名 (Owner)**: `lisalee23042605`
   - **仓库名称 (Repo)**: `emby-autorenew-singbox`
   - **GitHub PAT Token**: 粘贴刚刚生成的 `ghp_xxxx` Token
   - 点击 **保存配置**。
3. 点击右上角 **➕ 添加账号**：
   - 填写你的 Emby 服务器地址、用户名、密码。
   - 模拟设备名默认选 `Lisa's iPhone`。
   - 点击 **保存**。
4. 点击右上角的 **🚀 立即触发保号** 进行联调测试：
   - 页面会提示 `Successfully dispatched GitHub Action`。
   - 去你的 GitHub 仓库 -> **Actions** 标签页查看，即可看到最新的保号任务已完美运行！

---

## 🎉 常见问题

Q: **以后添加或删除 Emby 账号还需要修改 GitHub 吗？**
A: 不需要！以后所有账号的增删改查都在 Cloudflare Worker 网页后台完成，Cloudflare 每天会自动把最新生效的账号列表传给 GitHub Actions 执行保号。

Q: **保号日志在哪看？**
A: 在 GitHub 仓库的 **Actions** 页面点击最新一次由 `repository_dispatch` 触发的运行，点开 `Run Emby Keep-Alive` 步骤即可看到详细日志，日志中设备名均显示为 `Lisa's iPhone`。
