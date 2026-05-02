"""
爬虫引擎 - 多线程抓取引擎，整合所有抓取功能
支持两级抓取：列表页抓取 + 详情页抓取
新增：社交媒体数据源抓取
"""

import time
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from loguru import logger

from ..config_loader import get_config
from ..models import get_db, HotspotORM
from .fetcher import Fetcher
from .parser import ContentParser
from .detail_crawler import DetailCrawler, DetailTask
from .task_manager import task_manager
from .social_sources import SocialSourceAggregator
from .playwright_fetcher import PlaywrightFetcher, PLAYWRIGHT_SOURCES

# 尝试导入WebSocket管理器（可选依赖）
try:
    from ..websocket import websocket_manager, SOCKET_IO_AVAILABLE
except ImportError:
    websocket_manager = None
    SOCKET_IO_AVAILABLE = False


@dataclass
class CrawlResult:
    """抓取结果"""
    source: str
    source_id: str
    success: bool
    items: List[Dict]
    message: str
    crawl_time: datetime
    saved_ids: List[int] = field(default_factory=list)  # 保存的热点ID列表


class TwoLevelCrawlStats:
    """两级抓取统计"""
    def __init__(self):
        self.list_crawl_stats = {
            'total': 0,
            'success': 0,
            'failed': 0
        }
        self.detail_crawl_stats = {
            'queued': 0,
            'success': 0,
            'failed': 0
        }
    
    def to_dict(self) -> Dict:
        return {
            'list_crawl': self.list_crawl_stats.copy(),
            'detail_crawl': self.detail_crawl_stats.copy()
        }


class CrawlerEngine:
    """
    爬虫引擎 - 支持两级抓取模式
    
    两级抓取流程：
    1. 列表页抓取：获取文章URL和摘要（第一阶段）
    2. 详情页抓取：获取完整文章内容（第二阶段）
    """
    
    def __init__(self, max_workers: int = None, enable_two_level: bool = True, enable_social: bool = True):
        self.config = get_config()
        self.system_config = self.config.system_config
        self.max_workers = max_workers or self.system_config.get('concurrency', {}).get('max_workers', 5)
        
        self.fetcher = Fetcher()
        self.parser = ContentParser()
        self.db = get_db()
        
        # 详情页抓取器（两级抓取）
        self.enable_two_level = enable_two_level
        if enable_two_level:
            self.detail_crawler = DetailCrawler(
                max_workers=3,
                delay_range=(2, 5)
            )
        else:
            self.detail_crawler = None
        
        # 社交媒体数据源（V3.1新增）
        self.enable_social = enable_social
        self.social_sources = None
        if enable_social:
            try:
                import os
                social_config = self.config.get('social_sources', {})
                self.social_sources = SocialSourceAggregator(
                    twitter_api_key=os.getenv("TWITTER_API_KEY"),
                    enable_bing=social_config.get('bing', {}).get('enabled', True),
                    enable_hackernews=social_config.get('hackernews', {}).get('enabled', True),
                    enable_sogou=social_config.get('sogou', {}).get('enabled', True),
                    enable_bilibili=social_config.get('bilibili', {}).get('enabled', True),
                    enable_weibo=social_config.get('weibo', {}).get('enabled', True)
                )
                logger.info("✅ 社交媒体数据源初始化完成")
            except Exception as e:
                logger.warning(f"⚠️ 社交媒体数据源初始化失败: {e}")
                self.social_sources = None
        
        # 示例数据（用于抓取失败时降级）
        self._demo_data = self._generate_demo_data()
        
        # Playwright 抓取器（用于JS渲染页面）
        self._playwright_fetcher: Optional[PlaywrightFetcher] = None
        
        # 统计信息
        self.stats = TwoLevelCrawlStats()
    
    def _generate_demo_data(self) -> List[Dict]:
        """生成示例数据（用于演示和降级）"""
        return [
            {
                "title": "OpenAI发布GPT-5预览版，多模态能力大幅提升",
                "source": "示例数据",
                "url": "https://example.com/news/1",
                "summary": "OpenAI今日发布了GPT-5预览版本，新模型在图像理解、视频生成和多语言处理方面都有显著改进...",
                "publish_time": datetime.now(),
                "views": 15000,
                "interactions": 2300
            },
            {
                "title": "Google DeepMind推出新型蛋白质结构预测模型",
                "source": "示例数据",
                "url": "https://example.com/news/2",
                "summary": "DeepMind团队发布了AlphaFold的升级版本，在药物研发领域展现出更大潜力...",
                "publish_time": datetime.now(),
                "views": 12000,
                "interactions": 1800
            },
            {
                "title": "国内首个千亿参数大模型开源，性能对标GPT-4",
                "source": "示例数据",
                "url": "https://example.com/news/3",
                "summary": "国内AI公司宣布开源其千亿参数大模型，在多项 benchmark 上达到GPT-4水平...",
                "publish_time": datetime.now(),
                "views": 20000,
                "interactions": 3500
            },
            {
                "title": "Meta发布新一代AR眼镜，集成实时AI翻译功能",
                "source": "示例数据",
                "url": "https://example.com/news/4",
                "summary": "Meta在年度开发者大会上展示了新款AR眼镜，内置AI芯片支持40种语言的实时翻译...",
                "publish_time": datetime.now(),
                "views": 18000,
                "interactions": 2800
            },
            {
                "title": "自动驾驶新进展：L4级无人车获准在主城区运营",
                "source": "示例数据",
                "url": "https://example.com/news/5",
                "summary": "多家自动驾驶公司获得L4级无人车运营牌照，标志着自动驾驶商业化进入新阶段...",
                "publish_time": datetime.now(),
                "views": 25000,
                "interactions": 4200
            }
        ]
    
    def crawl_source(self, source_id: str, source_config: Dict) -> CrawlResult:
        """
        抓取单个数据源（列表页抓取 - 第一阶段）
        
        Args:
            source_id: 数据源ID
            source_config: 数据源配置
        
        Returns:
            抓取结果
        """
        start_time = datetime.now()
        source_name = source_config.get('name', source_id)
        
        try:
            logger.info(f"开始抓取列表页: {source_name}")
            
            url = source_config.get('url', '')
            selectors = source_config.get('selectors', {})
            
            if not url or not selectors:
                return CrawlResult(
                    source=source_name,
                    source_id=source_id,
                    success=False,
                    items=[],
                    message="配置缺失",
                    crawl_time=start_time
                )
            
            # 判断是否需要使用 Playwright（JS渲染页面）
            if source_id in PLAYWRIGHT_SOURCES:
                logger.info(f"使用 Playwright 抓取 JS 渲染页面: {source_name}")
                html = self._fetch_with_playwright(url, source_config)
            else:
                # 普通 HTTP 抓取
                html = self.fetcher.fetch_html(url)
            
            if not html:
                logger.warning(f"抓取失败: {source_name}，切换到示例数据")
                # 返回示例数据作为降级
                demo_items = self._get_demo_items_for_source(source_name)
                return CrawlResult(
                    source=source_name,
                    source_id=source_id,
                    success=True,  # 降级视为成功
                    items=demo_items,
                    message="使用示例数据（抓取失败降级）",
                    crawl_time=start_time
                )
            
            # 解析内容
            items = self.parser.parse_html(html, selectors, url)
            
            # 添加来源信息
            for item in items:
                item['source'] = source_name
                item['source_id'] = source_id  # 添加source_id用于详情页抓取
                if not item.get('publish_time'):
                    item['publish_time'] = datetime.now()
            
            logger.info(f"列表页抓取完成: {source_name}, 获取 {len(items)} 条数据")
            
            return CrawlResult(
                source=source_name,
                source_id=source_id,
                success=True,
                items=items,
                message=f"成功获取 {len(items)} 条数据",
                crawl_time=start_time
            )
            
        except Exception as e:
            logger.error(f"抓取异常 {source_name}: {e}")
            # 异常时也返回示例数据
            demo_items = self._get_demo_items_for_source(source_name)
            return CrawlResult(
                source=source_name,
                source_id=source_id,
                success=True,  # 降级视为成功
                items=demo_items,
                message=f"使用示例数据（异常: {str(e)[:50]}）",
                crawl_time=start_time
            )
    
    def _get_demo_items_for_source(self, source_name: str) -> List[Dict]:
        """获取特定来源的示例数据"""
        items = []
        for i, demo in enumerate(self._demo_data):
            item = demo.copy()
            item['source'] = source_name
            item['url'] = f"https://example.com/{source_name}/{i}"
            item['title'] = f"[{source_name}] {demo['title']}"
            items.append(item)
        return items

    def _fetch_with_playwright(self, url: str, source_config: Dict) -> Optional[str]:
        """
        使用 Playwright 抓取 JS 渲染页面（同步版本），失败时尝试普通 HTTP 抓取
        
        Args:
            url: 页面 URL
            source_config: 数据源配置
            
        Returns:
            HTML 内容
        """
        html = None
        
        # 首先尝试 Playwright 抓取
        try:
            # 初始化 Playwright fetcher（延迟初始化）
            if self._playwright_fetcher is None:
                self._playwright_fetcher = PlaywrightFetcher(headless=True, timeout=30)
                logger.info("Playwright 抓取器已初始化")
            
            selectors = source_config.get('selectors', {})
            container_selector = selectors.get('container', '')
            
            # 调用增强版同步抓取方法
            html = self._playwright_fetcher.fetch(
                url,
                wait_for=container_selector or None,
                wait_timeout=10,
                max_retries=2
            )
            
            if html and len(html) > 3000:
                logger.info(f"✅ Playwright 抓取成功: {url[:60]}...")
                return html
            else:
                logger.warning(f"⚠️ Playwright 抓取结果异常，尝试 HTTP 备用抓取")
                
        except ImportError as e:
            logger.error(f"Playwright 未安装，将使用普通 HTTP 抓取: {e}")
        except Exception as e:
            logger.error(f"Playwright 抓取失败: {e}")
        
        # Playwright 失败或结果异常，尝试普通 HTTP 抓取作为备用
        try:
            logger.info(f"🔄 尝试使用普通 HTTP 抓取作为备用: {url[:60]}...")
            html = self.fetcher.fetch_html(url)
            
            if html and len(html) > 1000:
                logger.info(f"✅ HTTP 备用抓取成功: {url[:60]}... (大小: {len(html)} bytes)")
                return html
            else:
                logger.warning(f"⚠️ HTTP 备用抓取结果太短或为空")
                
        except Exception as e:
            logger.error(f"❌ HTTP 备用抓取也失败: {e}")
        
        return None
    
    def crawl_all(self, callback: Callable = None) -> List[CrawlResult]:
        """
        抓取所有启用的数据源
        
        Args:
            callback: 进度回调函数 (current, total, result)
        
        Returns:
            所有抓取结果
        """
        data_sources = self.config.data_sources
        enabled_sources = {
            k: v for k, v in data_sources.items() 
            if v.get('enabled', True)
        }
        
        results = []
        
        # 分离 Playwright 源和普通源（Playwright 需要在主线程中运行）
        playwright_sources = {}
        normal_sources = {}
        for sid, cfg in enabled_sources.items():
            if sid in PLAYWRIGHT_SOURCES:
                playwright_sources[sid] = cfg
            else:
                normal_sources[sid] = cfg
        
        total = len(enabled_sources)
        completed = 0
        
        logger.info(f"开始批量抓取，共 {total} 个数据源 (普通: {len(normal_sources)}, Playwright: {len(playwright_sources)})")
        
        # 步骤1: 使用线程池抓取普通数据源
        if normal_sources:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_source = {
                    executor.submit(self.crawl_source, sid, cfg): sid 
                    for sid, cfg in normal_sources.items()
                }
                
                for future in as_completed(future_to_source):
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if callback:
                        callback(completed, total, result)
                    
                    # 添加延迟避免请求过快
                    time.sleep(random.uniform(1, 2))
        
        # 步骤2: 抓取 Playwright 数据源（使用线程池带超时）
        if playwright_sources:
            logger.info(f"开始抓取 {len(playwright_sources)} 个 Playwright 数据源（带60秒超时）")
            
            # 使用单线程池来执行 Playwright 任务，并设置超时
            with ThreadPoolExecutor(max_workers=1) as playwright_executor:
                for sid, cfg in playwright_sources.items():
                    future = playwright_executor.submit(self.crawl_source, sid, cfg)
                    try:
                        # 设置60秒超时
                        result = future.result(timeout=60)
                        results.append(result)
                        completed += 1
                        
                        if callback:
                            callback(completed, total, result)
                            
                    except FutureTimeoutError:
                        logger.error(f"⏱️ Playwright 抓取超时: {cfg.get('name', sid)} (超过60秒)")
                        # 创建超时结果
                        from datetime import datetime
                        timeout_result = CrawlResult(
                            source=cfg.get('name', sid),
                            source_id=sid,
                            success=False,
                            items=[],
                            message="抓取超时(超过60秒)",
                            crawl_time=datetime.now()
                        )
                        results.append(timeout_result)
                        completed += 1
                        
                        if callback:
                            callback(completed, total, timeout_result)
                    except Exception as e:
                        logger.error(f"❌ Playwright 抓取异常: {cfg.get('name', sid)} - {e}")
                        from datetime import datetime
                        error_result = CrawlResult(
                            source=cfg.get('name', sid),
                            source_id=sid,
                            success=False,
                            items=[],
                            message=f"抓取异常: {str(e)[:50]}",
                            crawl_time=datetime.now()
                        )
                        results.append(error_result)
                        completed += 1
                        
                        if callback:
                            callback(completed, total, error_result)
                    
                    # 添加延迟避免请求过快
                    time.sleep(random.uniform(2, 3))
        
        logger.info(f"批量抓取完成，成功 {sum(1 for r in results if r.success)}/{len(results)}")
        return results
    
    def _crawl_social_sync(self, keywords: List[str] = None) -> List[CrawlResult]:
        """
        同步方式抓取社交媒体数据（在异步事件循环中执行）
        注意：进度更新由调用方统一处理，此函数只返回结果
        
        Args:
            keywords: 搜索关键词列表，默认使用配置中的关键词
            
        Returns:
            抓取结果列表
        """
        if not self.social_sources:
            return []
        
        results = []
        
        try:
            # 获取热门内容
            trending_task = self.social_sources.get_trending()
            trending_results = asyncio.run(trending_task)
            
            for source_name, items in trending_results.items():
                source_display_name = f"{source_name}_热门"
                try:
                    if items:
                        # 转换为标准格式
                        formatted_items = []
                        for item in items:
                            formatted_item = {
                                'title': item.title,
                                'source': source_display_name,
                                'url': item.url,
                                'summary': item.content[:500] if item.content else '',
                                'content': item.content,
                                'publish_time': item.published_at or datetime.now(),
                                'views': item.views,
                                'interactions': item.likes + item.comments + item.shares,
                                'hot_score': (item.views * 0.4 + item.likes * 0.6) / 100
                            }
                            formatted_items.append(formatted_item)
                        
                        results.append(CrawlResult(
                            source=source_display_name,
                            source_id=source_name,
                            success=True,
                            items=formatted_items,
                            message=f"成功获取 {len(formatted_items)} 条热门数据",
                            crawl_time=datetime.now()
                        ))
                        logger.info(f"社交媒体抓取 {source_name}: {len(formatted_items)} 条")
                    else:
                        # 没有数据也返回结果，让调用方统一更新进度
                        results.append(CrawlResult(
                            source=source_display_name,
                            source_id=source_name,
                            success=True,
                            items=[],
                            message="没有获取到数据",
                            crawl_time=datetime.now()
                        ))
                except Exception as e:
                    logger.error(f"处理 {source_name} 数据失败: {e}")
                    # 失败也返回结果
                    results.append(CrawlResult(
                        source=source_display_name,
                        source_id=source_name,
                        success=False,
                        items=[],
                        message=f"处理失败: {str(e)[:50]}",
                        crawl_time=datetime.now()
                    ))
        
        except Exception as e:
            logger.error(f"社交媒体抓取失败: {e}")
        
        return results
    
    def crawl_and_save(self, filter_engine=None, enable_detail_crawl: bool = True, 
                       task_id: str = None, enable_social: bool = True,
                       analyzer=None, fast_mode: bool = False,
                       enable_email_notification: bool = True) -> Dict[str, Any]:
        """
        抓取并保存到数据库（支持两级抓取 + 社交媒体 + AI分析 + 邮件通知）
        
        Args:
            filter_engine: AI筛选引擎（已弃用，使用analyzer替代）
            enable_detail_crawl: 是否启用详情页抓取（第二阶段）
            task_id: 任务ID（用于进度跟踪）
            enable_social: 是否启用社交媒体抓取
            analyzer: 热点分析器（V3.1 AI集成）用于AI分析
            fast_mode: 快速模式，跳过AI分析和详情页抓取，速度提升10倍以上
            enable_email_notification: 是否启用邮件通知（默认为True）
        
        Returns:
            处理统计信息
        """
        from ..filter.analyzer import HotspotAnalyzer
        
        # 如果没有提供analyzer，创建一个
        if analyzer is None:
            analyzer = HotspotAnalyzer()
        
        results = self.crawl_all()
        
        # 抓取社交媒体数据
        if enable_social and self.enable_social and self.social_sources:
            logger.info("开始抓取社交媒体数据...")
            social_results = self._crawl_social_sync()
            results.extend(social_results)
        
        stats = {
            'total_crawled': 0,
            'total_filtered': 0,
            'total_saved': 0,
            'total_new': 0,  # 新增热点数量
            'total_ai_analyzed': 0,
            'sources': {},
            'two_level_crawl': {
                'enabled': self.enable_two_level and enable_detail_crawl,
                'detail_tasks': 0,
                'detail_success': 0
            },
            'social_crawl': {
                'enabled': enable_social and self.enable_social,
                'sources': []
            },
            'ai_analysis': {
                'enabled': analyzer._is_ai_enabled(),
                'model': analyzer.config.get('ai_service.model', 'unknown')
            },
            'email_notification': {
                'enabled': enable_email_notification,
                'sent': False,
                'message': ''
            }
        }
        
        all_saved_items = []  # 用于详情页抓取
        all_new_hotspots = []  # 用于邮件通知的新热点列表
        
        # 快速模式日志提示
        if fast_mode:
            logger.info("⚡ 启用快速模式：跳过AI分析和详情页抓取")
        
        logger.info(f"开始处理抓取结果，共 {len(results)} 个数据源")
        
        for result in results:
            source_stats = {
                'crawled': len(result.items),
                'success': result.success,
                'message': result.message,
                'filtered': 0,
                'saved': 0
            }
            stats['sources'][result.source] = source_stats
            stats['total_crawled'] += len(result.items)
            
            logger.info(f"[{result.source}] 原始数据: {len(result.items)} 条")
            
            if not result.success or not result.items:
                logger.warning(f"[{result.source}] 抓取失败或无数据: {result.message}")
                # 更新进度
                if task_id:
                    task_manager.update_progress(
                        task_id, result.source, 
                        len(result.items), 0, 0
                    )
                continue
            
            # 根据模式选择分析方式
            if fast_mode:
                # 快速模式：只使用关键词过滤，跳过AI分析
                # 使用filter_engine进行简单关键词匹配，速度极快
                analyzed_items = self._fast_filter_items(result.items, analyzer.filter_engine)
                filtered_count = len(result.items) - len(analyzed_items)
                stats['ai_analysis']['enabled'] = False  # 快速模式下禁用AI分析
            else:
                # 标准模式：使用批量并发AI分析（性能优化）
                # 使用并发分析替代逐个分析，速度提升5倍以上
                analyzed_items = analyzer.analyze_batch_sync(result.items, max_workers=5)
                filtered_count = len(result.items) - len(analyzed_items)
            
            logger.info(f"[{result.source}] 分析通过: {len(analyzed_items)} 条, 被过滤: {filtered_count} 条")
            
            source_stats['filtered'] = len(analyzed_items)
            stats['total_filtered'] += len(analyzed_items)
            if not fast_mode:
                stats['total_ai_analyzed'] += len(analyzed_items)
            
            # 保存到数据库
            saved_items = self._save_to_db_with_ids(analyzed_items)
            
            # 统计新增数量，收集新热点数据
            new_items = [item for item in saved_items if item.get('is_new', False)]
            new_count = len(new_items)
            all_new_hotspots.extend(new_items)  # 收集所有新热点用于邮件通知
            
            logger.info(f"[{result.source}] 保存到数据库: {len(saved_items)} 条 (新增 {new_count} 条)")
            
            source_stats['saved'] = len(saved_items)
            source_stats['new'] = new_count  # 记录该数据源新增数量
            stats['total_saved'] += len(saved_items)
            stats['total_new'] += new_count
            
            # 更新进度（在分析和保存完成后）- 修复统计显示问题
            if task_id:
                task_manager.update_progress(
                    task_id, result.source,
                    len(result.items), len(analyzed_items), len(saved_items), new_count
                )
            
            # 准备详情页抓取任务（快速模式下跳过）
            if not fast_mode and self.enable_two_level and enable_detail_crawl and self.detail_crawler:
                all_saved_items.extend(saved_items)
        
        logger.info(f"抓取处理完成: 原始 {stats['total_crawled']} 条, 分析通过 {stats['total_filtered']} 条, 保存 {stats['total_saved']} 条, 新增 {stats['total_new']} 条")
        
        # 执行详情页抓取（第二阶段）- 快速模式下跳过
        if not fast_mode and self.enable_two_level and enable_detail_crawl and self.detail_crawler and all_saved_items:
            detail_stats = self._crawl_details(all_saved_items)
            stats['two_level_crawl']['detail_tasks'] = detail_stats.get('tasks', 0)
            stats['two_level_crawl']['detail_success'] = detail_stats.get('success', 0)
        else:
            stats['two_level_crawl']['enabled'] = False
        
        # WebSocket推送：广播抓取完成事件（如果有新数据保存）
        if stats['total_saved'] > 0 and SOCKET_IO_AVAILABLE and websocket_manager:
            try:
                # 使用异步方式推送，不阻塞当前线程
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    asyncio.create_task(
                        websocket_manager.broadcast_crawl_complete({
                            'saved': stats['total_saved'],
                            'filtered': stats['total_filtered'],
                            'crawled': stats['total_crawled']
                        })
                    )
                else:
                    # 如果没有运行的事件循环，使用 run_coroutine_threadsafe
                    asyncio.run_coroutine_threadsafe(
                        websocket_manager.broadcast_crawl_complete({
                            'saved': stats['total_saved'],
                            'filtered': stats['total_filtered'],
                            'crawled': stats['total_crawled']
                        }),
                        loop
                    )
                logger.info(f"WebSocket广播: 抓取完成，保存 {stats['total_saved']} 条数据")
            except Exception as e:
                logger.warning(f"WebSocket广播失败: {e}")
        
        # ========== 邮件通知自动化绑定 ==========
        if enable_email_notification:
            try:
                from ..email_notification_service import get_email_notification_service
                
                email_service = get_email_notification_service()
                email_result = email_service.on_crawl_completed(stats, all_new_hotspots)
                
                stats['email_notification']['sent'] = email_result.get('sent', False)
                stats['email_notification']['message'] = email_result.get('message', '')
                
                if email_result.get('should_send'):
                    if email_result.get('sent'):
                        logger.success(f"📧 邮件通知发送成功: {email_result['message']}")
                    else:
                        logger.error(f"📧 邮件通知发送失败: {email_result['message']}")
                else:
                    logger.info(f"📧 邮件通知跳过: {email_result['message']}")
                    
            except Exception as e:
                logger.error(f"📧 邮件通知处理异常: {e}")
                stats['email_notification']['message'] = f"处理异常: {str(e)}"
        else:
            stats['email_notification']['message'] = "邮件通知已禁用"
            logger.info("📧 邮件通知已禁用")
        
        return stats
    
    def _fast_filter_items(self, items: List[Dict], filter_engine) -> List[Dict]:
        """
        快速过滤items，只使用关键词匹配，跳过AI分析
        
        Args:
            items: 原始数据列表
            filter_engine: 筛选引擎
            
        Returns:
            过滤后的数据列表
        """
        results = []
        for item in items:
            filtered = filter_engine.filter_hotspot(item)
            if filtered:
                # 设置默认值（跳过AI分析）
                filtered['is_real'] = True
                filtered['relevance'] = 70  # 默认中等相关性
                filtered['relevance_reason'] = "快速模式：基于关键词匹配"
                filtered['importance'] = "medium"
                filtered['ai_summary'] = filtered.get('summary', '')[:100]
                filtered['keyword_mentioned'] = True
                filtered['matched_keywords'] = filtered.get('_matched_keywords', [])
                results.append(filtered)
        return results
    
    def _crawl_details(self, items: List[Dict]) -> Dict[str, int]:
        """
        执行详情页抓取（第二阶段）
        
        Args:
            items: 已保存的热点列表（包含id, url, source, source_id）
        
        Returns:
            详情页抓取统计
        """
        if not self.detail_crawler:
            return {'tasks': 0, 'success': 0}
        
        # 过滤出需要抓取详情页的项目（没有content或content太短）
        items_need_detail = [
            item for item in items 
            if not item.get('content') or len(item.get('content', '')) < 200
        ]
        
        if not items_need_detail:
            logger.info("没有需要抓取详情页的热点")
            return {'tasks': 0, 'success': 0}
        
        logger.info(f"开始详情页抓取，共 {len(items_need_detail)} 个任务")
        
        # 添加任务到队列
        added_count = 0
        for item in items_need_detail:
            # 确保 source_id 不为空 - 优先使用 source_id，如果没有则使用 source 名称反向查找
            source_id = item.get('source_id', '')
            source_name = item.get('source', '')
            
            # 如果没有 source_id，尝试从配置中查找
            if not source_id and source_name:
                for sid, cfg in self.config.data_sources.items():
                    if cfg.get('name') == source_name:
                        source_id = sid
                        break
            
            # 跳过示例数据
            url = item.get('url', '')
            if 'example.com' in url:
                logger.debug(f"跳过示例数据: {item.get('id')}")
                continue
            
            if self.detail_crawler.add_task(
                hotspot_id=item.get('id'),
                url=url,
                source=source_name,
                source_id=source_id
            ):
                added_count += 1
        
        if added_count == 0:
            logger.info("没有有效的详情页任务可处理")
            return {'tasks': 0, 'success': 0}
        
        # 立即处理队列
        results = self.detail_crawler.process_queue()
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"详情页抓取完成: 成功 {success_count}/{added_count}")
        
        return {
            'tasks': added_count,
            'success': success_count
        }
    
    def start_detail_crawler_worker(self, interval_seconds: int = 60):
        """启动详情页后台抓取器"""
        if self.detail_crawler:
            self.detail_crawler.start_background_worker(interval_seconds)
    
    def stop_detail_crawler_worker(self):
        """停止详情页后台抓取器"""
        if self.detail_crawler:
            self.detail_crawler.stop_background_worker()
    
    def get_detail_crawler_stats(self) -> Dict[str, int]:
        """获取详情页抓取统计"""
        if self.detail_crawler:
            return self.detail_crawler.get_stats()
        return {}
    
    def _save_to_db(self, items: List[Dict]) -> List[int]:
        """
        保存数据到数据库
        
        Returns:
            保存的热点ID列表（用于详情页抓取）
        """
        saved_items = self._save_items_internal(items, return_full_items=False)
        return [item['id'] for item in saved_items]
    
    def _save_to_db_with_ids(self, items: List[Dict]) -> List[Dict]:
        """
        保存数据到数据库，并返回包含ID的完整item数据
        
        Returns:
            保存的热点数据列表（包含id字段）
        """
        return self._save_items_internal(items, return_full_items=True)
    
    def _save_items_internal(self, items: List[Dict], return_full_items: bool = False) -> List[Dict]:
        """
        内部保存方法，统一处理数据库保存逻辑
        
        Args:
            items: 要保存的热点数据列表
            return_full_items: 是否返回完整的item数据（包含id）
        
        Returns:
            保存的热点数据列表（包含id字段）
        """
        import json

        if not items:
            return []

        # 过滤掉示例数据（example.com）
        valid_items = [
            item for item in items 
            if 'example.com' not in item.get('url', '')
        ]
        
        if len(valid_items) < len(items):
            logger.warning(f"过滤了 {len(items) - len(valid_items)} 条示例数据")
        
        if not valid_items:
            return []

        session = self.db.get_session()
        saved_items = []
        new_items = []  # 记录新增的热点

        try:
            for item in valid_items:
                # 检查是否已存在（根据URL去重）
                existing = session.query(HotspotORM).filter_by(
                    url=item.get('url', '')
                ).first()

                if existing:
                    # 更新热度
                    existing.hot_score = item.get('hot_score', existing.hot_score)
                    existing.views = item.get('views', existing.views)
                    existing.interactions = item.get('interactions', existing.interactions)
                    # 如果已有记录，添加到列表
                    saved_item = item.copy()
                    saved_item['id'] = existing.id
                    saved_item['is_new'] = False  # 标记为已存在
                    saved_items.append(saved_item)
                else:
                    # 处理AI分析理由
                    ai_analysis = item.get('ai_analysis')
                    ai_analysis_json = None
                    if ai_analysis:
                        if isinstance(ai_analysis, dict):
                            ai_analysis_json = json.dumps(ai_analysis, ensure_ascii=False)
                        else:
                            ai_analysis_json = json.dumps(ai_analysis.dict(), ensure_ascii=False)

                    # 创建新记录
                    hotspot = HotspotORM(
                        title=item.get('title', '')[:500],
                        source=item.get('source', ''),
                        url=item.get('url', ''),
                        summary=item.get('summary', '')[:5000] if item.get('summary') else None,
                        content=item.get('content', '')[:50000] if item.get('content') else None,
                        publish_time=item.get('publish_time'),
                        crawl_time=datetime.utcnow(),
                        hot_score=item.get('hot_score', 0.0),
                        views=item.get('views', 0),
                        interactions=item.get('interactions', 0),
                        sentiment=item.get('sentiment', 'neutral'),
                        category=item.get('category', '其他'),
                        keywords=item.get('keywords', ''),
                        ai_analysis=ai_analysis_json,
                        # AI深度分析字段（V3.1 AI集成新增）
                        is_real=item.get('is_real', True),
                        relevance=item.get('relevance', 50),
                        relevance_reason=item.get('relevance_reason'),
                        importance=item.get('importance', 'medium'),
                        ai_summary=item.get('ai_summary'),
                        keyword_mentioned=item.get('keyword_mentioned', False),
                        matched_keywords=','.join(item.get('matched_keywords', [])) if isinstance(item.get('matched_keywords'), list) else item.get('matched_keywords')
                    )
                    session.add(hotspot)
                    session.flush()  # 获取ID
                    
                    # 返回包含ID的完整item
                    saved_item = item.copy()
                    saved_item['id'] = hotspot.id
                    saved_item['is_new'] = True  # 标记为新增
                    saved_items.append(saved_item)
                    new_items.append(saved_item)  # 记录新增数据

            session.commit()
            logger.info(f"保存到数据库: {len(saved_items)} 条数据 (新增 {len(new_items)} 条)")
            return saved_items

        except Exception as e:
            session.rollback()
            logger.error(f"保存数据库失败: {e}")
            return []
        finally:
            session.close()
    
    def close(self):
        """关闭资源"""
        self.fetcher.close()
        if self.detail_crawler:
            self.detail_crawler.close()
        # 关闭 Playwright 浏览器
        if self._playwright_fetcher:
            try:
                self._playwright_fetcher.close()
                logger.info("Playwright 浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭 Playwright 时发生错误: {e}")


class ScheduledCrawler:
    """定时爬虫调度器 - 支持两级抓取"""
    
    def __init__(self, crawler: CrawlerEngine = None, enable_detail_crawl: bool = True, monitor_service=None):
        self.crawler = crawler or CrawlerEngine(enable_two_level=enable_detail_crawl)
        self.running = False
        self.enable_detail_crawl = enable_detail_crawl
        self.monitor_service = monitor_service  # 监控服务实例引用
    
    def start(self, interval_minutes: int = 30):
        """启动定时抓取"""
        from apscheduler.schedulers.background import BackgroundScheduler
        
        self.scheduler = BackgroundScheduler()
        
        # 列表页抓取任务
        self.scheduler.add_job(
            self._crawl_job,
            'interval',
            minutes=interval_minutes,
            id='crawl_job',
            replace_existing=True
        )
        
        # 详情页抓取任务（每10分钟检查一次队列）
        if self.enable_detail_crawl and self.crawler.detail_crawler:
            self.scheduler.add_job(
                self._detail_crawl_job,
                'interval',
                minutes=10,
                id='detail_crawl_job',
                replace_existing=True
            )
        
        self.scheduler.start()
        self.running = True
        logger.info(f"定时爬虫已启动，间隔: {interval_minutes}分钟")
    
    def _crawl_job(self):
        """定时任务 - 列表页抓取"""
        logger.info("执行定时列表页抓取任务")
        try:
            from core.filter.analyzer import HotspotAnalyzer

            analyzer = HotspotAnalyzer()
            stats = self.crawler.crawl_and_save(
                analyzer=analyzer,
                enable_detail_crawl=self.enable_detail_crawl
            )

            # 更新监控服务统计（使用直接引用，避免后台线程导入问题）
            if self.monitor_service:
                self.monitor_service._last_crawl_time = datetime.now()
                self.monitor_service._crawl_count += 1
                logger.info(f"✅ 监控计数已更新: 已执行 {self.monitor_service._crawl_count} 次")
            else:
                logger.warning("⚠️ 监控服务实例未设置，无法更新计数")

            logger.info(f"定时抓取完成: {stats}")
        except Exception as e:
            logger.error(f"定时抓取失败: {e}")
    
    def _detail_crawl_job(self):
        """定时任务 - 详情页抓取"""
        if not self.crawler.detail_crawler:
            return
        
        logger.info("执行定时详情页抓取任务")
        try:
            stats = self.crawler.detail_crawler.get_stats()
            if stats.get('queued', 0) > 0:
                self.crawler.detail_crawler.process_queue()
                logger.info("详情页抓取任务处理完成")
        except Exception as e:
            logger.error(f"详情页抓取失败: {e}")
    
    def stop(self):
        """停止定时抓取"""
        if self.running and self.scheduler:
            try:
                self.scheduler.shutdown(wait=False)
                logger.info("定时爬虫已停止")
            except Exception as e:
                logger.warning(f"停止调度器时发生错误（可能已停止）: {e}")
            finally:
                self.running = False
    
    def run_once(self):
        """立即执行一次"""
        self._crawl_job()
