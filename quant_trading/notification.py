"""
实时通知模块 - 支持钉钉/企业微信机器人
功能：将交易信号、市场情绪、热点异动推送到手机
"""

import requests
import json
import logging
import os
import datetime

# 配置文件路径
CONFIG_FILE = os.path.join("data", "notification_config.json")

class NotificationManager:
    def __init__(self):
        self.config = self._load_config()
        self.webhook_url = self.config.get("webhook_url", "")
        self.platform = self.config.get("platform", "dingtalk")  # dingtalk 或 wecom
        self.enabled = self.config.get("enabled", False)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"enabled": False, "platform": "dingtalk", "webhook_url": ""}

    def save_config(self, enabled, platform, webhook_url):
        """保存配置"""
        self.enabled = enabled
        self.platform = platform
        self.webhook_url = webhook_url
        self.config = {
            "enabled": enabled,
            "platform": platform,
            "webhook_url": webhook_url
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
            
        return self.send_text("🔔 通知服务配置成功！测试消息")

    def send_text(self, content):
        """发送纯文本消息"""
        if not self.enabled or not self.webhook_url:
            return False
            
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            full_content = f"[{timestamp}] 量化提醒\n{content}"
            
            if self.platform == "dingtalk":
                return self._send_dingtalk(full_content)
            elif self.platform == "wecom":
                return self._send_wecom(full_content)
        except Exception as e:
            logging.error(f"发送通知失败: {e}")
            return False

    def send_markdown(self, title, content):
        """发送Markdown消息 (更美观)"""
        if not self.enabled or not self.webhook_url:
            return False
            
        try:
            if self.platform == "dingtalk":
                return self._send_dingtalk_markdown(title, content)
            elif self.platform == "wecom":
                # 企业微信Markdown格式稍有不同，简单适配
                return self._send_wecom_markdown(content)
        except Exception as e:
            logging.error(f"发送Markdown通知失败: {e}")
            return False

    def _send_dingtalk(self, content):
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        resp = requests.post(self.webhook_url, headers=headers, json=data, timeout=5)
        return resp.json().get("errcode") == 0

    def _send_dingtalk_markdown(self, title, text):
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{text}"
            }
        }
        resp = requests.post(self.webhook_url, headers=headers, json=data, timeout=5)
        return resp.json().get("errcode") == 0

    def _send_wecom(self, content):
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        resp = requests.post(self.webhook_url, headers=headers, json=data, timeout=5)
        return resp.json().get("errcode") == 0

    def _send_wecom_markdown(self, content):
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        resp = requests.post(self.webhook_url, headers=headers, json=data, timeout=5)
        return resp.json().get("errcode") == 0

    # === 业务场景快捷方法 ===

    def notify_trade(self, action, symbol, name, price, volume, reason=""):
        """交易通知"""
        color = "#dd0000" if action == "买入" else "#00dd00"
        title = f"{action}提醒: {name}"
        
        md = f"""
**<font color='{color}'>{action}成交提醒</font>**
---
- **股票**: {name} ({symbol})
- **价格**: {price}
- **数量**: {volume}
- **金额**: {price * volume:.0f}
- **理由**: {reason}
- **时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_markdown(title, md)

    def notify_sentiment_change(self, old_status, new_status, score):
        """情绪变更通知"""
        title = "市场情绪变更"
        status_map = {
            "BULLISH": "🔴 牛市 (积极买入)",
            "BEARISH": "🟢 熊市 (停止买入)",
            "NEUTRAL": "⚪ 震荡 (谨慎操作)"
        }
        old_str = status_map.get(old_status, old_status)
        new_str = status_map.get(new_status, new_status)
        
        md = f"""
**市场情绪发生变化** ??
---
- **变化**: {old_str} ➔ **{new_str}**
- **当前评分**: {score}/100
- **策略调整**: 系统已自动更新风控策略
"""
        return self.send_markdown(title, md)

    def notify_hotspot_change(self, new_sectors):
        """热点板块变更通知"""
        title = "新晋热点板块"
        sectors_str = "\n".join([f"- 🔥 {s['name']} ({s['cycle']})" for s in new_sectors])
        
        md = f"""
**发现新热点板块** 🚀
---
{sectors_str}

*建议关注板块内前排龙头*
"""
        return self.send_markdown(title, md)

# 全局单例
notifier = NotificationManager()
