#!/usr/bin/env python3
"""
Outlook OAuth 认证脚本 - 世纪互联版（21Vianet）
使用 Device Code Flow 完成 Microsoft Graph API 授权
"""
import json
import os
import sys
import requests
import time
import webbrowser
from pathlib import Path

# ========== 配置 ==========
TENANT_ID = os.environ.get("OUTLOOK_TENANT_ID", "")
CLIENT_ID = os.environ.get("OUTLOOK_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("OUTLOOK_CLIENT_SECRET", "")
CREDENTIALS_DIR = Path.home() / ".outlook-microsoft"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"

GRAPH_BASE_URL = "https://microsoftgraph.chinacloudapi.cn"

SCOPES = [
    "offline_access",
    "Mail.ReadWrite",
    "Mail.Send",
    "Calendars.ReadWrite",
    "User.Read",
    "profile",
    "openid"
]


def get_env_client_id():
    """从 .env 文件读取凭证"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
    return (
        os.environ.get("OUTLOOK_CLIENT_ID", ""),
        os.environ.get("OUTLOOK_TENANT_ID", ""),
        os.environ.get("OUTLOOK_CLIENT_SECRET", "")
    )


def ensure_credentials_dir():
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def load_credentials():
    if not CREDENTIALS_FILE.exists():
        return None
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)


def save_credentials(cred):
    ensure_credentials_dir()
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(cred, f, indent=2)


def is_token_valid():
    cred = load_credentials()
    if not cred:
        return False
    # 检查是否过期（提前5分钟）
    return time.time() < (cred.get("expires_at", 0) - 300)


def device_code_flow(client_id, tenant_id):
    """启动设备码授权流程"""
    device_code_url = f"https://login.chinacloudapi.cn/{tenant_id}/oauth2/v2.0/devicecode"

    payload = {
        "client_id": client_id,
        "scope": " ".join(SCOPES)
    }

    print("正在获取设备码...")
    try:
        resp = requests.post(device_code_url, data=payload, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"网络错误: {e}")
        sys.exit(1)

    data = resp.json()
    if "error" in data:
        print(f"错误: {data.get('error_description', data['error'])}")
        sys.exit(1)

    print(f"\n请在浏览器中打开以下网址并输入码：")
    print(f"\n  {data.get('verification_uri')}")
    print(f"\n  设备码: {data.get('user_code')}")
    print(f"\n或直接访问: {data.get('verification_uri')}?user_code={data.get('user_code')}")

    # 自动打开浏览器
    webbrowser.open(data.get('verification_uri') + "?user_code=" + data.get('user_code'))

    # 轮询等待授权
    token_url = f"https://login.chinacloudapi.cn/{tenant_id}/oauth2/v2.0/token"
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 300)

    print(f"\n等待授权（最多 {expires_in} 秒）...", flush=True)

    for _ in range(expires_in // interval):
        time.sleep(interval)
        token_payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "device_code": data["device_code"]
        }

        try:
            token_resp = requests.post(token_url, data=token_payload, timeout=30)
            token_data = token_resp.json()
        except requests.exceptions.RequestException as e:
            print(f"\n轮询请求失败: {e}")
            continue

        if "access_token" in token_data:
            cred = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_at": time.time() + token_data.get("expires_in", 3600),
                "token_type": token_data.get("token_type", "Bearer"),
                "client_id": client_id,
                "tenant_id": tenant_id
            }
            save_credentials(cred)
            print("\n授权成功！凭据已保存。")
            return cred

        error = token_data.get("error", "")
        if error == "authorization_pending":
            print(".", end="", flush=True)
        elif error == "slow_down":
            interval += 1
            print(".", end="", flush=True)
        else:
            print(f"\n授权失败: {token_data.get('error_description', error)}")
            sys.exit(1)

    print("\n授权超时，请重试。")
    sys.exit(1)


def refresh_access_token(client_id, tenant_id, refresh_token):
    """用 refresh_token 刷新 access_token"""
    token_url = f"https://login.chinacloudapi.cn/{tenant_id}/oauth2/v2.0/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "scope": " ".join(SCOPES)
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"刷新失败: {e}")
        return None

    if "access_token" not in data:
        return None

    cred = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_at": time.time() + data.get("expires_in", 3600),
        "token_type": data.get("token_type", "Bearer"),
        "client_id": client_id,
        "tenant_id": tenant_id
    }
    save_credentials(cred)
    return cred


def get_valid_token():
    """获取有效 token，必要时自动刷新"""
    client_id, tenant_id, _ = get_env_client_id()

    if not client_id or not tenant_id:
        print("错误: 请先在 .env 文件中配置 OUTLOOK_CLIENT_ID 和 OUTLOOK_TENANT_ID")
        return None, None, None

    cred = load_credentials()
    if not cred:
        print("错误: 未找到凭据，请先运行 authorize 命令")
        return None, None, None

    if time.time() < (cred.get("expires_at", 0) - 300):
        return cred["access_token"], cred["client_id"], cred["tenant_id"]

    # Token 过期，尝试刷新
    print("Token 已过期或即将过期，正在刷新...")
    new_cred = refresh_access_token(cred["client_id"], cred["tenant_id"], cred.get("refresh_token", ""))
    if new_cred:
        print("Token 刷新成功！")
        return new_cred["access_token"], new_cred["client_id"], new_cred["tenant_id"]

    print("Token 刷新失败，请重新运行 authorize 命令")
    return None, None, None


def test_connection():
    """测试 Graph API 连接"""
    token, client_id, tenant_id = get_valid_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{GRAPH_BASE_URL}/v1.0/me", headers=headers, timeout=30)
        resp.raise_for_status()
        user = resp.json()
        print(f"✅ 连接成功！当前用户: {user.get('displayName', 'N/A')}")
        print(f"   邮箱: {user.get('mail', user.get('userPrincipalName', 'N/A'))}")

        # 检查邮箱
        mail_headers = {"Authorization": f"Bearer {token}"}
        mail_resp = requests.get(f"{GRAPH_BASE_URL}/v1.0/me/mailFolders/inbox", headers=mail_headers, timeout=30)
        if mail_resp.ok:
            print(f"   邮箱统计: ✅ 已连接")
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")


def show_status():
    """显示当前授权状态"""
    client_id, tenant_id, _ = get_env_client_id()
    cred = load_credentials()

    if not cred:
        print("❌ 未授权（无凭据文件）")
        return

    expires_at = cred.get("expires_at", 0)
    remaining = max(0, expires_at - time.time())
    remaining_min = remaining / 60

    print(f"状态: {'✅ 有效' if remaining > 300 else '⚠️ 即将过期'}")
    print(f"Token 剩余时间: {remaining_min:.1f} 分钟")
    print(f"过期时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))}")
    print(f"Client ID: {cred.get('client_id', 'N/A')}")
    print(f"Tenant ID: {cred.get('tenant_id', 'N/A')}")

    if remaining < 300:
        print("\n建议运行 'python3 outlook_auth.py refresh' 刷新 token")


def revoke():
    """撤销授权"""
    global CREDENTIALS_FILE
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        print("✅ 授权已撤销")
    else:
        print("无授权记录")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "authorize":
        client_id, tenant_id, _ = get_env_client_id()
        if not client_id or not tenant_id:
            print("错误: 请确保 .env 文件中包含 OUTLOOK_CLIENT_ID 和 OUTLOOK_TENANT_ID")
            sys.exit(1)
        device_code_flow(client_id, tenant_id)

    elif cmd == "refresh":
        token, client_id, tenant_id = get_valid_token()
        if token:
            print("✅ Token 有效，无需刷新")
        else:
            cred = load_credentials()
            if cred and cred.get("refresh_token"):
                new_cred = refresh_access_token(cred["client_id"], cred["tenant_id"], cred["refresh_token"])
                if new_cred:
                    print("✅ Token 已刷新")
                else:
                    print("❌ 刷新失败")
            else:
                print("❌ 无法刷新，请运行 authorize")

    elif cmd == "test":
        test_connection()

    elif cmd == "status":
        show_status()

    elif cmd == "revoke":
        revoke()

    else:
        print(f"用法: {sys.argv[0]} <authorize|refresh|test|status|revoke>")
