"""
监控服务管理模块
管理定时爬虫的启动、停止、状态查询
"""

from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from .crawler.engine import CrawlerEngine, ScheduledCrawler
from .config_loader import get_config


class MonitorService:
    """监控服务管理器 - 单例模式"""
    
    _instance = None
    _scheduled_crawler: Optional[ScheduledCrawler] = None
    _crawler_engine: Optional[CrawlerEngine] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._start_time: Optional[datetime] = None
        self._last_crawl_time: Optional[datetime] = None
        self._crawl_count = 0
        
    def initialize(self, enable_detail_crawl: bool = True):
        """初始化监控服务"""
        if self._crawler_engine is None:
            self._crawler_engine = CrawlerEngine(enable_two_level=enable_detail_crawl)
            logger.info("✅ 爬虫引擎初始化完成")
        
        if self._scheduled_crawler is None:
            self._scheduled_crawler = ScheduledCrawler(
                crawler=self._crawler_engine,
                enable_detail_crawl=enable_detail_crawl,
                monitor_service=self  # 传递监控服务实例
            )
            logger.info("✅ 定时爬虫调度器初始化完成")
    
    def start(self, interval_minutes: int = None) -> bool:
        """启动监控服务"""
        try:
            if self._scheduled_crawler is None:
                self.initialize()
            
            if self._scheduled_crawler.running:
                logger.warning("监控服务已在运行中")
                return True
            
            # 获取配置中的间隔
            if interval_minutes is None:
                config = get_config()
                interval_minutes = config.general_config.get('monitor_interval', 30)
            
            self._scheduled_crawler.start(interval_minutes=interval_minutes)
            self._start_time = datetime.now()
            logger.info(f"🚀 监控服务已启动，间隔: {interval_minutes}分钟")
            return True
            
        except Exception as e:
            logger.error(f"启动监控服务失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止监控服务"""
        try:
            if self._scheduled_crawler and self._scheduled_crawler.running:
                self._scheduled_crawler.stop()
                self._start_time = None
                logger.info("🛑 监控服务已停止")
                return True
            else:
                logger.warning("监控服务未在运行")
                return False
                
        except Exception as e:
            logger.error(f"停止监控服务失败: {e}")
            return False
    
    def restart(self, interval_minutes: int = None) -> bool:
        """重启监控服务"""
        self.stop()
        return self.start(interval_minutes)
    
    def update_interval(self, interval_minutes: int) -> bool:
        """更新监控间隔（实时生效）"""
        try:
            if self._scheduled_crawler and self._scheduled_crawler.running:
                # 先停止再启动以应用新间隔
                self._scheduled_crawler.stop()
                self._scheduled_crawler.start(interval_minutes=interval_minutes)
                logger.info(f"🔄 监控间隔已更新为: {interval_minutes}分钟")
                return True
            else:
                # 服务未运行，只更新配置
                logger.info(f"📋 监控间隔已设置为: {interval_minutes}分钟（服务未启动）")
                return True
                
        except Exception as e:
            logger.error(f"更新监控间隔失败: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        config = get_config()
        interval = config.general_config.get('monitor_interval', 30)
        
        if self._scheduled_crawler is None:
            return {
                'running': False,
                'initialized': False,
                'interval_minutes': interval,
                'start_time': None,
                'uptime_seconds': 0,
                'last_crawl_time': None,
                'crawl_count': 0,
                'next_run_time': None
            }
        
        # 计算运行时间
        uptime = 0
        if self._start_time and self._scheduled_crawler.running:
            uptime = (datetime.now() - self._start_time).total_seconds()
        
        # 获取下次执行时间
        next_run_time = None
        if self._scheduled_crawler.running and self._scheduled_crawler.scheduler:
            try:
                # 检查调度器是否正在运行 (APScheduler: STATE_STOPPED=0, STATE_RUNNING=1, STATE_PAUSED=2)
                from apscheduler.schedulers.base import STATE_RUNNING
                scheduler_state = getattr(self._scheduled_crawler.scheduler, 'state', None)
                if scheduler_state == STATE_RUNNING:
                    job = self._scheduled_crawler.scheduler.get_job('crawl_job')
                    if job and job.next_run_time:
                        next_run_time = job.next_run_time.isoformat()
            except Exception:
                pass
        
        return {
            'running': self._scheduled_crawler.running,
            'initialized': True,
            'interval_minutes': interval,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'uptime_seconds': int(uptime),
            'last_crawl_time': self._last_crawl_time.isoformat() if self._last_crawl_time else None,
            'crawl_count': self._crawl_count,
            'next_run_time': next_run_time
        }
    
    def run_once(self) -> bool:
        """立即执行一次抓取"""
        try:
            if self._scheduled_crawler:
                self._scheduled_crawler.run_once()
                # 注意: 计数在 _crawl_job 中已更新，这里不再重复增加
                return True
            return False
        except Exception as e:
            logger.error(f"立即抓取失败: {e}")
            return False
    
    def is_running(self) -> bool:
        """检查监控是否正在运行"""
        return self._scheduled_crawler is not None and self._scheduled_crawler.running


# 全局监控服务实例
monitor_service = MonitorService()


def get_monitor_service() -> MonitorService:
    """获取监控服务实例"""
    return monitor_service
