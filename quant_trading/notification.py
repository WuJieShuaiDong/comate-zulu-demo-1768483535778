"""
实时通知模块 - 支持钉钉/企业微信机器人
功能：将交易信号、市场情绪、热点异动推送到手机
"""

import requests
import json
import logging
import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 配置文件路径
CONFIG_FILE = os.path.join("data", "notification_config.json")

class NotificationManager:
    def __init__(self):
        self.config = self._load_config()
        self.webhook_url = self.config.get("webhook_url", "")
        self.platform = self.config.get("platform", "dingtalk")  # dingtalk, wecom, or pushplus
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
            elif self.platform == "pushplus":
                return self._send_pushplus(content, "量化交易提醒")
            elif self.platform == "email":
                return self._send_email("量化交易提醒", content)
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
            elif self.platform == "pushplus":
                return self._send_pushplus(content, title, "markdown")
            elif self.platform == "email":
                # 邮件不支持Markdown，转为纯文本或HTML
                # 这里简单处理，直接发内容
                return self._send_email(title, content)
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

    def _send_pushplus(self, content, title="量化通知", template="html"):
        """
        PushPlus 发送接口
        :param content: 消息内容
        :param title: 消息标题
        :param template: 模板类型 ('html', 'markdown', 'txt', 'json')
        """
        url = "http://www.pushplus.plus/send"
        data = {
            "token": self.webhook_url,  # PushPlus 的 token 直接填在 webhook_url 字段里
            "title": title,
            "content": content,
            "template": template
        }
        resp = requests.post(url, json=data, timeout=5)
        res_json = resp.json()
        return res_json.get("code") == 200

    def _send_email(self, title, content):
        """
        发送邮件通知 (QQ邮箱/163邮箱等)
        webhook_url 格式: "smtp.qq.com|587|your_email@qq.com|auth_code|target_email@qq.com"
        """
        try:
            # 解析配置
            parts = self.webhook_url.split('|')
            if len(parts) < 5:
                logging.error("邮件配置格式错误，应为: host|port|user|pass|to")
                return False
                
            smtp_host = parts[0]
            smtp_port = int(parts[1])
            smtp_user = parts[2]
            smtp_pass = parts[3]
            smtp_to = parts[4]
            
            # 构造邮件
            message = MIMEText(content, 'plain', 'utf-8')
            message['From'] = Header("量化交易机器人", 'utf-8')
            message['To'] = Header("管理员", 'utf-8')
            message['Subject'] = Header(title, 'utf-8')
            
            # 发送邮件
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
                
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [smtp_to], message.as_string())
            server.quit()
            return True
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")
            return False

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
