"""
推送渠道实现 - 支持多种推送方式
"""

import json
import hmac
import hashlib
import base64
import time
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from urllib.parse import urlencode
import requests
from loguru import logger


class PushChannel(ABC):
    """推送渠道基类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
    
    @abstractmethod
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送消息"""
        pass
    
    def _retry_send(self, send_func, max_retries: int = 2) -> bool:
        """带重试的发送"""
        for i in range(max_retries + 1):
            try:
                return send_func()
            except Exception as e:
                if i < max_retries:
                    logger.warning(f"发送失败，第{i+1}次重试: {e}")
                else:
                    logger.error(f"发送失败，已重试{max_retries}次: {e}")
        return False


class WeComChannel(PushChannel):
    """企业微信推送"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        webhook_url = self.config.get('webhook_url', '')
        if not webhook_url:
            logger.error("企业微信webhook未配置")
            return False
        
        def _send():
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"**{title}**\n\n{content}"
                }
            }
            
            mention_users = self.config.get('mention_users', [])
            if mention_users:
                data["markdown"]["mentioned_mobile_list"] = mention_users
            
            resp = requests.post(
                webhook_url,
                json=data,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get('errcode') == 0:
                logger.info("企业微信推送成功")
                return True
            else:
                raise Exception(f"企业微信API错误: {result}")
        
        return self._retry_send(_send)


class DingTalkChannel(PushChannel):
    """钉钉推送"""
    
    def _generate_sign(self, timestamp: str, secret: str) -> str:
        """生成钉钉签名"""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return requests.utils.quote(sign, safe='')
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        webhook_url = self.config.get('webhook_url', '')
        secret = self.config.get('secret', '')
        
        if not webhook_url:
            logger.error("钉钉webhook未配置")
            return False
        
        def _send():
            timestamp = str(int(time.time() * 1000))
            
            # 如果有secret，添加签名
            if secret:
                sign = self._generate_sign(timestamp, secret)
                webhook_url_with_sign = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
            else:
                webhook_url_with_sign = webhook_url
            
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"### {title}\n\n{content}"
                }
            }
            
            resp = requests.post(
                webhook_url_with_sign,
                json=data,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get('errcode') == 0:
                logger.info("钉钉推送成功")
                return True
            else:
                raise Exception(f"钉钉API错误: {result}")
        
        return self._retry_send(_send)


class FeishuChannel(PushChannel):
    """飞书推送"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        webhook_url = self.config.get('webhook_url', '')
        if not webhook_url:
            logger.error("飞书webhook未配置")
            return False
        
        def _send():
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": title
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
                            }
                        }
                    ]
                }
            }
            
            resp = requests.post(
                webhook_url,
                json=data,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get('code') == 0:
                logger.info("飞书推送成功")
                return True
            else:
                raise Exception(f"飞书API错误: {result}")
        
        return self._retry_send(_send)


class EmailChannel(PushChannel):
    """邮件推送"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_server = self.config.get('smtp_server', '')
        smtp_port = self.config.get('smtp_port', 587)
        username = self.config.get('username', '')
        password = self.config.get('password', '')
        recipients = self.config.get('recipients', [])
        
        if not all([smtp_server, username, password, recipients]):
            logger.error("邮件配置不完整")
            return False
        
        def _send():
            import ssl
            
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = title
            
            # 添加HTML内容
            html_content = f"""
            <html>
                <body>
                    <h2>{title}</h2>
                    <div>{content.replace(chr(10), '<br>')}</div>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            context = ssl.create_default_context()
            
            # 根据端口选择正确的连接方式
            # 465端口: SMTPS (SSL/TLS直连)
            # 587端口: SMTP + STARTTLS
            if smtp_port == 465:
                # 465端口使用SMTP_SSL直接建立SSL连接
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # 587端口使用SMTP + STARTTLS
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls(context=context)
                    server.login(username, password)
                    server.send_message(msg)
            
            logger.info("邮件推送成功")
            return True
        
        return self._retry_send(_send)


class TelegramChannel(PushChannel):
    """Telegram推送"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        bot_token = self.config.get('bot_token', '')
        chat_id = self.config.get('chat_id', '')
        
        if not bot_token or not chat_id:
            logger.error("Telegram配置不完整")
            return False
        
        def _send():
            message = f"<b>{title}</b>\n\n{content}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            resp = requests.post(url, json=data, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            
            if result.get('ok'):
                logger.info("Telegram推送成功")
                return True
            else:
                raise Exception(f"Telegram API错误: {result}")
        
        return self._retry_send(_send)


class NtfyChannel(PushChannel):
    """ntfy推送（简单HTTP推送服务）"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        if not self.enabled:
            return True
        
        server = self.config.get('server', 'https://ntfy.sh')
        topic = self.config.get('topic', 'ai-hot-monitor')
        
        if not topic:
            logger.error("ntfy topic未配置")
            return False
        
        def _send():
            url = f"{server}/{topic}"
            
            headers = {
                "Title": title,
                "Priority": kwargs.get('priority', 'default'),
                "Tags": "robot"
            }
            
            resp = requests.post(
                url,
                data=content.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            
            logger.info("ntfy推送成功")
            return True
        
        return self._retry_send(_send)


class ConsoleChannel(PushChannel):
    """控制台输出（用于测试）"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        print("=" * 50)
        print(f"[推送消息] {title}")
        print("-" * 50)
        print(content)
        print("=" * 50)
        return True
