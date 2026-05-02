"""
详情页抓取模块 - 实现两级抓取的第二阶段
用于抓取文章的完整内容
"""

import time
import random
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from queue import Queue, Empty
from loguru import logger
from bs4 import BeautifulSoup

from ..config_loader import get_config
from ..models import get_db, HotspotORM
from .fetcher import Fetcher


@dataclass
class DetailTask:
    """详情页抓取任务"""
    hotspot_id: int
    url: str
    source: str
    source_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class DetailResult:
    """详情页抓取结果"""
    hotspot_id: int
    url: str
    source: str
    success: bool
    content: Optional[str] = None
    message: str = ""
    crawl_time: datetime = field(default_factory=datetime.utcnow)


class DetailCrawler:
    """
    详情页抓取器
    
    负责抓取文章的完整内容，作为两级抓取的第二阶段：
    第一阶段：列表页抓取（CrawlerEngine）-> 获取URL和摘要
    第二阶段：详情页抓取（DetailCrawler）-> 获取完整内容
    """
    
    def __init__(
        self,
        max_workers: int = 3,
        delay_range: tuple = (2, 5),
        queue_size: int = 1000
    ):
        self.config = get_config()
        self.max_workers = max_workers
        self.delay_range = delay_range  # 请求延迟范围（秒）
        self.fetcher = Fetcher()
        self.db = get_db()
        
        # 任务队列
        self.task_queue = Queue(maxsize=queue_size)
        self.result_queue = Queue()
        
        # 运行状态
        self._running = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'queued': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def extract_content(self, html: str, content_selector: str) -> Optional[str]:
        """
        从HTML中提取正文内容
        
        Args:
            html: 页面HTML
            content_selector: 正文CSS选择器
            
        Returns:
            提取的正文内容，失败返回None
        """
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除不需要的元素
            for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
                elem.decompose()
            
            # 尝试使用配置的选择器（支持多个选择器，用逗号分隔）
            if content_selector:
                selectors = [s.strip() for s in content_selector.split(',')]
                for selector in selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content = self._clean_content(content_elem.get_text(separator='\n'))
                        if len(content) >= 2:  # 只要内容非空即可
                            logger.debug(f"使用选择器提取成功: {selector}, 长度: {len(content)}")
                            return content
            
            # 如果配置的选择器失败，尝试通用选择器
            fallback_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-detail',
                '.article-detail',
                '.markdown-body',
                '.rich-text',
                '#article-content',
                '.content',
                'main',
                '[role="main"]',
                '.detail-content',
                '.article-body',
                '.post-body',
            ]
            
            for selector in fallback_selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = self._clean_content(elem.get_text(separator='\n'))
                    if len(content) >= 2:  # 只要内容非空即可
                        logger.debug(f"使用备用选择器提取成功: {selector}, 长度: {len(content)}")
                        return content
            
            # 最后尝试从body中提取最长的段落（仅当没有指定选择器或选择器为空时）
            if not content_selector:
                body = soup.find('body')
                if body:
                    # 获取所有段落
                    paragraphs = body.find_all(['p', 'div', 'section', 'article'])
                    longest_text = ""
                    for p in paragraphs:
                        text = self._clean_content(p.get_text(separator='\n'))
                        if len(text) > len(longest_text):
                            longest_text = text
                    
                    if len(longest_text) >= 2:  # 只要内容非空即可
                        logger.debug(f"从body提取成功, 长度: {len(longest_text)}")
                        return longest_text
            
            logger.warning(f"无法提取有效内容")
            return None
            
        except Exception as e:
            logger.error(f"提取内容失败: {e}")
            return None
    
    def _clean_content(self, text: str) -> str:
        """清理正文内容"""
        if not text:
            return ""
        
        # 移除多余空白，但保留段落结构
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n\n'.join(lines)
        
        # 移除特殊字符但保留中文标点
        text = text.replace('\t', ' ')
        
        # 移除过多的空行
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        # 移除常见的广告/版权文字
        ad_patterns = [
            '版权声明',
            '未经许可',
            '不得转载',
            '本文仅代表作者观点',
            '关于作者',
            '相关阅读',
            '推荐阅读',
            '热门文章',
            '猜你喜欢',
            '扫描下方二维码',
            '关注公众号',
            '扫码关注',
        ]
        for pattern in ad_patterns:
            if pattern in text[-500:]:  # 只在文末检查
                idx = text.rfind(pattern)
                if idx > len(text) * 0.7:  # 只在文章后30%部分裁剪
                    text = text[:idx].strip()
        
        return text.strip()
    
    def crawl_single(self, task: DetailTask) -> DetailResult:
        """
        抓取单个详情页
        
        Args:
            task: 详情页抓取任务
            
        Returns:
            抓取结果
        """
        try:
            logger.debug(f"抓取详情页: {task.url}")
            
            # 添加随机延迟
            delay = random.uniform(*self.delay_range)
            time.sleep(delay)
            
            # 获取详情页配置
            detail_config = task.config.get('detail', {})
            content_selector = detail_config.get('content_selector', '')
            
            # 抓取页面
            html = self.fetcher.fetch_html(task.url)
            if not html:
                return DetailResult(
                    hotspot_id=task.hotspot_id,
                    url=task.url,
                    source=task.source,
                    success=False,
                    message="无法获取页面内容"
                )
            
            # 提取正文
            content = self.extract_content(html, content_selector)
            if not content:
                return DetailResult(
                    hotspot_id=task.hotspot_id,
                    url=task.url,
                    source=task.source,
                    success=False,
                    message="无法提取正文内容"
                )
            
            return DetailResult(
                hotspot_id=task.hotspot_id,
                url=task.url,
                source=task.source,
                success=True,
                content=content,
                message=f"成功提取 {len(content)} 字符"
            )
            
        except Exception as e:
            logger.error(f"抓取详情页异常 {task.url}: {e}")
            return DetailResult(
                hotspot_id=task.hotspot_id,
                url=task.url,
                source=task.source,
                success=False,
                message=f"异常: {str(e)[:50]}"
            )
    
    def save_content(self, result: DetailResult) -> bool:
        """
        保存抓取的内容到数据库
        
        Args:
            result: 抓取结果
            
        Returns:
            是否保存成功
        """
        if not result.success or not result.content:
            return False
        
        session = self.db.get_session()
        try:
            hotspot = session.query(HotspotORM).filter_by(id=result.hotspot_id).first()
            if hotspot:
                hotspot.content = result.content[:50000]  # 限制长度
                session.commit()
                logger.debug(f"保存内容成功: {result.hotspot_id}")
                return True
            else:
                logger.warning(f"热点不存在: {result.hotspot_id}")
                return False
        except Exception as e:
            session.rollback()
            logger.error(f"保存内容失败: {e}")
            return False
        finally:
            session.close()
    
    def process_queue(self, callback: Callable = None) -> List[DetailResult]:
        """
        处理任务队列中的所有任务
        
        Args:
            callback: 进度回调函数 (current, total, result)
            
        Returns:
            所有抓取结果
        """
        results = []
        tasks = []
        
        # 收集队列中的所有任务
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get(timeout=1)
                tasks.append(task)
            except Empty:
                break
        
        if not tasks:
            return results
        
        total = len(tasks)
        logger.info(f"开始处理 {total} 个详情页任务")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self.crawl_single, task): task 
                for task in tasks
            }
            
            completed = 0
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
                completed += 1
                
                # 保存成功的内容
                if result.success:
                    self.save_content(result)
                    with self._lock:
                        self.stats['success'] += 1
                else:
                    with self._lock:
                        self.stats['failed'] += 1
                
                with self._lock:
                    self.stats['processed'] += 1
                
                if callback:
                    callback(completed, total, result)
        
        logger.info(f"详情页抓取完成: 成功 {self.stats['success']}/{total}")
        return results
    
    def add_task(self, hotspot_id: int, url: str, source: str, source_id: str) -> bool:
        """
        添加详情页抓取任务
        
        Args:
            hotspot_id: 热点ID
            url: 详情页URL
            source: 来源名称
            source_id: 数据源ID
            
        Returns:
            是否添加成功
        """
        try:
            # 获取数据源配置 - 首先尝试用 source_id 查找
            source_config = self.config.data_sources.get(source_id, {})
            
            # 如果没找到，尝试根据 source 名称反向查找
            if not source_config and source:
                for sid, cfg in self.config.data_sources.items():
                    if cfg.get('name') == source:
                        source_config = cfg
                        source_id = sid
                        break
            
            # 如果还是没找到，检查是否是社交媒体数据源
            if not source_config:
                # 社交媒体数据源（如 hackernews_热门、微博热搜等）不需要配置
                social_sources = ['hackernews', 'weibo', 'twitter', 'bilibili', 'bing', 'sogou']
                is_social = any(social in source.lower() for social in social_sources)
                
                if not is_social:
                    logger.warning(f"未找到数据源配置: source_id={source_id}, source={source}，使用默认配置")
                source_config = {}
            
            detail_config = source_config.get('detail', {})
            
            # 检查是否启用详情页抓取 - 默认启用
            if not detail_config.get('enabled', True):
                with self._lock:
                    self.stats['skipped'] += 1
                logger.debug(f"详情页抓取已禁用: {source}")
                return False
            
            task = DetailTask(
                hotspot_id=hotspot_id,
                url=url,
                source=source,
                source_id=source_id,
                config={'detail': detail_config}
            )
            
            self.task_queue.put(task, block=False)
            with self._lock:
                self.stats['queued'] += 1
            
            logger.debug(f"添加详情页任务: {hotspot_id} - {url}")
            return True
            
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False
    
    def add_tasks_from_hotspots(self, hotspots: List[Dict]) -> int:
        """
        从热点列表批量添加详情页任务
        
        Args:
            hotspots: 热点数据列表，每个应包含id, url, source等信息
            
        Returns:
            成功添加的任务数
        """
        added = 0
        for hotspot in hotspots:
            # 检查是否需要抓取详情页
            if not hotspot.get('content') or len(hotspot.get('content', '')) < 100:
                if self.add_task(
                    hotspot_id=hotspot.get('id'),
                    url=hotspot.get('url'),
                    source=hotspot.get('source'),
                    source_id=hotspot.get('source_id', '')
                ):
                    added += 1
        
        logger.info(f"添加了 {added} 个详情页任务")
        return added
    
    def start_background_worker(self, interval_seconds: int = 60):
        """
        启动后台工作线程
        
        Args:
            interval_seconds: 检查队列的间隔时间
        """
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        
        def worker():
            while not self._stop_event.is_set():
                if not self.task_queue.empty():
                    self.process_queue()
                self._stop_event.wait(interval_seconds)
        
        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()
        logger.info("详情页后台抓取器已启动")
    
    def stop_background_worker(self):
        """停止后台工作线程"""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        
        if hasattr(self, '_worker_thread'):
            self._worker_thread.join(timeout=5)
        
        logger.info("详情页后台抓取器已停止")
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self.stats = {
                'queued': 0,
                'processed': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0
            }
    
    def close(self):
        """关闭资源"""
        self.stop_background_worker()
        self.fetcher.close()
