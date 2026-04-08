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

    def __init__(self, cookies: str, timeout: int = 30):
        """
        初始化签到类

        Args:
            cookies: Cloud Studio 登录 Cookie
            timeout: 请求超时时间(秒)
        """
        self.cookies = cookies
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/146.0.0.0",
            "Referer": "https://cloudstudio.net/user-center",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookies,  # 直接设置 Cookie 头
        })

        # Cloud Studio API 端点
        self.api_base = "https://cloudstudio.net"
        # 签到 API (2025Q3 活动)
        self.signin_endpoint = "/api/billing/activityTask/SIGN_IN_2025Q3"
        # 状态查询参数
        self.status_param = "?lastRecord=true"

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
        # POST /api/billing/activityTask/SIGN_IN_2025Q3
        # 每日可领取1次，每次2个机时
        url = f"{self.api_base}{self.signin_endpoint}"

        try:
            resp = self.session.post(url, timeout=self.timeout)
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
        # GET /api/billing/activityTask/SIGN_IN_2025Q3?lastRecord=true
        url = f"{self.api_base}{self.signin_endpoint}{self.status_param}"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_status_result(data)
        except requests.RequestException as e:
            return {"claimed": None, "message": f"检查状态失败: {e}"}

    def _parse_signin_result(self, response: dict) -> dict:
        """解析签到响应"""
        # 响应格式:
        # {"code": 0, "message": "success", "data": {...}}
        # {"code": 400, "message": "已签到", "data": null}
        code = response.get("code", -1)
        if code == 0:
            return {
                "success": True,
                "message": "签到成功",
                "hours": 2,  # 固定2个机时
            }
        else:
            return {
                "success": False,
                "message": response.get("message", "签到失败"),
                "code": code,
            }

    def _parse_status_result(self, response: dict) -> dict:
        """解析状态查询响应"""
        # GET /api/billing/activityTask/SIGN_IN_2025Q3?lastRecord=true
        # 响应包含 lastRecord 字段表示今日签到状态
        data = response.get("data", {})
        last_record = data.get("lastRecord", {})

        return {
            "claimed": last_record.get("claimed", False) if last_record else False,
            "remaining_hours": data.get("remainingHours", 0),
            "message": "查询成功" if response.get("code") == 0 else f"查询失败: {response.get('message')}",
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

    if not cookies:
        print("错误: 未设置 CLOUD_STUDIO_COOKIES")
        print("请设置环境变量或创建 config.json")
        sys.exit(1)

    # 执行签到
    signin = CloudStudioSignIn(cookies)

    if args.check:
        # 仅检查状态
        status = signin.check_signin_status()
        print(f"今日已签到: {status.get('claimed', '未知')}")
        print(f"剩余机时: {status.get('remaining_hours', '未知')} 小时")
        return

    # 执行签到
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始 Cloud Studio 签到...")

    # 先检查状态
    status = signin.check_signin_status()
    if status.get("claimed"):
        print("今日已签到，跳过")
        send_notification("Cloud Studio 签到: 今日已签到 ✅", config)
        return

    # 执行签到
    result = signin.claim_daily_reward()

    if result.get("success"):
        hours = result.get("hours", 2)
        msg = f"签到成功! 获得 {hours} 小时机时 🎉"
        print(msg)
        send_notification(f"Cloud Studio 签到成功! 获得 {hours} 小时机时", config)
    else:
        msg = f"签到失败: {result.get('message', '未知错误')}"
        print(msg)
        send_notification(f"Cloud Studio 签到失败: {result.get('message', '未知错误')}", config)
        sys.exit(1)


if __name__ == "__main__":
    main()
