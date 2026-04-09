#!/usr/bin/env python3
"""
腾讯 Cloud Studio 每日签到脚本
自动领取每日机时（2小时/天）
"""

import json
import os
import sys
import argparse
from datetime import datetime
import requests


class CloudStudioSignIn:
    """Cloud Studio 签到类"""

    def __init__(self, cookies: str, xsrf_token: str = "", timeout: int = 30):
        """
        初始化签到类

        Args:
            cookies: Cloud Studio 完整 Cookie 字符串
                     格式: cloudstudio-session=xxx; cloudstudio-session-team=wx
            xsrf_token: XSRF Token (从浏览器开发者工具获取)
            timeout: 请求超时时间(秒)
        """
        self.cookies = cookies.strip()
        self.timeout = timeout
        self.session = requests.Session()
        # 解析 cookies 到 session 的 cookie jar
        self._parse_cookies_to_session(self.cookies)
        # XSRF Token
        self._csrf_token = xsrf_token.strip()
        # 设置请求头
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
            "Referer": "https://cloudstudio.net/user-center",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "X-XSRF-TOKEN": self._csrf_token,
        })

        # Cloud Studio API 端点
        self.api_base = "https://cloudstudio.net"
        # 签到 API (2025Q3 活动)
        self.signin_endpoint = "/api/billing/activityTask/SIGN_IN_2025Q3"
        # 状态查询参数
        self.status_param = "?lastRecord=true"

    def _extract_cookie_value(self, cookie_string: str, name: str) -> str:
        """从 Cookie 字符串中提取指定名称的值"""
        for part in cookie_string.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                if key.strip() == name:
                    return value.strip()
        return ""

    def _parse_cookies_to_session(self, cookie_string: str) -> None:
        """将 Cookie 字符串解析到 session 的 cookie jar"""
        print(f"解析 Cookie 字符串: {cookie_string[:50]}...")
        for part in cookie_string.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    self.session.cookies.set(key, value)
                    print(f"  添加 Cookie: {key} = {value[:30]}...")
        print(f"共 {len(list(self.session.cookies))} 个 Cookie")

    def _get_csrf_token(self) -> str:
        """获取 XSRF Token（已通过构造函数传入）"""
        return self._csrf_token

    def get_user_info(self) -> dict:
        """获取用户信息"""
        url = f"{self.api_base}/api/user/info"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"获取用户信息失败: {e}")
            return {}

    def claim_daily_reward(self) -> dict:
        """
        领取每日机时 (2025Q3 活动)

        Returns:
            dict: 签到结果
        """
        # 先获取 CSRF Token
        csrf_token = self._get_csrf_token()
        if csrf_token:
            self.session.headers["X-XSRF-TOKEN"] = csrf_token

        # GET /api/billing/activityTask/SIGN_IN_2025Q3 (不带 lastRecord 参数，触发签到)
        url = f"{self.api_base}{self.signin_endpoint}"

        print(f"尝试签到: GET {url}")
        if csrf_token:
            print(f"XSRF Token: {csrf_token[:10]}...")

        # 打印 Cookie jar 中的 Cookie
        jar_cookies = "; ".join(f"{c.name}={c.value[:20] if c.value else 'None'}..."
                                for c in self.session.cookies)
        print(f"Cookie Jar: {jar_cookies}")

        try:
            resp = self.session.get(url, timeout=self.timeout)
            print(f"响应状态: {resp.status_code}")
            print(f"响应内容: {resp.text[:1000]}")
            resp.raise_for_status()
            result = resp.json()
            return self._parse_signin_result(result)
        except requests.RequestException as e:
            return {"success": False, "message": f"签到请求失败: {e}"}

    def check_signin_status(self) -> dict:
        """
        检查今日签到状态

        Returns:
            dict: 签到状态
        """
        # 先获取 CSRF Token
        csrf_token = self._get_csrf_token()
        if csrf_token:
            self.session.headers["X-XSRF-TOKEN"] = csrf_token

        # GET /api/billing/activityTask/SIGN_IN_2025Q3?lastRecord=true
        url = f"{self.api_base}{self.signin_endpoint}{self.status_param}"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            print(f"状态查询响应: {resp.status_code} - {resp.text[:1000]}")
            resp.raise_for_status()
            data = resp.json()
            return self._parse_status_result(data)
        except requests.RequestException as e:
            return {"claimed": None, "message": f"检查状态失败: {e}"}

    def _parse_signin_result(self, response: dict) -> dict:
        """解析签到响应"""
        # 响应格式:
        # {"code": 0, "msg": "Success", "data": {"taskId": "SIGN_IN_2025Q3", "records": [...]}}
        # records[0]: {"status": "REWARDED", "rewardNum": 200000000, "rewardType": "INSTANCE_HOUR", ...}
        code = response.get("code", -1)
        msg = response.get("msg", response.get("message", ""))
        data = response.get("data") or {}
        records = data.get("records") or []

        if code == 0 and records:
            record = records[0]
            status = record.get("status", "")
            reward_num = record.get("rewardNum", 0)
            reward_type = record.get("rewardType", "")
            reward_expires = record.get("rewardExpires", 0)

            # 奖励数值通常是毫秒或特定单位，转换为小时
            if reward_type == "INSTANCE_HOUR":
                # rewardNum 可能是 200000000 (200小时) 或其他值
                hours = reward_num
            else:
                hours = reward_num

            return {
                "success": True,
                "message": f"签到成功",
                "status": status,
                "hours": hours,
                "reward_type": reward_type,
                "reward_expires_days": reward_expires,
            }
        elif code == 0 and not records:
            # 可能已签到或无需签到
            return {
                "success": True,
                "message": msg or "签到完成",
                "hours": 0,
            }
        else:
            return {
                "success": False,
                "message": msg or response.get("message", "签到失败"),
                "code": code,
            }

    def _parse_status_result(self, response: dict) -> dict:
        """解析状态查询响应"""
        # GET /api/billing/activityTask/SIGN_IN_2025Q3?lastRecord=true
        # 响应格式: {"code": 0, "data": {"taskId": "SIGN_IN_2025Q3", "records": [...]}}
        # records[0]: {"status": "REWARDED", "rewardNum": 200000000, ...}
        data = response.get("data") or {}
        records = data.get("records") or {}

        # records 是数组，检查今日是否已签到 (status == "REWARDED")
        claimed = False
        reward_info = {}
        if records:
            record = records[0] if isinstance(records, list) else records
            status = record.get("status", "")
            claimed = status == "REWARDED"
            if claimed:
                reward_info = {
                    "hours": record.get("rewardNum", 0),
                    "reward_type": record.get("rewardType", ""),
                    "reward_expires_days": record.get("rewardExpires", 0),
                    "reward_time": record.get("rewardTime", ""),
                }

        return {
            "claimed": claimed,
            "reward_info": reward_info,
            "message": "查询成功" if response.get("code") == 0 else f"查询失败: {response.get('msg') or response.get('message')}",
        }


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    if not os.path.exists(config_path):
        print(f"配置文件 {config_path} 不存在，使用环境变量")
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_notification(message: str, config: dict) -> None:
    """
    发送通知

    支持的渠道:
    - TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
    - BARK_KEY
    - SERVERCHAN_KEY (Server酱)
    """
    # Telegram 通知
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("telegram", {}).get("bot_token")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("telegram", {}).get("chat_id")

    if telegram_token and telegram_chat_id:
        try:
            tg_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            requests.post(tg_url, json={
                "chat_id": telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            }, timeout=10)
            print("Telegram 通知已发送")
        except requests.RequestException as e:
            print(f"Telegram 通知发送失败: {e}")

    # Bark 通知
    bark_key = os.environ.get("BARK_KEY") or config.get("bark", {}).get("key")
    if bark_key:
        try:
            bark_url = f"https://api.day.app/{bark_key}/Cloud%20Studio%20签到/{message}"
            requests.get(bark_url, timeout=10)
            print("Bark 通知已发送")
        except requests.RequestException as e:
            print(f"Bark 通知发送失败: {e}")

    # Server酱 通知 (https://sct.ftqq.com/)
    serverchan_key = os.environ.get("SERVERCHAN_KEY") or config.get("serverchan", {}).get("key")
    if serverchan_key:
        try:
            # Server酱 SendKey 模式
            sc_url = f"https://sctapi.ftqq.com/{serverchan_key}.send"
            requests.post(sc_url, data={
                "title": "Cloud Studio 签到通知",
                "desp": message,
            }, timeout=10)
            print("Server酱 通知已发送")
        except requests.RequestException as e:
            print(f"Server酱 通知发送失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="腾讯 Cloud Studio 每日签到")
    parser.add_argument("--check", action="store_true", help="仅检查签到状态")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 获取 Cookie
    # 优先级: 环境变量 > 配置文件
    cookies = os.environ.get("CLOUD_STUDIO_COOKIES") or config.get("cookies", "")
    # 获取 XSRF Token
    xsrf_token = os.environ.get("CLOUD_STUDIO_XSRF_TOKEN") or config.get("xsrf_token", "")

    if not cookies:
        print("错误: 未设置 CLOUD_STUDIO_COOKIES")
        print("请设置环境变量或创建 config.json")
        sys.exit(1)

    if not xsrf_token:
        print("错误: 未设置 CLOUD_STUDIO_XSRF_TOKEN")
        print("请设置环境变量或创建 config.json")
        sys.exit(1)

    print("已获取 Cookie，长度:", len(cookies))
    print("已获取 XSRF Token:", xsrf_token[:10] + "...")

    # 执行签到
    signin = CloudStudioSignIn(cookies, xsrf_token)

    if args.check:
        # 仅检查状态
        status = signin.check_signin_status()
        print(f"今日已签到: {status.get('claimed', '未知')}")
        if status.get("reward_info"):
            info = status["reward_info"]
            print(f"获得奖励: {info.get('hours', '未知')} {info.get('reward_type', '')}")
            print(f"有效期: {info.get('reward_expires_days', '未知')} 天")
        return

    # 执行签到
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始 Cloud Studio 签到...")

    # 先检查状态
    status = signin.check_signin_status()
    if status.get("claimed"):
        reward_info = status.get("reward_info", {})
        hours = reward_info.get("hours", 0)
        print(f"今日已签到，获得 {hours} 小时机时")
        send_notification(f"Cloud Studio 签到: 今日已签到 (获得 {hours} 小时) ✅", config)
        return

    # 执行签到
    result = signin.claim_daily_reward()

    if result.get("success"):
        hours = result.get("hours", 0)
        reward_type = result.get("reward_type", "INSTANCE_HOUR")
        expires_days = result.get("reward_expires_days", 0)
        msg = f"签到成功! 获得 {hours} {reward_type} (有效期 {expires_days} 天) 🎉"
        print(msg)
        send_notification(f"Cloud Studio 签到成功! 获得 {hours} {reward_type}", config)
    else:
        msg = f"签到失败: {result.get('message', '未知错误')}"
        print(msg)
        send_notification(f"Cloud Studio 签到失败: {result.get('message', '未知错误')}", config)
        sys.exit(1)


if __name__ == "__main__":
    main()
