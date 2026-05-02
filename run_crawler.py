#!/usr/bin/env python3
"""
AI热点监控 - 命令行爬虫执行脚本
用于GitHub Actions定时执行爬虫任务
"""

import os
import sys
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
project_root = Path(__file__).parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# 添加项目路径
sys.path.insert(0, str(project_root))

from loguru import logger
from core.config_loader import get_config
from core.models import init_database
from core.crawler.engine import CrawlerEngine
from core.crawler.task_manager import task_manager
from core.filter.analyzer import HotspotAnalyzer
from core.ai_service import get_ai_service
from core.email_service import get_email_service, EmailConfig
from core.email_notification_service import EmailNotificationService

def setup_logging():
    """配置日志"""
    os.makedirs('logs', exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        colorize=True
    )
    logger.add(
        "logs/crawler.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8"
    )

def init_services():
    """初始化所有服务"""
    logger.info("🚀 初始化服务...")
    
    # 初始化数据库
    db = init_database()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化AI服务
    config = get_config()
    ai_config = config.ai_service_config
    provider = ai_config.get('provider', 'moonshot')
    
    if provider in ['moonshot', 'kimi']:
        ai_api_key = os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
    else:
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or ai_config.get('api_key')
    
    ai_service = None
    if ai_api_key:
        ai_service = get_ai_service(ai_api_key, provider)
        logger.info(f"✅ AI服务初始化完成 (提供商: {provider})")
    else:
        logger.warning("⚠️ AI服务未配置")
    
    # 初始化邮件服务
    email_config = None
    if os.getenv("EMAIL_SMTP_SERVER"):
        email_config = EmailConfig(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            username=os.getenv("EMAIL_USERNAME", ""),
            password=os.getenv("EMAIL_PASSWORD", ""),
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
            from_name=os.getenv("EMAIL_FROM_NAME", "AI热点监控")
        )
    
    email_service = get_email_service(email_config)
    if email_config:
        logger.info("✅ 邮件服务初始化完成")
    else:
        logger.warning("⚠️ 邮件服务未配置")
    
    return db, ai_service, email_service

def run_crawler_job():
    """执行爬虫任务"""
    logger.info("=" * 60)
    logger.info("🎯 AI热点监控 - 开始执行定时抓取任务")
    logger.info("=" * 60)
    
    # 初始化服务
    db, ai_service, email_service = init_services()
    
    # 创建爬虫引擎
    crawler_engine = CrawlerEngine()
    logger.info("✅ 爬虫引擎初始化完成")
    
    # 创建任务
    task_id = task_manager.create_task()
    logger.info(f"📋 任务ID: {task_id}")
    
    try:
        # 获取启用的数据源数量
        config = get_config()
        data_sources = config.data_sources
        enabled_sources = {k: v for k, v in data_sources.items() if v.get('enabled', True)}
        total_sources = len(enabled_sources)
        
        # 检查社交媒体源
        social_config = config.get('social_sources', {})
        if social_config.get('hackernews', {}).get('enabled', True):
            total_sources += 1
        if social_config.get('weibo', {}).get('enabled', True):
            total_sources += 1
        
        logger.info(f"📊 启用的数据源: {total_sources} 个")
        
        # 开始任务
        task_manager.start_task(task_id, total_sources)
        
        # 创建分析器
        analyzer = HotspotAnalyzer()
        
        # 执行抓取
        logger.info("🔍 开始抓取数据...")
        stats = crawler_engine.crawl_and_save(
            analyzer=analyzer,
            task_id=task_id,
            fast_mode=False,
            enable_email_notification=True
        )
        
        # 完成任务
        task_manager.complete_task(task_id, stats)
        
        # 输出统计信息
        logger.info("=" * 60)
        logger.info("✅ 抓取任务完成!")
        logger.info(f"📈 抓取统计:")
        logger.info(f"   - 列表页抓取: {stats.get('list_crawl', {}).get('saved', 0)} 条")
        logger.info(f"   - 详情页抓取: {stats.get('detail_crawl', {}).get('saved', 0)} 条")
        logger.info(f"   - 社交媒体: {stats.get('social_crawl', {}).get('total', 0)} 条")
        logger.info(f"   - AI分析: {stats.get('ai_analysis', {}).get('total', 0)} 条")
        logger.info("=" * 60)
        
        # 发送邮件通知
        if email_service and stats:
            try:
                email_notify = EmailNotificationService(email_service)
                email_stats = {
                    'total_crawled': stats.get('list_crawl', {}).get('saved', 0),
                    'new_hotspots': stats.get('total_new', 0),
                    'ai_analyzed': stats.get('ai_analysis', {}).get('total', 0),
                    'crawl_time': datetime.now()
                }
                # 获取新增的热点
                from core.models import get_db
                from sqlalchemy import desc
                from core.models import HotspotORM
                
                db_gen = get_db()
                db_session = next(db_gen)
                
                new_hotspots = db_session.query(HotspotORM).order_by(
                    desc(HotspotORM.created_at)
                ).limit(email_stats['new_hotspots']).all()
                
                email_notify.on_crawl_completed(email_stats, new_hotspots)
                logger.info("📧 邮件通知已发送")
            except Exception as e:
                logger.error(f"❌ 邮件通知发送失败: {e}")
        
        return 0  # 成功
        
    except Exception as e:
        logger.error(f"❌ 抓取任务失败: {e}")
        task_manager.fail_task(task_id, str(e))
        return 1  # 失败

if __name__ == "__main__":
    from datetime import datetime
    
    setup_logging()
    exit_code = run_crawler_job()
    sys.exit(exit_code)
