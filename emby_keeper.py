#!/usr/bin/env python3
"""
Emby 自动保号脚本 (轻量版)
参考 emby-keeper 项目的 API 逻辑，使用 requests 库重写
支持多账号管理、代理转发、模拟播放视频

核心流程：
1. 从环境变量读取 Emby 账号配置 (JSON)
2. 依次登录每个账号
3. 随机选择视频并模拟播放约 2 分钟
4. 上报播放进度，模拟真实客户端行为
"""

import json
import os
import random
import string
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import requests

# ========== 日志工具 ==========

class Logger:
    """简单日志工具，带颜色和前缀"""

    COLORS = {
        "INFO": "\033[92m",    # 绿色
        "WARN": "\033[93m",    # 黄色
        "ERROR": "\033[91m",   # 红色
        "DEBUG": "\033[94m",   # 蓝色
        "RESET": "\033[0m",
    }

    @staticmethod
    def _log(level, server, msg):
        color = Logger.COLORS.get(level, "")
        reset = Logger.COLORS["RESET"]
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{server}] " if server else ""
        print(f"{color}[{ts}] [{level}] {prefix}{msg}{reset}")

    @staticmethod
    def info(msg, server=""):
        Logger._log("INFO", server, msg)

    @staticmethod
    def warn(msg, server=""):
        Logger._log("WARN", server, msg)

    @staticmethod
    def error(msg, server=""):
        Logger._log("ERROR", server, msg)

    @staticmethod
    def debug(msg, server=""):
        Logger._log("DEBUG", server, msg)


log = Logger()

# ========== Emby 客户端模拟 ==========

# 模拟 Fileball / Filebar iOS 客户端
CLIENT_CHOICES = [
    {"client": "Fileball", "version": f"1.3.{random.randint(16, 30)}"},
    {"client": "Filebar", "version": f"1.3.{random.randint(30, 36)}"},
    {"client": "Infuse", "version": f"7.{random.randint(6, 8)}.{random.randint(1, 9)}"},
]

# 中文姓氏用于生成随机设备名
CHINESE_SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
]

CHINESE_NAMES = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋",
    "勇", "军", "杰", "涛", "明", "超", "秀兰", "霞", "平", "刚",
    "桂英", "文", "华", "建华", "建国", "建军", "玉兰", "桂花", "小红", "志强",
]

ENGLISH_NAMES = [
    "James", "Mary", "John", "Linda", "Robert", "Sarah", "Michael", "Jessica",
    "David", "Emily", "Alex", "Emma", "Daniel", "Olivia", "Chris", "Sophia",
    "Kevin", "Hannah", "Tom", "Grace", "Jack", "Lucy", "Ryan", "Lily",
]

DEVICE_TYPES = ["iPhone", "iPad"]


def generate_device_name():
    """生成随机设备名称，模拟真实用户"""
    device_type = random.choice(DEVICE_TYPES)
    pattern = random.choices(
        ["cn_full", "cn_surname", "en_possessive", "en_upper", "en_name_only"],
        weights=[25, 30, 25, 10, 10],
    )[0]

    if pattern == "cn_full":
        return f"{random.choice(CHINESE_SURNAMES)}{random.choice(CHINESE_NAMES)}的{device_type}"
    elif pattern == "cn_surname":
        surname = random.choice(CHINESE_SURNAMES)
        return f"{surname}的{device_type}"
    elif pattern == "en_possessive":
        name = random.choice(ENGLISH_NAMES)
        return f"{name}'s {device_type}"
    elif pattern == "en_upper":
        name = random.choice(ENGLISH_NAMES)
        return f"{name.upper()}{device_type.upper()}"
    else:
        return random.choice(ENGLISH_NAMES)


def generate_client_env():
    """生成客户端环境信息"""
    choice = random.choice(CLIENT_CHOICES)
    device_name = generate_device_name()
    device_id = str(uuid.uuid4()).upper()
    return {
        "client": choice["client"],
        "version": choice["version"],
        "device": device_name,
        "device_id": device_id,
        "useragent": f"{choice['client']}/{choice['version']}",
    }


# ========== Emby API 客户端 ==========

class EmbyClient:
    """Emby API 客户端，处理认证、视频获取和播放模拟"""

    def __init__(self, name, url, username, password, proxy=None):
        self.name = name
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.proxy = proxy
        self.token = None
        self.user_id = None
        self.env = generate_client_env()
        self.session = requests.Session()
        self.session.verify = False

        # 设置代理
        if self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }

        log.info(f"客户端: {self.env['client']} v{self.env['version']}", self.name)
        log.info(f"设备: {self.env['device']}", self.name)

    def _build_auth_header(self):
        """构建 Emby 认证头"""
        parts = {
            "Client": self.env["client"],
            "Device": self.env["device"],
            "DeviceId": self.env["device_id"],
            "Version": self.env["version"],
        }
        auth_str = ",".join([f"{k}={quote(str(v))}" for k, v in parts.items()])
        token_part = f"Token={self.token}" if self.token else "Token="
        run_id = str(uuid.uuid4()).upper()
        return f'MediaBrowser {token_part},Emby UserId={run_id},{auth_str}'

    def _get_headers(self):
        """获取请求头"""
        headers = {
            "User-Agent": self.env["useragent"],
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Emby-Authorization": self._build_auth_header(),
        }
        if self.token:
            headers["X-Emby-Token"] = self.token
        return headers

    def _request(self, method, path, **kwargs):
        """发送 HTTP 请求，带重试逻辑"""
        if path.startswith(("http://", "https://")):
            url = path
        else:
            url = f"{self.url}/{path.lstrip('/')}"

        for attempt in range(3):
            try:
                resp = self.session.request(
                    method, url,
                    headers=self._get_headers(),
                    timeout=30,
                    **kwargs
                )

                if resp.status_code == 401 and attempt < 2:
                    log.warn(f"认证失败，尝试重新登录 (尝试 {attempt + 1}/3)", self.name)
                    if self.login():
                        continue
                    return None

                if resp.status_code in (502, 503, 504):
                    log.warn(f"服务器暂时不可用 ({resp.status_code})，重试中...", self.name)
                    time.sleep(random.uniform(2, 5))
                    continue

                return resp

            except requests.exceptions.ConnectionError as e:
                log.error(f"连接失败: {e}", self.name)
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                continue
            except requests.exceptions.Timeout:
                log.error("请求超时", self.name)
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                continue
            except Exception as e:
                log.error(f"请求异常: {e}", self.name)
                return None

        return None

    def login(self):
        """登录 Emby 服务器"""
        log.info(f"正在登录 {self.url} (用户: {self.username})", self.name)

        payload = {
            "Username": self.username,
            "Pw": self.password,
        }

        resp = self._request(
            "POST",
            "/emby/Users/AuthenticateByName",
            json=payload,
        )

        if resp is None:
            log.error("登录请求失败", self.name)
            return False

        if resp.status_code != 200:
            log.error(f"登录失败，状态码: {resp.status_code}", self.name)
            try:
                log.error(f"响应: {resp.text[:200]}", self.name)
            except Exception:
                pass
            return False

        try:
            data = resp.json()
            self.token = data.get("AccessToken")
            self.user_id = data.get("User", {}).get("Id")

            if not self.token or not self.user_id:
                log.error("登录响应缺少 Token 或 UserId", self.name)
                return False

            user_name = data.get("User", {}).get("Name", self.username)
            log.info(f"✅ 登录成功！用户: {user_name}", self.name)
            return True

        except Exception as e:
            log.error(f"解析登录响应失败: {e}", self.name)
            return False

    def get_random_items(self, media_type="Video", limit=50):
        """获取随机视频列表"""
        params = {
            "IncludeItemTypes": media_type,
            "Recursive": "true",
            "SortBy": "Random",
            "SortOrder": "Ascending",
            "Limit": limit,
            "Fields": "MediaSources,Path,RunTimeTicks",
            "UserId": self.user_id,
        }

        resp = self._request("GET", "/emby/Items", params=params)

        if resp is None or resp.status_code != 200:
            log.warn(f"获取 {media_type} 列表失败", self.name)
            return []

        try:
            data = resp.json()
            items = data.get("Items", [])
            return items
        except Exception as e:
            log.error(f"解析视频列表失败: {e}", self.name)
            return []

    def get_episodes(self, series_id, limit=20):
        """获取剧集的分集列表"""
        params = {
            "ParentId": series_id,
            "Recursive": "true",
            "IncludeItemTypes": "Episode",
            "SortBy": "Random",
            "Limit": limit,
            "Fields": "MediaSources,Path,RunTimeTicks",
            "UserId": self.user_id,
        }

        resp = self._request("GET", "/emby/Items", params=params)

        if resp is None or resp.status_code != 200:
            return []

        try:
            return resp.json().get("Items", [])
        except Exception:
            return []

    def find_playable_item(self):
        """查找一个可播放的视频项目"""
        # 尝试获取电影
        log.info("正在查找可播放的视频...", self.name)

        # 先尝试获取电影
        movies = self.get_random_items("Movie", limit=30)
        if movies:
            # 筛选有媒体源的电影
            playable = [m for m in movies if m.get("MediaSources")]
            if playable:
                item = random.choice(playable)
                log.info(f"🎬 选中电影: {item.get('Name', '未知')}", self.name)
                return item

        # 尝试获取剧集
        episodes = self.get_random_items("Episode", limit=30)
        if episodes:
            playable = [e for e in episodes if e.get("MediaSources")]
            if playable:
                item = random.choice(playable)
                series_name = item.get("SeriesName", "")
                season = item.get("ParentIndexNumber", "?")
                ep = item.get("IndexNumber", "?")
                name = item.get("Name", "未知")
                log.info(f"📺 选中剧集: {series_name} S{season}E{ep} - {name}", self.name)
                return item

        # 最后尝试任何视频类型
        videos = self.get_random_items("Video", limit=30)
        if videos:
            playable = [v for v in videos if v.get("MediaSources")]
            if playable:
                item = random.choice(playable)
                log.info(f"🎞️ 选中视频: {item.get('Name', '未知')}", self.name)
                return item

        log.error("❌ 未找到任何可播放的视频", self.name)
        return None

    def report_playback_start(self, item):
        """上报播放开始"""
        item_id = item.get("Id")
        media_source_id = ""
        if item.get("MediaSources"):
            media_source_id = item["MediaSources"][0].get("Id", "")

        payload = {
            "ItemId": item_id,
            "MediaSourceId": media_source_id,
            "PlaySessionId": str(uuid.uuid4()).replace("-", ""),
            "PlayMethod": "DirectStream",
            "PositionTicks": 0,
            "CanSeek": True,
            "IsPaused": False,
            "IsMuted": False,
            "VolumeLevel": random.randint(60, 100),
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": -1,
        }

        resp = self._request(
            "POST",
            "/emby/Sessions/Playing",
            json=payload,
        )

        if resp and resp.status_code in (200, 204):
            log.info("▶️ 已通知服务器开始播放", self.name)
            return payload.get("PlaySessionId")
        else:
            status = resp.status_code if resp else "无响应"
            log.warn(f"播放开始上报失败 (状态: {status})", self.name)
            return payload.get("PlaySessionId")  # 仍然返回 session id 继续模拟

    def report_playback_progress(self, item, play_session_id, position_ticks, is_paused=False):
        """上报播放进度"""
        item_id = item.get("Id")
        media_source_id = ""
        if item.get("MediaSources"):
            media_source_id = item["MediaSources"][0].get("Id", "")

        payload = {
            "ItemId": item_id,
            "MediaSourceId": media_source_id,
            "PlaySessionId": play_session_id,
            "PlayMethod": "DirectStream",
            "PositionTicks": position_ticks,
            "CanSeek": True,
            "IsPaused": is_paused,
            "IsMuted": False,
            "VolumeLevel": random.randint(60, 100),
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": -1,
            "EventName": "timeupdate",
        }

        resp = self._request(
            "POST",
            "/emby/Sessions/Playing/Progress",
            json=payload,
        )

        if resp and resp.status_code in (200, 204):
            position_seconds = position_ticks // 10_000_000
            log.debug(f"📊 进度更新: {position_seconds}s", self.name)
        else:
            log.debug("进度更新失败（非致命）", self.name)

    def report_playback_stop(self, item, play_session_id, position_ticks):
        """上报播放停止"""
        item_id = item.get("Id")
        media_source_id = ""
        if item.get("MediaSources"):
            media_source_id = item["MediaSources"][0].get("Id", "")

        payload = {
            "ItemId": item_id,
            "MediaSourceId": media_source_id,
            "PlaySessionId": play_session_id,
            "PositionTicks": position_ticks,
        }

        resp = self._request(
            "POST",
            "/emby/Sessions/Playing/Stopped",
            json=payload,
        )

        if resp and resp.status_code in (200, 204):
            log.info("⏹️ 已通知服务器停止播放", self.name)
        else:
            log.warn("播放停止上报失败（非致命）", self.name)

    def simulate_watch(self, duration_seconds=120):
        """
        模拟观看视频
        duration_seconds: 观看时长（秒），默认 120 秒 (2分钟)
        """
        # 查找可播放的视频
        item = self.find_playable_item()
        if not item:
            return False

        item_name = item.get("Name", "未知")
        # 获取视频总时长 (ticks, 1 tick = 100 纳秒)
        total_ticks = item.get("RunTimeTicks", 0)
        total_seconds = total_ticks // 10_000_000 if total_ticks else 0

        if total_seconds > 0:
            log.info(f"视频总时长: {total_seconds // 60}分{total_seconds % 60}秒", self.name)

        # 随机选择一个起始位置（避免总是从头开始）
        if total_seconds > duration_seconds + 60:
            start_seconds = random.randint(0, total_seconds - duration_seconds - 30)
        else:
            start_seconds = 0

        start_ticks = start_seconds * 10_000_000
        log.info(f"从 {start_seconds // 60}分{start_seconds % 60}秒 处开始播放", self.name)

        # 上报播放开始
        play_session_id = self.report_playback_start(item)

        # 模拟播放
        progress_interval = random.randint(25, 35)  # 每 25-35 秒上报一次进度
        elapsed = 0
        current_ticks = start_ticks

        log.info(f"⏳ 开始模拟播放 {duration_seconds} 秒...", self.name)

        while elapsed < duration_seconds:
            sleep_time = min(progress_interval, duration_seconds - elapsed)
            # 添加一些随机性
            sleep_time += random.uniform(-2, 2)
            sleep_time = max(5, sleep_time)

            time.sleep(sleep_time)
            elapsed += sleep_time

            # 模拟真实播放，有时会有轻微的进度波动
            speed_factor = random.uniform(0.98, 1.02)
            current_ticks += int(sleep_time * 10_000_000 * speed_factor)

            # 确保不超过视频总时长
            if total_ticks > 0 and current_ticks >= total_ticks:
                current_ticks = total_ticks - 10_000_000  # 停在结束前 1 秒

            # 上报进度
            self.report_playback_progress(
                item, play_session_id, current_ticks,
                is_paused=False,
            )

            current_seconds = current_ticks // 10_000_000
            remaining = max(0, int(duration_seconds - elapsed))
            log.info(
                f"🎬 [{item_name}] 播放位置: {current_seconds // 60}分{current_seconds % 60}秒"
                f" | 剩余: {remaining}秒",
                self.name
            )

        # 上报播放停止
        self.report_playback_stop(item, play_session_id, current_ticks)

        final_seconds = current_ticks // 10_000_000
        log.info(
            f"✅ 模拟播放完成！观看了约 {int(elapsed)} 秒"
            f" ({item_name}，播放至 {final_seconds // 60}分{final_seconds % 60}秒)",
            self.name
        )
        return True


# ========== 主函数 ==========

def load_accounts():
    """从环境变量加载 Emby 账号配置"""
    accounts_json = os.environ.get("EMBY_ACCOUNTS", "")

    if not accounts_json:
        log.error("未设置 EMBY_ACCOUNTS 环境变量！")
        log.info("请在 GitHub Secrets 中设置 EMBY_ACCOUNTS，格式为 JSON 数组：")
        log.info('[{"name":"服务器名","url":"https://emby.example.com","username":"user","password":"pass"}]')
        return []

    try:
        accounts = json.loads(accounts_json)
        if not isinstance(accounts, list):
            log.error("EMBY_ACCOUNTS 必须是 JSON 数组格式！")
            return []
        return accounts
    except json.JSONDecodeError as e:
        log.error(f"EMBY_ACCOUNTS JSON 解析失败: {e}")
        return []


def get_proxy():
    """获取代理设置"""
    is_proxy = os.environ.get("IS_PROXY", "false").lower() == "true"
    proxy = os.environ.get("PROXY_SERVER", "")

    if is_proxy and proxy:
        log.info(f"🌐 使用代理: {proxy}")
        # requests + pysocks 使用 socks5h:// 可以让 DNS 也走代理
        if proxy.startswith("socks5://"):
            proxy = proxy.replace("socks5://", "socks5h://", 1)
        elif proxy.startswith("socks://"):
            proxy = proxy.replace("socks://", "socks5h://", 1)
        log.info(f"🌐 代理地址 (转换后): {proxy}")
        return proxy
    elif proxy:
        # 有 PROXY_SERVER 但 IS_PROXY 不是 true，可能代理启动失败
        log.warn("🌐 检测到 PROXY_SERVER 但代理状态异常，尝试使用代理...")
        if proxy.startswith("socks5://"):
            proxy = proxy.replace("socks5://", "socks5h://", 1)
        return proxy
    else:
        log.info("🌐 未配置代理，使用直连模式")
        return None


def main():
    """主入口"""
    print("=" * 60)
    print("  Emby 自动保号工具 (GitHub Actions 版)")
    print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 加载配置
    accounts = load_accounts()
    if not accounts:
        sys.exit(1)

    proxy = get_proxy()

    log.info(f"📋 共加载 {len(accounts)} 个 Emby 账号")
    print()

    # 禁用 SSL 警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 处理每个账号
    success_count = 0
    fail_count = 0

    for i, account in enumerate(accounts):
        name = account.get("name", f"服务器{i + 1}")
        url = account.get("url", "")
        username = account.get("username", "")
        password = account.get("password", "")

        if not url or not username:
            log.error(f"账号 #{i + 1} ({name}) 配置不完整，跳过", name)
            fail_count += 1
            continue

        print(f"\n{'─' * 50}")
        log.info(f"🔄 开始处理账号 {i + 1}/{len(accounts)}: {name}", name)
        print(f"{'─' * 50}")

        try:
            client = EmbyClient(
                name=name,
                url=url,
                username=username,
                password=password,
                proxy=proxy,
            )

            # 登录
            if not client.login():
                log.error("登录失败，跳过此账号", name)
                fail_count += 1
                continue

            # 模拟观看 (110-130 秒，增加随机性)
            watch_duration = random.randint(110, 130)
            if client.simulate_watch(duration_seconds=watch_duration):
                success_count += 1
            else:
                log.warn("模拟播放失败", name)
                fail_count += 1

        except Exception as e:
            log.error(f"处理账号时出错: {e}", name)
            fail_count += 1

        # 账号之间随机等待
        if i < len(accounts) - 1:
            wait_time = random.randint(10, 30)
            log.info(f"⏳ 等待 {wait_time} 秒后处理下一个账号...", "")
            time.sleep(wait_time)

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  📊 执行结果汇总")
    print(f"  ✅ 成功: {success_count} 个账号")
    print(f"  ❌ 失败: {fail_count} 个账号")
    print(f"  ⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    if fail_count > 0 and success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
