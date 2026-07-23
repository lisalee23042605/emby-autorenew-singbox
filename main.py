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

        # Small sleep to simulate realistic session duration
        time.sleep(2)
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

    success_count = 0
    fail_count = 0

    for i, acc in enumerate(accounts):
        ok = keep_alive_account(acc, i)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    print(f"\n==========================================")
    print(f" Summary: Total {len(accounts)} | Success: {success_count} | Failed: {fail_count}")
    print(f"==========================================")

    if fail_count > 0 and success_count == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
