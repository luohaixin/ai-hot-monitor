"""
邮件通知服务
基于 SMTP 实现热点邮件推送
"""

import smtplib
import ssl
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


def encode_rfc2047_header(text: str) -> str:
    """
    根据RFC2047标准编码邮件头部中的非ASCII字符
    
    Args:
        text: 要编码的文本（如中文昵称）
    
    Returns:
        RFC2047格式的编码字符串，例如: =?UTF-8?B?UVHpgq7nrrHmmLXnp7DnpLrkvos=?=
    """
    try:
        # 尝试直接编码为UTF-8 bytes，然后base64编码
        encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
        return f"=?UTF-8?B?{encoded}?="
    except Exception:
        # 编码失败时返回原文
        return text


def format_from_header(name: str, email: str) -> str:
    """
    格式化From头部，符合RFC5322/RFC2047标准
    
    如果名称包含非ASCII字符（如中文），则使用Base64编码
    
    Args:
        name: 显示名称（可能包含中文）
        email: 邮箱地址
    
    Returns:
        格式化后的From头部，例如:
        - ASCII名称: "AI Monitor <abc@qq.com>"
        - 中文名称: "=?UTF-8?B?QUkg55So55qE566h55CG5qGf6KiT?=<abc@qq.com>"
    """
    # 检查名称是否包含非ASCII字符
    try:
        name.encode('ascii')
        # 纯ASCII字符，直接使用
        return f"{name} <{email}>"
    except UnicodeEncodeError:
        # 包含非ASCII字符（如中文），需要RFC2047编码
        encoded_name = encode_rfc2047_header(name)
        return f"{encoded_name} <{email}>"


@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    from_name: Optional[str] = None


@dataclass
class HotspotEmailData:
    """热点邮件数据"""
    title: str
    summary: str
    url: str
    source: str
    importance: str
    relevance: int
    hot_score: float
    published_at: Optional[str] = None


class EmailService:
    """邮件服务"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config
        self._enabled = config is not None
    
    def is_configured(self) -> bool:
        """检查邮件是否已配置"""
        return (
            self._enabled and
            self.config and
            self.config.smtp_server and
            self.config.username and
            self.config.password
        )
    
    def _create_smtp_connection(self):
        """创建 SMTP 连接"""
        context = ssl.create_default_context()
        
        # 根据端口选择正确的连接方式
        # 465端口: SMTPS (SSL/TLS直连)
        # 587端口: SMTP + STARTTLS
        if self.config.smtp_port == 465:
            # 465端口使用SMTP_SSL直接建立SSL连接
            server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, context=context)
        elif self.config.use_tls:
            # 587端口使用SMTP + STARTTLS
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls(context=context)
        else:
            # 其他情况使用普通SMTP
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
        
        server.login(self.config.username, self.config.password)
        return server
    
    def _build_html_content(self, hotspot: HotspotEmailData) -> str:
        """构建邮件 HTML 内容"""
        
        importance_colors = {
            "urgent": "#dc2626",  # red
            "high": "#ea580c",    # orange
            "medium": "#ca8a04",  # yellow
            "low": "#6b7280"      # gray
        }
        importance_labels = {
            "urgent": "🔥 紧急",
            "high": "⭐ 重要",
            "medium": "📌 中等",
            "low": "📝 一般"
        }
        
        color = importance_colors.get(hotspot.importance, "#6b7280")
        label = importance_labels.get(hotspot.importance, "一般")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; background: {color}; margin-right: 10px; }}
                .meta {{ color: #6b7280; font-size: 14px; margin: 15px 0; }}
                .summary {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color}; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-top: 20px; }}
                .button:hover {{ background: #5a67d8; }}
                .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 30px; }}
                .stats {{ display: flex; gap: 20px; margin: 15px 0; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 20px; font-weight: bold; color: {color}; }}
                .stat-label {{ font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 AI热点监控</h1>
                <p>发现新的AI热点内容</p>
            </div>
            <div class="content">
                <div>
                    <span class="badge">{label}</span>
                    <span style="color: #6b7280; font-size: 14px;">{hotspot.source}</span>
                </div>
                
                <h2 style="margin-top: 20px; color: #1f2937;">{hotspot.title}</h2>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{hotspot.relevance}%</div>
                        <div class="stat-label">相关性</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{hotspot.hot_score:.0f}</div>
                        <div class="stat-label">热度</div>
                    </div>
                </div>
                
                <div class="summary">
                    <p style="margin: 0; color: #4b5563;">{hotspot.summary}</p>
                </div>
                
                <div class="meta">
                    <p>📅 发布时间: {hotspot.published_at or '未知'}</p>
                    <p>🔗 来源: {hotspot.source}</p>
                </div>
                
                <center>
                    <a href="{hotspot.url}" class="button">查看原文</a>
                </center>
            </div>
            
            <div class="footer">
                <p>此邮件由 AI热点监控工具 自动发送</p>
                <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def send_hotspot_notification(
        self,
        to_emails: List[str],
        hotspot: HotspotEmailData
    ) -> Dict[str, bool]:
        """
        发送热点通知邮件
        
        Args:
            to_emails: 收件人列表
            hotspot: 热点数据
            
        Returns:
            发送结果字典
        """
        if not self.is_configured():
            logger.warning("邮件服务未配置")
            return {email: False for email in to_emails}
        
        results = {}
        
        try:
            server = self._create_smtp_connection()
            
            for to_email in to_emails:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = f"[{hotspot.importance.upper()}] {hotspot.title[:50]}..."
                    # 使用RFC2047编码From头部，确保中文昵称符合标准
                    from_name = self.config.from_name or 'AI热点监控'
                    msg['From'] = format_from_header(from_name, self.config.username)
                    msg['To'] = to_email
                    
                    # HTML内容
                    html_content = self._build_html_content(hotspot)
                    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
                    
                    # 发送
                    server.send_message(msg)
                    results[to_email] = True
                    logger.info(f"邮件已发送到: {to_email}")
                    
                except Exception as e:
                    logger.error(f"发送邮件到 {to_email} 失败: {e}")
                    results[to_email] = False
            
            server.quit()
            
        except Exception as e:
            logger.error(f"邮件服务连接失败: {e}")
            return {email: False for email in to_emails}
        
        return results
    
    def send_batch_notification(
        self,
        to_emails: List[str],
        hotspots: List[HotspotEmailData],
        subject: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        发送批量热点通知
        
        Args:
            to_emails: 收件人列表
            hotspots: 热点列表
            subject: 邮件主题
            
        Returns:
            发送结果字典
        """
        if not self.is_configured():
            logger.warning("邮件服务未配置")
            return {email: False for email in to_emails}
        
        if not hotspots:
            return {email: True for email in to_emails}
        
        results = {}
        
        try:
            server = self._create_smtp_connection()
            
            for to_email in to_emails:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject or f"🔥 AI热点日报 - 发现 {len(hotspots)} 条热点"
                    # 使用RFC2047编码From头部，确保中文昵称符合标准
                    from_name = self.config.from_name or 'AI热点监控'
                    msg['From'] = format_from_header(from_name, self.config.username)
                    msg['To'] = to_email

                    # 构建批量HTML
                    html = self._build_batch_html(hotspots)
                    msg.attach(MIMEText(html, 'html', 'utf-8'))
                    
                    server.send_message(msg)
                    results[to_email] = True
                    logger.info(f"批量邮件已发送到: {to_email}")
                    
                except Exception as e:
                    logger.error(f"发送批量邮件到 {to_email} 失败: {e}")
                    results[to_email] = False
            
            server.quit()
            
        except Exception as e:
            logger.error(f"邮件服务连接失败: {e}")
            return {email: False for email in to_emails}
        
        return results
    
    def _build_batch_html(self, hotspots: List[HotspotEmailData]) -> str:
        """构建批量邮件HTML"""
        
        importance_colors = {
            "urgent": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#6b7280"
        }
        
        items_html = ""
        for i, hotspot in enumerate(hotspots[:10], 1):  # 最多显示10条
            color = importance_colors.get(hotspot.importance, "#6b7280")
            items_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 15px;">
                    <div style="font-weight: bold; color: #1f2937; margin-bottom: 5px;">
                        {i}. {hotspot.title}
                    </div>
                    <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">
                        {hotspot.source} | 热度: {hotspot.hot_score:.0f} | 相关性: {hotspot.relevance}%
                    </div>
                    <div style="font-size: 14px; color: #4b5563; line-height: 1.5;">
                        {hotspot.summary[:100]}...
                    </div>
                    <div style="margin-top: 8px;">
                        <a href="{hotspot.url}" style="color: #667eea; font-size: 13px; text-decoration: none;">查看原文 →</a>
                    </div>
                </td>
                <td style="padding: 15px; text-align: center;" width="80">
                    <span style="background: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px;">
                        {hotspot.importance.upper()}
                    </span>
                </td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }}
                .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔥 AI热点监控日报</h1>
                <p>今日发现 {len(hotspots)} 条AI相关热点</p>
            </div>
            <div class="content">
                <table>
                    {items_html}
                </table>
            </div>
            <div class="footer">
                <p>此邮件由 AI热点监控工具 自动发送</p>
                <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
    
    def test_connection(self) -> bool:
        """测试邮件连接"""
        if not self.is_configured():
            return False
        
        try:
            server = self._create_smtp_connection()
            server.quit()
            return True
        except Exception as e:
            logger.error(f"邮件连接测试失败: {e}")
            return False


# 全局邮件服务实例
_email_service: Optional[EmailService] = None


def get_email_service(config: Optional[EmailConfig] = None) -> EmailService:
    """获取邮件服务实例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService(config)
    return _email_service
