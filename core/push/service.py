"""
推送服务 - 统一推送接口
"""

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from loguru import logger

from ..config_loader import get_config
from ..models import get_db, HotspotORM
from .channels import (
    WeComChannel, DingTalkChannel, FeishuChannel,
    EmailChannel, TelegramChannel, NtfyChannel, ConsoleChannel
)

if TYPE_CHECKING:
    from ..urgent_detector import UrgentHotspotDetector, UrgentPushService


class PushService:
    """推送服务"""
    
    def __init__(self):
        self.config = get_config()
        self.push_config = self.config.push_config
        self.channels = self._init_channels()
        self.db = get_db()
    
    def _init_channels(self) -> Dict:
        """初始化推送渠道"""
        channels = {}
        
        # 验证并初始化各渠道
        if 'wecom' in self.push_config:
            config = self.push_config['wecom']
            if config.get('enabled', False) and not config.get('webhook_url'):
                logger.warning("企业微信推送已启用但webhook_url未配置")
            else:
                channels['wecom'] = WeComChannel(config)
        
        if 'dingtalk' in self.push_config:
            config = self.push_config['dingtalk']
            if config.get('enabled', False) and not config.get('webhook_url'):
                logger.warning("钉钉推送已启用但webhook_url未配置")
            else:
                channels['dingtalk'] = DingTalkChannel(config)
        
        if 'feishu' in self.push_config:
            config = self.push_config['feishu']
            if config.get('enabled', False) and not config.get('webhook_url'):
                logger.warning("飞书推送已启用但webhook_url未配置")
            else:
                channels['feishu'] = FeishuChannel(config)
        
        if 'email' in self.push_config:
            config = self.push_config['email']
            if config.get('enabled', False):
                required_fields = ['smtp_server', 'username', 'password', 'recipients']
                missing = [f for f in required_fields if not config.get(f)]
                if missing:
                    logger.warning(f"邮件推送已启用但配置不完整，缺少: {', '.join(missing)}")
                else:
                    channels['email'] = EmailChannel(config)
            else:
                channels['email'] = EmailChannel(config)
        
        if 'telegram' in self.push_config:
            config = self.push_config['telegram']
            if config.get('enabled', False):
                missing = []
                if not config.get('bot_token'):
                    missing.append('bot_token')
                if not config.get('chat_id'):
                    missing.append('chat_id')
                if missing:
                    logger.warning(f"Telegram推送已启用但配置不完整，缺少: {', '.join(missing)}")
                else:
                    channels['telegram'] = TelegramChannel(config)
            else:
                channels['telegram'] = TelegramChannel(config)
        
        if 'ntfy' in self.push_config:
            config = self.push_config['ntfy']
            if config.get('enabled', False) and not config.get('topic'):
                logger.warning("ntfy推送已启用但topic未配置，使用默认topic: ai-hot-monitor")
                config['topic'] = 'ai-hot-monitor'
                channels['ntfy'] = NtfyChannel(config)
            else:
                channels['ntfy'] = NtfyChannel(config)
        
        # 默认添加控制台渠道用于测试
        channels['console'] = ConsoleChannel({'enabled': True})
        
        # 记录已加载的渠道
        enabled_channels = [name for name, ch in channels.items() if ch.enabled]
        logger.info(f"推送渠道初始化完成，已启用: {enabled_channels}")
        
        return channels
    
    def send(self, title: str, content: str, channels: List[str] = None, **kwargs) -> Dict[str, bool]:
        """
        发送推送
        
        Args:
            title: 标题
            content: 内容
            channels: 指定渠道，None则使用所有启用的渠道
        
        Returns:
            各渠道发送结果
        """
        if not self.push_config.get('enabled', False):
            logger.warning("推送功能未启用")
            return {}
        
        results = {}
        target_channels = channels or list(self.channels.keys())
        
        for channel_name in target_channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    success = channel.send(title, content, **kwargs)
                    results[channel_name] = success
                except Exception as e:
                    logger.error(f"推送渠道 {channel_name} 失败: {e}")
                    results[channel_name] = False
            else:
                logger.warning(f"未知的推送渠道: {channel_name}")
                results[channel_name] = False
        
        return results
    
    def push_hotspot(self, hotspot: Dict, **kwargs) -> Dict[str, bool]:
        """推送单个热点"""
        title = f"🔥 {hotspot.get('title', '新热点')}"
        
        content_parts = [
            f"📊 热度: {hotspot.get('hot_score', 0):.1f}",
            f"🏷️ 分类: {hotspot.get('category', '其他')}",
            f"😊 情感: {self._format_sentiment(hotspot.get('sentiment', 'neutral'))}",
            f"📰 来源: {hotspot.get('source', '未知')}",
            "",
            f"📝 {hotspot.get('summary', '无摘要')[:200]}..." if hotspot.get('summary') else "",
            "",
            f"🔗 {hotspot.get('url', '')}"
        ]
        
        content = "\n".join(filter(None, content_parts))
        
        return self.send(title, content, **kwargs)
    
    def push_daily_summary(self, hotspots: List[Dict]) -> Dict[str, bool]:
        """推送每日汇总"""
        today = datetime.now().strftime('%Y-%m-%d')
        title = f"📈 AI热点日报 ({today})"
        
        content_parts = [f"今日共发现 {len(hotspots)} 条AI热点：\n"]
        
        # 按热度排序
        sorted_hotspots = sorted(hotspots, key=lambda x: x.get('hot_score', 0), reverse=True)[:10]
        
        for i, hotspot in enumerate(sorted_hotspots, 1):
            content_parts.append(
                f"{i}. {hotspot.get('title', '无标题')} "
                f"(热度: {hotspot.get('hot_score', 0):.1f})"
            )
        
        content = "\n".join(content_parts)
        
        return self.send(title, content)
    
    def push_alert(self, alert_type: str, message: str, **kwargs) -> Dict[str, bool]:
        """推送告警"""
        title = f"⚠️ 系统告警: {alert_type}"
        return self.send(title, message, priority='high', **kwargs)
    
    def check_and_push(self, threshold: float = None) -> int:
        """
        检查并推送热点（阈值模式）
        
        Returns:
            推送的热点数量
        """
        threshold = threshold or self.config.hot_score_config.get('threshold', 100)
        
        session = self.db.get_session()
        try:
            # 获取未推送的热点
            hotspots = session.query(HotspotORM).filter_by(
                is_pushed=False,
                is_deleted=False
            ).filter(
                HotspotORM.hot_score >= threshold
            ).order_by(
                HotspotORM.hot_score.desc()
            ).limit(10).all()
            
            pushed_count = 0
            for hotspot in hotspots:
                hotspot_dict = {
                    'title': hotspot.title,
                    'hot_score': hotspot.hot_score,
                    'category': hotspot.category,
                    'sentiment': hotspot.sentiment,
                    'source': hotspot.source,
                    'summary': hotspot.summary,
                    'url': hotspot.url
                }
                
                results = self.push_hotspot(hotspot_dict)
                
                # 如果至少有一个渠道成功，标记为已推送
                if any(results.values()):
                    hotspot.is_pushed = True
                    pushed_count += 1
            
            session.commit()
            logger.info(f"阈值推送完成: {pushed_count} 条")
            return pushed_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"阈值推送失败: {e}")
            return 0
        finally:
            session.close()
    
    def _format_sentiment(self, sentiment: str) -> str:
        """格式化情感显示"""
        mapping = {
            'positive': '😊 正面',
            'negative': '😔 负面',
            'neutral': '😐 中性'
        }
        return mapping.get(sentiment, sentiment)
    
    def test(self, channel: str = None) -> Dict[str, bool]:
        """测试推送"""
        title = "🧪 推送测试"
        content = "这是一条测试消息，如果您收到说明推送配置正确！"
        
        if channel:
            return self.send(title, content, channels=[channel])
        else:
            return self.send(title, content)


class PushScheduler:
    """推送调度器"""

    def __init__(self, push_service: PushService = None):
        self.push_service = push_service or PushService()
        self.running = False
        self._urgent_detector = None
        self._urgent_push = None

    @property
    def urgent_detector(self):
        """延迟初始化 urgent_detector，避免循环导入"""
        if self._urgent_detector is None:
            from ..urgent_detector import UrgentHotspotDetector
            self._urgent_detector = UrgentHotspotDetector()
        return self._urgent_detector

    @property
    def urgent_push(self):
        """延迟初始化 urgent_push，避免循环导入"""
        if self._urgent_push is None:
            from ..urgent_detector import UrgentPushService
            self._urgent_push = UrgentPushService()
        return self._urgent_push
    
    def start(self, mode: str = 'threshold', interval_minutes: int = 10):
        """
        启动推送调度
        
        Args:
            mode: 推送模式 - threshold(阈值) / daily(每日) / realtime(实时)
            interval_minutes: 检查间隔（分钟）
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        self.scheduler = BackgroundScheduler()
        
        if mode == 'threshold':
            self.scheduler.add_job(
                self._threshold_push_job,
                'interval',
                minutes=interval_minutes,
                id='push_job'
            )
        elif mode == 'daily':
            self.scheduler.add_job(
                self._daily_push_job,
                CronTrigger(hour=9, minute=0),
                id='push_job'
            )
        elif mode == 'realtime':
            self.scheduler.add_job(
                self._realtime_push_job,
                'interval',
                minutes=1,
                id='push_job'
            )
        
        # 添加紧急热点扫描任务（每5分钟检查一次）
        self.scheduler.add_job(
            self._urgent_scan_job,
            'interval',
            minutes=5,
            id='urgent_scan_job'
        )
        
        # 添加紧急热点推送任务（每10分钟推送一次）
        self.scheduler.add_job(
            self._urgent_push_job,
            'interval',
            minutes=10,
            id='urgent_push_job'
        )
        
        self.scheduler.start()
        self.running = True
        logger.info(f"推送调度已启动，模式: {mode}")
    
    def _threshold_push_job(self):
        """阈值推送任务"""
        try:
            self.push_service.check_and_push()
        except Exception as e:
            logger.error(f"阈值推送任务失败: {e}")
    
    def _daily_push_job(self):
        """每日推送任务"""
        try:
            from datetime import datetime, timedelta
            
            session = self.push_service.db.get_session()
            yesterday = datetime.now() - timedelta(days=1)
            
            hotspots = session.query(HotspotORM).filter(
                HotspotORM.crawl_time >= yesterday
            ).order_by(
                HotspotORM.hot_score.desc()
            ).limit(20).all()
            
            hotspot_dicts = [
                {
                    'title': h.title,
                    'hot_score': h.hot_score,
                    'category': h.category
                }
                for h in hotspots
            ]
            
            self.push_service.push_daily_summary(hotspot_dicts)
            session.close()
            
        except Exception as e:
            logger.error(f"每日推送任务失败: {e}")
    
    def _realtime_push_job(self):
        """实时推送任务"""
        # 实时推送在数据入库时触发，这里仅做状态检查
        pass
    
    def _urgent_scan_job(self):
        """紧急热点扫描任务"""
        try:
            config = get_config()
            urgent_config = config.get('urgent_hotspot', {})
            
            if not urgent_config.get('enabled', True):
                return
            
            # 扫描最近1小时的热点
            urgent_ids = self.urgent_detector.scan_and_mark_urgent(hours=1)
            if urgent_ids:
                logger.info(f"紧急扫描发现 {len(urgent_ids)} 个新紧急热点")
        except Exception as e:
            logger.error(f"紧急扫描任务失败: {e}")
    
    def _urgent_push_job(self):
        """紧急热点推送任务"""
        try:
            config = get_config()
            urgent_config = config.get('urgent_hotspot', {})
            
            if not urgent_config.get('enabled', True):
                return
            
            if not urgent_config.get('auto_push', True):
                return
            
            # 推送未确认的紧急热点
            count = self.urgent_push.check_and_push_urgent(self.push_service)
            if count > 0:
                logger.info(f"紧急推送任务完成: {count} 条")
        except Exception as e:
            logger.error(f"紧急推送任务失败: {e}")
    
    def stop(self):
        """停止推送调度"""
        if self.running and self.scheduler:
            self.scheduler.shutdown()
            self.running = False
            logger.info("推送调度已停止")
