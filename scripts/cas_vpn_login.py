import re
import json
import random
import hashlib
import base64
import requests
from urllib.parse import quote
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ======================== 常量 ========================

CAS_LOGIN_URL = "https://ids.cqytxy.edu.cn/authserver/login"
CHECK_CAPTCHA_URL = "https://ids.cqytxy.edu.cn/authserver/checkNeedCaptcha.htl"

VPN_BASE = "https://vpn.cqytxy.edu.cn"
VPN_CAS_SERVICE = f"{VPN_BASE}/callback/cas/yGrVwtUA"
VPN_CALLBACK_URL = f"{VPN_BASE}/callback/cas/yGrVwtUA"
VPN_AUTH_FINISH_URL = f"{VPN_BASE}/api/access/auth/finish"

AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ======================== AES 加密 ========================

def _random_str(length):
    return "".join(random.choice(AES_CHARS) for _ in range(length))


def _encrypt_password(password, salt):
    if not salt:
        return password
    data = _random_str(64) + password
    key = salt.strip().encode("utf-8")
    iv = _random_str(16).encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


# ======================== 工具 ========================

def _extract(html, field_id):
    for pat in [
        rf'id="{field_id}"[^>]*value="([^"]*)"',
        rf'value="([^"]*)"[^>]*id="{field_id}"',
    ]:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return ""


def _gen_device_id():
    seed = f"zfcheck_{random.random()}"
    return hashlib.md5(seed.encode()).hexdigest()


# ======================== 主流程 ========================

def cas_vpn_login(username, cas_password):

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    # === 步骤1: CAS登录 ===
    cas_url = f"{CAS_LOGIN_URL}?service={quote(VPN_CAS_SERVICE, safe='')}"

    try:
        resp = session.get(cas_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return None, f"CAS页面访问失败: {e}"

    html = resp.text
    salt = _extract(html, "pwdEncryptSalt")
    execution = _extract(html, "execution")
    if not salt or not execution:
        return None, "无法从CAS页面提取salt/execution"

    try:
        cap = session.get(CHECK_CAPTCHA_URL, params={"username": username}, timeout=10)
        if cap.json().get("isNeed", False):
            return None, "CAS登录需要验证码，暂不支持"
    except Exception:
        pass

    encrypted_pwd = _encrypt_password(cas_password, salt)

    form = {
        "username": username,
        "password": encrypted_pwd,
        "captcha": "",
        "rememberMe": "true",
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": "",
        "execution": execution,
    }

    try:
        login_resp = session.post(cas_url, data=form, allow_redirects=False, timeout=15)
    except Exception as e:
        return None, f"CAS登录请求失败: {e}"

    if login_resp.status_code not in (301, 302):
        return None, "CAS登录失败，未获得302重定向（可能密码错误）"

    location = login_resp.headers.get("Location", "")
    ticket_match = re.search(r"ticket=([^&]+)", location)
    if not ticket_match:
        return None, f"CAS重定向中无ticket: {location[:100]}"

    ticket = ticket_match.group(1)
    print(f"[CAS] 认证成功, ticket: {ticket[:30]}...")

    # === 步骤2: 访问VPN callback页面 ===
    callback_url = f"{VPN_CALLBACK_URL}?ticket={ticket}"
    try:
        session.get(callback_url, timeout=15)
    except Exception:
        pass

    # === 步骤3: 调用auth/finish获取webvpn-token ===
    device_id = _gen_device_id()
    auth_data = {
        "externalId": "yGrVwtUA",
        "data": json.dumps({
            "callbackUrl": VPN_CALLBACK_URL,
            "ticket": ticket,
            "deviceId": device_id,
        }),
    }

    try:
        auth_resp = session.post(
            VPN_AUTH_FINISH_URL,
            json=auth_data,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/json",
                "Referer": callback_url,
                "Origin": VPN_BASE,
            },
            timeout=15,
        )
    except Exception as e:
        return None, f"VPN auth/finish请求失败: {e}"

    token_found = any(c.name == "webvpn-token" for c in session.cookies)
    if not token_found:
        return None, f"auth/finish未返回webvpn-token, 状态码: {auth_resp.status_code}"

    print("[VPN] webvpn-token 获取成功")
    return session, ""
