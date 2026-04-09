# Cloud Studio 每日签到

腾讯 Cloud Studio 每日机时自动签到脚本，支持 GitHub Actions 调度和多种通知渠道。

## 功能

- 自动领取每日 2 小时免费机时
- GitHub Actions 定时调度（每天北京时间 9:00）
- 支持手动触发
- Telegram / Bark / Server酱 通知推送
- 签到状态查询

## 快速开始

### 1. Fork 本仓库

### 2. 获取凭证

#### Cookie

1. 登录 [腾讯云](https://cloud.tencent.com/)
2. 按 F12 打开开发者工具，切换到 Network 标签
3. 刷新页面，找到第一个请求
4. 复制 Request Headers 中的 Cookie 值

#### XSRF Token

1. 在开发者工具 Network 标签中，找到任意请求
2. 在请求 Headers 中找到 `X-XSRF-TOKEN` 值
3. 如果没有，在响应 Headers 中查找 `set-cookie` 中的 `XSRF-TOKEN`

### 3. 配置 Secrets

在 GitHub 仓库的 `Settings → Secrets and variables → Actions` 中添加：

| Name | Required | Description |
|------|----------|-------------|
| `CLOUD_STUDIO_COOKIES` | Yes | 腾讯云登录 Cookie |
| `CLOUD_STUDIO_XSRF_TOKEN` | Yes | XSRF Token |
| `TELEGRAM_BOT_TOKEN` | No | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | No | Telegram Chat ID |
| `BARK_KEY` | No | Bark 推送 Key |
| `SERVERCHAN_KEY` | No | Server酱 SendKey |

### 4. 启用 Actions

1. 进入 Actions 标签
2. 点击 "I understand my workflows, go ahead and enable them"
3. 选择 "Cloud Studio Daily Sign-in"
4. 点击 "Run workflow" 测试

## 本地运行

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/cloud-studio-signin.git
cd cloud-studio-signin

# 安装依赖
pip install -r requirements.txt

# 运行签到（使用环境变量）
export CLOUD_STUDIO_COOKIES="your_cookies_here"
export CLOUD_STUDIO_XSRF_TOKEN="your_xsrf_token_here"
python signin.py

# 或使用配置文件
cp config.example.json config.json
# 编辑 config.json 填入你的凭证
python signin.py

# 仅检查签到状态
python signin.py --check
```

## 配置文件格式

```json
{
  "cookies": "your_cloud_studio_cookies_here",
  "xsrf_token": "your_xsrf_token_here",
  "telegram": {
    "bot_token": "your_telegram_bot_token",
    "chat_id": "your_telegram_chat_id"
  },
  "bark": {
    "key": "your_bark_key"
  },
  "serverchan": {
    "key": "your_serverchan_sendkey"
  }
}
```

## 获取 Cookie 教程

### 方法一：浏览器开发者工具

1. 登录 https://cloud.tencent.com/
2. 按 F12 打开开发者工具
3. 切换到 Network 标签
4. 刷新页面 (F5)
5. 点击第一个请求（通常是 document 或 init）
6. 在 Headers 中找到 Cookie，复制完整值

### 方法二：浏览器插件

安装 EditThisCookie 或 Cookie Editor 插件，直接导出 Cookie。

## 注意事项

- Cookie 和 XSRF Token 有效期有限，发现签到失败时请更新凭证
- 建议设置较短的调度周期（如每 12 小时）以便及时发现过期
- 请勿将凭证泄露给他人

## License

MIT
