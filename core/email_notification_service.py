"""
邮件通知服务 - 爬取任务自动化绑定模块
实现热点爬取与邮件发送的自动化关联
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from .email_service import EmailService, EmailConfig, HotspotEmailData
from .config_loader import get_config


@dataclass
class CrawlEmailBindingConfig:
    """爬取-邮件绑定配置"""
    enabled: bool = True  # 是否启用自动邮件通知
    min_hotspots_to_notify: int = 1  # 最少新热点数量才发送邮件
    notify_on_urgent_only: bool = False  # 是否仅紧急热点时才通知
    recipients: List[str] = field(default_factory=list)  # 邮件接收者列表
    send_batch: bool = True  # 是否批量发送（True=批量邮件，False=单条邮件）
    include_summary: bool = True  # 是否包含摘要信息


@dataclass
class EmailSendLog:
    """邮件发送日志记录"""
    send_time: datetime
    crawl_time: datetime
    new_hotspots_count: int
    recipients: List[str]
    success: bool
    message: str
    hotspot_ids: List[int] = field(default_factory=list)
    error_details: Optional[str] = None


class EmailNotificationService:
    """
    邮件通知服务
    
    功能：
    1. 监听爬取任务结果
    2. 检测新热点内容
    3. 自动触发邮件发送（仅在发现新热点时）
    4. 完整的日志记录
    """
    
    def __init__(self, email_service: Optional[EmailService] = None):
        self.config = get_config()
        self.binding_config = self._load_binding_config()
        
        # 邮件服务实例
        self.email_service = email_service or self._create_email_service()
        
        # 发送日志记录（最多保留100条）
        self.send_logs: List[EmailSendLog] = []
        self.max_logs = 100
        
        # 上次爬取状态
        self._last_crawl_stats: Optional[Dict[str, Any]] = None
        self._last_new_hotspots: List[Dict] = []
        
        logger.info(f"📧 邮件通知服务初始化完成 (启用: {self.binding_config.enabled})")
    
    def _load_binding_config(self) -> CrawlEmailBindingConfig:
        """加载绑定配置"""
        email_config = self.config.email_config
        
        # 从配置中读取接收者列表
        recipients = email_config.get('recipients', [])
        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(',') if r.strip()]
        
        # 优先从环境变量读取收件人列表
        env_recipients = os.getenv("EMAIL_RECIPIENTS")
        if env_recipients:
            recipients = [r.strip() for r in env_recipients.split(',') if r.strip()]
        
        # 读取自动化绑定配置（新增配置项）
        auto_notify = email_config.get('auto_notify', True)
        min_hotspots = email_config.get('min_hotspots_to_notify', 1)
        urgent_only = email_config.get('notify_on_urgent_only', False)
        send_batch = email_config.get('send_batch', True)
        include_summary = email_config.get('include_summary', True)
        
        # 检查邮件功能是否启用（email.enabled）
        email_enabled = email_config.get('enabled', False)
        push_enabled = self.config.push_config.get('enabled', False)
        
        # 只有当email.enabled为true时才启用（不再强制依赖push.enabled）
        enabled = email_enabled and auto_notify
        
        logger.debug(f"邮件绑定配置: enabled={enabled}, email_enabled={email_enabled}, push_enabled={push_enabled}, auto_notify={auto_notify}")
        
        return CrawlEmailBindingConfig(
            enabled=enabled,
            min_hotspots_to_notify=min_hotspots,
            notify_on_urgent_only=urgent_only,
            recipients=recipients,
            send_batch=send_batch,
            include_summary=include_summary
        )
    
    def _create_email_service(self) -> EmailService:
        """创建邮件服务实例"""
        # 优先从环境变量读取配置
        if os.getenv("EMAIL_SMTP_SERVER"):
            config = EmailConfig(
                smtp_server=os.getenv("EMAIL_SMTP_SERVER"),
                smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "465")),
                username=os.getenv("EMAIL_USERNAME", ""),
                password=os.getenv("EMAIL_PASSWORD", ""),
                use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
                from_name=os.getenv("EMAIL_FROM_NAME", "AI热点监控")
            )
            return EmailService(config)
        
        # 否则从配置文件读取
        email_config = self.config.email_config
        if email_config.get('smtp_server') and email_config.get('username'):
            config = EmailConfig(
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config.get('smtp_port', 465),
                username=email_config['username'],
                password=email_config.get('password', ''),
                use_tls=email_config.get('use_tls', True),
                from_name=email_config.get('from_name', 'AI热点监控')
            )
            return EmailService(config)
        
        logger.warning("⚠️ 邮件服务未配置，邮件通知功能不可用")
        return EmailService(None)
    
    def on_crawl_completed(self, crawl_stats: Dict[str, Any], new_hotspots: List[Dict]) -> Dict[str, Any]:
        """
        爬取完成后的回调处理
        
        Args:
            crawl_stats: 爬取统计信息
            new_hotspots: 新增热点数据列表
        
        Returns:
            处理结果字典
        """
        result = {
            'should_send': False,
            'sent': False,
            'message': '',
            'send_log': None
        }
        
        # 记录爬取状态
        self._last_crawl_stats = crawl_stats
        self._last_new_hotspots = new_hotspots
        
        crawl_time = datetime.now()
        new_count = len(new_hotspots)
        
        logger.info(f"📊 爬取完成回调 - 新热点数量: {new_count}")
        
        send_time = datetime.now()
        
        # 1. 检查邮件服务是否配置
        if not self.email_service.is_configured():
            result['message'] = "邮件服务未配置"
            logger.warning(f"⏭️ {result['message']}，跳过邮件通知")
            self._record_send_log(send_time, crawl_time, new_hotspots, [], False, result['message'])
            return result
        
        # 2. 检查是否启用自动通知
        if not self.binding_config.enabled:
            result['message'] = "自动邮件通知已禁用"
            logger.info(f"⏭️ {result['message']}")
            self._record_send_log(send_time, crawl_time, new_hotspots, [], False, result['message'])
            return result
        
        # 3. 检查是否有接收者
        if not self.binding_config.recipients:
            result['message'] = "未配置邮件接收者"
            logger.warning(f"⏭️ {result['message']}，跳过邮件通知")
            self._record_send_log(send_time, crawl_time, new_hotspots, [], False, result['message'])
            return result
        
        # 4. 检查新热点数量是否达到最小阈值
        if new_count < self.binding_config.min_hotspots_to_notify:
            result['message'] = f"新热点数量({new_count})未达到阈值({self.binding_config.min_hotspots_to_notify})"
            logger.info(f"⏭️ {result['message']}，不发送邮件")
            self._record_send_log(send_time, crawl_time, new_hotspots, [], False, result['message'])
            return result
        
        # 5. 检查是否仅紧急热点模式
        if self.binding_config.notify_on_urgent_only:
            urgent_hotspots = [h for h in new_hotspots if h.get('importance') == 'urgent']
            if not urgent_hotspots:
                result['message'] = "无紧急热点，跳过通知"
                logger.info(f"⏭️ {result['message']}")
                self._record_send_log(send_time, crawl_time, new_hotspots, [], False, result['message'])
                return result
            new_hotspots = urgent_hotspots
            new_count = len(new_hotspots)
        
        # 满足发送条件
        result['should_send'] = True
        logger.info(f"📧 满足邮件发送条件，准备发送通知 (新热点: {new_count}条)")
        
        # 执行邮件发送
        send_result = self._send_notification(new_hotspots, crawl_stats)
        result['sent'] = send_result['success']
        result['message'] = send_result['message']
        result['send_log'] = send_result.get('log')
        
        return result
    
    def _send_notification(self, hotspots: List[Dict], crawl_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行邮件通知发送
        
        Args:
            hotspots: 要通知的热点列表
            crawl_stats: 爬取统计信息
        
        Returns:
            发送结果
        """
        result = {
            'success': False,
            'message': '',
            'log': None
        }
        
        recipients = self.binding_config.recipients
        send_time = datetime.now()
        
        try:
            if self.binding_config.send_batch and len(hotspots) > 1:
                # 批量发送模式
                logger.info(f"📧 发送批量邮件通知 ({len(hotspots)}条热点) -> {recipients}")
                
                email_data_list = [self._convert_to_email_data(h) for h in hotspots]
                send_results = self.email_service.send_batch_notification(
                    to_emails=recipients,
                    hotspots=email_data_list,
                    subject=f"🔥 AI热点监控 - 发现 {len(hotspots)} 条新热点"
                )
                
                success_count = sum(1 for v in send_results.values() if v)
                result['success'] = success_count > 0
                result['message'] = f"批量邮件发送完成: {success_count}/{len(recipients)} 成功"
                
            else:
                # 单条发送模式（只发第一条或批量模式关闭时）
                hotspot = hotspots[0] if hotspots else None
                if hotspot:
                    logger.info(f"📧 发送单条邮件通知 ({hotspot.get('title', '无标题')[:30]}...) -> {recipients}")
                    
                    email_data = self._convert_to_email_data(hotspot)
                    send_results = self.email_service.send_hotspot_notification(
                        to_emails=recipients,
                        hotspot=email_data
                    )
                    
                    success_count = sum(1 for v in send_results.values() if v)
                    result['success'] = success_count > 0
                    result['message'] = f"单条邮件发送完成: {success_count}/{len(recipients)} 成功"
                else:
                    result['message'] = "无热点数据可发送"
            
            # 记录发送日志
            log = self._record_send_log(
                send_time=send_time,
                crawl_time=crawl_stats.get('crawl_time', send_time),
                new_hotspots=hotspots,
                recipients=recipients,
                success=result['success'],
                message=result['message']
            )
            result['log'] = log
            
            if result['success']:
                logger.success(f"✅ {result['message']}")
            else:
                logger.error(f"❌ {result['message']}")
                
        except Exception as e:
            result['message'] = f"邮件发送异常: {str(e)}"
            result['error'] = str(e)
            logger.error(f"❌ {result['message']}")
            
            # 记录失败日志
            log = self._record_send_log(
                send_time=send_time,
                crawl_time=crawl_stats.get('crawl_time', send_time),
                new_hotspots=hotspots,
                recipients=recipients,
                success=False,
                message=result['message'],
                error_details=str(e)
            )
            result['log'] = log
        
        return result
    
    def _convert_to_email_data(self, hotspot: Dict) -> HotspotEmailData:
        """将热点数据转换为邮件数据格式"""
        return HotspotEmailData(
            title=hotspot.get('title', '无标题'),
            summary=hotspot.get('ai_summary') or hotspot.get('summary', ''),
            url=hotspot.get('url', ''),
            source=hotspot.get('source', '未知来源'),
            importance=hotspot.get('importance', 'medium'),
            relevance=hotspot.get('relevance', 70),
            hot_score=hotspot.get('hot_score', 0.0),
            published_at=hotspot.get('publish_time', '').strftime('%Y-%m-%d %H:%M') if hasattr(hotspot.get('publish_time'), 'strftime') else str(hotspot.get('publish_time', ''))
        )
    
    def _record_send_log(self, send_time: datetime, crawl_time: datetime, 
                        new_hotspots: List[Dict], recipients: List[str],
                        success: bool, message: str, error_details: Optional[str] = None) -> EmailSendLog:
        """记录发送日志"""
        log = EmailSendLog(
            send_time=send_time,
            crawl_time=crawl_time if isinstance(crawl_time, datetime) else send_time,
            new_hotspots_count=len(new_hotspots),
            recipients=recipients.copy(),
            success=success,
            message=message,
            hotspot_ids=[h.get('id') for h in new_hotspots if h.get('id')],
            error_details=error_details
        )
        
        self.send_logs.append(log)
        
        # 限制日志数量
        if len(self.send_logs) > self.max_logs:
            self.send_logs = self.send_logs[-self.max_logs:]
        
        return log
    
    def get_send_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取发送日志（用于API查询）"""
        logs = self.send_logs[-limit:] if limit < len(self.send_logs) else self.send_logs
        return [
            {
                'send_time': log.send_time.isoformat(),
                'crawl_time': log.crawl_time.isoformat(),
                'new_hotspots_count': log.new_hotspots_count,
                'recipients': log.recipients,
                'success': log.success,
                'message': log.message,
                'hotspot_ids': log.hotspot_ids,
                'error_details': log.error_details
            }
            for log in reversed(logs)  # 最新的在前
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """获取邮件通知服务状态"""
        return {
            'enabled': self.binding_config.enabled,
            'email_configured': self.email_service.is_configured(),
            'recipients_count': len(self.binding_config.recipients),
            'min_hotspots_to_notify': self.binding_config.min_hotspots_to_notify,
            'send_batch': self.binding_config.send_batch,
            'last_crawl_new_count': len(self._last_new_hotspots),
            'total_send_logs': len(self.send_logs),
            'recent_send_logs': self.get_send_logs(5)
        }
    
    def update_config(self, **kwargs) -> bool:
        """更新配置（运行时）"""
        try:
            if 'enabled' in kwargs:
                self.binding_config.enabled = bool(kwargs['enabled'])
            if 'min_hotspots_to_notify' in kwargs:
                self.binding_config.min_hotspots_to_notify = int(kwargs['min_hotspots_to_notify'])
            if 'recipients' in kwargs:
                recipients = kwargs['recipients']
                if isinstance(recipients, str):
                    recipients = [r.strip() for r in recipients.split(',') if r.strip()]
                self.binding_config.recipients = recipients
            if 'send_batch' in kwargs:
                self.binding_config.send_batch = bool(kwargs['send_batch'])
            
            logger.info(f"📧 邮件通知配置已更新: {kwargs}")
            return True
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            return False


# 全局邮件通知服务实例
_email_notification_service: Optional[EmailNotificationService] = None


def get_email_notification_service(email_service: Optional[EmailService] = None) -> EmailNotificationService:
    """获取邮件通知服务实例（单例）"""
    global _email_notification_service
    if _email_notification_service is None:
        _email_notification_service = EmailNotificationService(email_service)
    return _email_notification_service
