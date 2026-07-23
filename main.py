#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emby Auto-Renew & Keep-Alive Script
Supported Device Name: Fixed realistic names (e.g. Lisa's iPhone / Lisa's iPad)
"""

import os
import sys
import json
import time
import requests
import random
from typing import List, Dict, Any

DEFAULT_DEVICE_NAME = "Lisa's iPhone"
DEFAULT_CLIENT_NAME = "Emby for iOS"
DEFAULT_CLIENT_VERSION = "4.8.8.0"

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Emby/4.8.8.0",
    "Mozilla/5.0 (iPad; CPU OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Emby/4.8.8.0"
]


def send_telegram_notification(success_list: List[str], fail_list: List[str], skip_list: List[str]):
    """
    Send keep-alive results summary via Telegram Bot.
    Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment variables.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[TG] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping notification.")
        return

    total = len(success_list) + len(fail_list) + len(skip_list)
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    lines = []
    lines.append("📺 *Emby 自动保号报告*")
    lines.append(f"⏰ {now}")
    lines.append(f"📊 共 {total} 个账号 | ✅ {len(success_list)} | ❌ {len(fail_list)} | ⏭ {len(skip_list)}")
    lines.append("")

    if success_list:
        lines.append("✅ *保号成功:*")
        for name in success_list:
            lines.append(f"  • {name}")
        lines.append("")

    if fail_list:
        lines.append("❌ *保号失败:*")
        for name in fail_list:
            lines.append(f"  • {name}")
        lines.append("")

    if skip_list:
        lines.append("⏭ *已跳过 (已禁用):*")
        for name in skip_list:
            lines.append(f"  • {name}")
        lines.append("")

    if fail_list:
        lines.append("⚠️ 请检查失败账号的服务器地址和密码是否正确")
    else:
        lines.append("🎉 全部保号成功！")

    message = "\n".join(lines)

    try:
        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        res = requests.post(tg_url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=15)
        if res.status_code == 200:
            print("[TG] Telegram notification sent successfully.")
        else:
            print(f"[TG] Failed to send notification, HTTP {res.status_code}: {res.text[:200]}")
    except Exception as e:
        print(f"[TG] Error sending notification: {e}")

def get_accounts() -> List[Dict[str, Any]]:
    """
    Load accounts from environment variables.
    Priority 1: EMBY_ACCOUNTS_JSON (JSON string array passed from CF Worker or Secrets)
    Priority 2: Single account environment variables (EMBY_URL, EMBY_USERNAME, EMBY_PASSWORD)
    """
    accounts_json = os.environ.get("EMBY_ACCOUNTS_JSON")
    if accounts_json:
        try:
            parsed = json.loads(accounts_json)
            if isinstance(parsed, list):
                print(f"[Info] Found {len(parsed)} account(s) in EMBY_ACCOUNTS_JSON.")
                return parsed
            else:
                print("[Warning] EMBY_ACCOUNTS_JSON is not a list format, falling back to legacy ENV.")
        except Exception as e:
            print(f"[Error] Failed to parse EMBY_ACCOUNTS_JSON: {e}")

    # Fallback to single account mode
    emby_url = os.environ.get("EMBY_URL")
    username = os.environ.get("EMBY_USERNAME")
    password = os.environ.get("EMBY_PASSWORD")
    device_name = os.environ.get("EMBY_DEVICE_NAME", DEFAULT_DEVICE_NAME)

    if emby_url and username and password:
        print("[Info] Found single account settings from environment variables.")
        return [{
            "id": "env_single",
            "name": "Emby Server",
            "url": emby_url,
            "username": username,
            "password": password,
            "device_name": device_name,
            "enabled": True
        }]

    print("[Error] No Emby accounts configured!")
    return []

def format_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")

def keep_alive_account(account: Dict[str, Any], index: int) -> bool:
    name = account.get("name", f"Account #{index+1}")
    url = account.get("url")
    username = account.get("username")
    password = account.get("password")
    device_name = account.get("device_name", DEFAULT_DEVICE_NAME).strip() or DEFAULT_DEVICE_NAME
    enabled = account.get("enabled", True)

    if not enabled:
        print(f"\n[Skip] Skipping disabled account [{name}]")
        return True

    if not url or not username or not password:
        print(f"\n[Error] Invalid account data for [{name}]: missing URL, username or password.")
        return False

    base_url = format_url(url)
    device_id = f"Lisa-iOS-{hash(username + base_url) & 0xFFFFFFFF:08x}"
    
    print(f"\n==========================================")
    print(f" Processing Account [{name}]")
    print(f" Target Server : {base_url}")
    print(f" Username      : {username}")
    print(f" Device Name   : {device_name}")
    print(f"==========================================")

    # Prepare Auth Header
    auth_header = (
        f'MediaBrowser Client="{DEFAULT_CLIENT_NAME}", '
        f'Device="{device_name}", '
        f'DeviceId="{device_id}", '
        f'Version="{DEFAULT_CLIENT_VERSION}"'
    )
    
    headers = {
        "X-Emby-Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": random.choice(USER_AGENTS)
    }

    session = requests.Session()
    session.headers.update(headers)

    # Check for Proxy
    if os.environ.get("IS_PROXY") == "true" and os.environ.get("PROXY_SERVER"):
        proxy_url = os.environ.get("PROXY_SERVER")
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        print(f"[Proxy] Using proxy for this request: {proxy_url}")

    # 1. Authenticate by Username / Password
    auth_url = f"{base_url}/emby/Users/AuthenticateByName"
    auth_data = {
        "Username": username,
        "Pw": password
    }

    try:
        res = session.post(auth_url, json=auth_data, timeout=20)
        if res.status_code != 200:
            print(f"[Failed] Authentication failed! HTTP Status: {res.status_code}")
            print(f"[Response] {res.text[:200]}")
            return False

        res_data = res.json()
        access_token = res_data.get("AccessToken")
        user_info = res_data.get("User", {})
        user_id = user_info.get("Id")

        print(f"[Success] Login successful! User ID: {user_id}")
        session.headers.update({"X-Emby-Token": access_token})

        # 2. Get User Views / Items (Simulate app home screen load)
        views_url = f"{base_url}/emby/Users/{user_id}/Views"
        views_res = session.get(views_url, timeout=15)
        if views_res.status_code == 200:
            views_data = views_res.json()
            total_views = len(views_data.get("Items", []))
            print(f"[Keep-Alive] Fetched user views: {total_views} libraries found.")
        else:
            print(f"[Warning] Failed to fetch views, HTTP Status: {views_res.status_code}")

        # 3. Get Recent Items (Simulate browsing activity)
        items_url = f"{base_url}/emby/Users/{user_id}/Items/Latest?Limit=5"
        items_res = session.get(items_url, timeout=15)
        if items_res.status_code == 200:
            latest_items = items_res.json()
            print(f"[Keep-Alive] Browsed latest media items: {len(latest_items)} items fetched.")

        # 4. Report Active Session / Ping
        ping_url = f"{base_url}/emby/Sessions/Capabilities/Full"
        ping_data = {
            "PlayableMediaTypes": ["Audio", "Video"],
            "SupportedCommands": ["Play", "DisplayMessage"],
            "SupportsMediaControl": True
        }
        ping_res = session.post(ping_url, json=ping_data, timeout=10)
        if ping_res.status_code in [200, 204]:
            print(f"[Keep-Alive] Session capabilities reported successfully.")

        # Simulate watching media for 1 to 2 minutes
        watch_duration = random.randint(60, 120)
        print(f"[Keep-Alive] Simulating watching media for {watch_duration} seconds...")
        time.sleep(watch_duration)
        
        print(f"[Done] Account [{name}] keep-alive completed successfully!")
        return True

    except Exception as e:
        print(f"[Exception] Error during keep-alive for [{name}]: {str(e)}")
        return False

def main():
    accounts = get_accounts()
    if not accounts:
        print("[Fatal] No active accounts to process. Exiting.")
        sys.exit(1)

    success_list = []
    fail_list = []
    skip_list = []

    for i, acc in enumerate(accounts):
        name = acc.get("name", f"Account #{i+1}")
        enabled = acc.get("enabled", True)

        if not enabled:
            skip_list.append(name)
            print(f"\n[Skip] Skipping disabled account [{name}]")
            continue

        ok = keep_alive_account(acc, i)
        if ok:
            success_list.append(name)
        else:
            fail_list.append(name)

    total = len(success_list) + len(fail_list) + len(skip_list)
    print(f"\n==========================================")
    print(f" Summary: Total {total} | Success: {len(success_list)} | Failed: {len(fail_list)} | Skipped: {len(skip_list)}")
    print(f"==========================================")

    # Send Telegram notification
    send_telegram_notification(success_list, fail_list, skip_list)

    if len(fail_list) > 0 and len(success_list) == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
