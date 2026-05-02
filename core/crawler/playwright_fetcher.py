"""
Playwright浏览器抓取模块 - 支持JavaScript渲染
用于抓取单页应用(SPA)和动态加载内容的网站
"""

from typing import Optional, Dict, Any, List
from loguru import logger
import threading

# 导入网络管理器
try:
    from ..network_manager import get_network_manager
    NETWORK_MANAGER_AVAILABLE = True
except ImportError:
    NETWORK_MANAGER_AVAILABLE = False
    logger.warning("网络管理器不可用，Playwright将不使用代理")


class PlaywrightFetcher:
    """基于Playwright的浏览器抓取器（同步版本）- 支持智能代理"""
    
    def __init__(self, headless: bool = True, timeout: int = 30, enable_proxy: bool = True):
        self.headless = headless
        self.timeout = timeout
        self.enable_proxy = enable_proxy
        self._browser = None
        self._context = None
        self._playwright = None
        self._lock = threading.Lock()
        self._initialized = False
        
        # 初始化网络管理器
        if self.enable_proxy and NETWORK_MANAGER_AVAILABLE:
            try:
                self.network_manager = get_network_manager()
                logger.debug("✅ Playwright 已启用智能代理")
            except Exception as e:
                logger.warning(f"⚠️ Playwright 网络管理器初始化失败: {e}")
                self.network_manager = None
        else:
            self.network_manager = None
    
    def _init_browser(self):
        """初始化浏览器（同步版本）"""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            from playwright.sync_api import sync_playwright
            
            self._playwright = sync_playwright().start()
            
            # 准备浏览器启动参数
            launch_args = ['--no-sandbox', '--disable-dev-shm-usage']
            proxy_config = None
            
            # 获取代理配置
            if self.network_manager:
                proxy_config = self.network_manager.get_playwright_proxy_config()
                if proxy_config:
                    logger.info(f"🌐 Playwright 使用代理: {proxy_config.get('server', 'unknown')}")
            
            # 启动浏览器
            launch_options = {
                'headless': self.headless,
                'args': launch_args
            }
            if proxy_config:
                launch_options['proxy'] = proxy_config
            
            self._browser = self._playwright.chromium.launch(**launch_options)
            
            # 创建上下文
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            self._context = self._browser.new_context(**context_options)
            self._initialized = True
            logger.info("Playwright浏览器已启动")
    
    def fetch(self, url: str, wait_for: str = None, wait_timeout: int = 10, max_retries: int = 2) -> Optional[str]:
        """
        抓取页面HTML（支持JavaScript渲染）- 同步版本（增强版）
        
        Args:
            url: 页面URL
            wait_for: 等待特定选择器出现（如 '.article-item'）
            wait_timeout: 等待超时时间
            max_retries: 最大重试次数
        
        Returns:
            HTML内容
        """
        import time
        
        for attempt in range(max_retries):
            try:
                self._init_browser()
                
                page = self._context.new_page()
                
                # 设置更真实的浏览器行为
                page.set_extra_http_headers({
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Cache-Control': 'max-age=0',
                })
                
                try:
                    # 使用更宽松的加载策略
                    response = page.goto(
                        url, 
                        wait_until='domcontentloaded',
                        timeout=self.timeout * 1000
                    )
                    
                    if response and response.status >= 400:
                        logger.warning(f"页面返回错误状态码: {response.status}")
                    
                    # 等待网络空闲（关键页面完成加载）
                    try:
                        page.wait_for_load_state('networkidle', timeout=5000)
                    except:
                        pass  # 忽略超时，继续执行
                    
                    # 等待特定元素加载
                    if wait_for:
                        try:
                            page.wait_for_selector(wait_for, timeout=wait_timeout * 1000)
                            logger.debug(f"等待元素 {wait_for} 加载完成")
                        except Exception as e:
                            logger.warning(f"等待元素 {wait_for} 超时，但继续获取页面内容: {e}")
                    
                    # 额外等待JS渲染
                    time.sleep(2)
                    
                    # 获取HTML
                    html = page.content()
                    
                    # 验证内容有效性
                    if html and len(html) > 3000:
                        logger.info(f"✅ Playwright成功抓取: {url} (大小: {len(html)} bytes, 尝试: {attempt + 1})")
                        return html
                    else:
                        logger.warning(f"⚠️ 抓取内容太短 ({len(html) if html else 0} bytes)，可能页面未正确加载")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return html if html else None
                    
                finally:
                    page.close()
                    
            except Exception as e:
                logger.error(f"❌ Playwright抓取失败 (尝试 {attempt + 1}/{max_retries}) {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    return None
        
        return None
    
    def fetch_multiple(self, urls: List[str], wait_for: str = None) -> Dict[str, Optional[str]]:
        """批量抓取多个URL（同步版本）"""
        results = {}
        for url in urls:
            results[url] = self.fetch(url, wait_for)
            import time
            time.sleep(1)  # 避免请求过快
        return results
    
    def close(self):
        """关闭浏览器（同步版本）"""
        with self._lock:
            if self._browser:
                try:
                    self._browser.close()
                except:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    self._playwright.stop()
                except:
                    pass
                self._playwright = None
            self._initialized = False
            logger.info("Playwright浏览器已关闭")
    
    def __del__(self):
        """析构时关闭资源"""
        self.close()


class PlaywrightCrawlerMixin:
    """为CrawlerEngine添加Playwright支持的Mixin"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._playwright_fetcher: Optional[PlaywrightFetcher] = None
    
    def _crawl_with_playwright(self, source_id: str, source_config: Dict) -> list:
        """
        使用Playwright抓取需要JS渲染的页面（同步版本）
        
        Args:
            source_id: 数据源ID
            source_config: 数据源配置
        
        Returns:
            解析后的数据列表
        """
        if self._playwright_fetcher is None:
            self._playwright_fetcher = PlaywrightFetcher()
        
        url = source_config.get('url', '')
        selectors = source_config.get('selectors', {})
        container_selector = selectors.get('container', '')
        
        html = self._playwright_fetcher.fetch(
            url, 
            wait_for=container_selector or None
        )
        
        if html:
            items = self.parser.parse_html(html, selectors, url)
            logger.info(f"Playwright抓取 {source_id}: 获取 {len(items)} 条数据")
            return items
        return []


# 需要Playwright抓取的网站列表（SPA或重度JS依赖）
PLAYWRIGHT_SOURCES = [
    'zhihu',       # 知乎 - 需要JS渲染
    'juejin',      # 掘金 - SPA
    'csdn',        # CSDN - 动态加载
    'kr36',        # 36氪 - 动态加载
    'oschina',     # 开源中国
    'segmentfault', # 思否
    # 注意：GitHub 不需要 Playwright，使用普通 HTTP 抓取即可
]
