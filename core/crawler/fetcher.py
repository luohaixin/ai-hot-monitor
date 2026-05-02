"""
网络请求模块 - 封装请求逻辑，支持UA伪装、重试、代理等
"""

import time
import random
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fake_useragent import UserAgent
from loguru import logger


class Fetcher:
    """网络请求器 - 支持智能代理"""
    
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY = 3
    
    def __init__(self, timeout: int = None, max_retries: int = None, enable_proxy: bool = True):
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_RETRY
        self.enable_proxy = enable_proxy
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0')
        self.session = self._create_session()
        
        # 初始化网络管理器
        if self.enable_proxy:
            try:
                from ..network_manager import get_network_manager
                self.network_manager = get_network_manager()
                logger.debug("✅ Fetcher 已启用智能代理")
            except Exception as e:
                logger.warning(f"⚠️ 网络管理器初始化失败: {e}")
                self.network_manager = None
        else:
            self.network_manager = None
    
    def _create_session(self) -> requests.Session:
        """创建带有重试机制的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_headers(self, referer: str = None) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        if referer:
            headers['Referer'] = referer
        
        return headers
    
    def fetch(
        self, 
        url: str, 
        method: str = 'GET',
        headers: Dict = None,
        referer: str = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        执行HTTP请求（支持智能代理）
        
        Returns:
            Response对象，失败返回None
        """
        request_headers = self.get_headers(referer)
        if headers:
            request_headers.update(headers)
        
        # 智能代理配置
        proxies = None
        if self.network_manager:
            proxies = self.network_manager.get_proxies_for_requests(url)
            if proxies:
                logger.debug(f"🌐 使用代理访问: {url}")
        
        try:
            logger.debug(f"Fetching: {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                timeout=self.timeout,
                proxies=proxies,
                **kwargs
            )
            response.raise_for_status()
            
            # 随机延迟，避免被封
            time.sleep(random.uniform(0.5, 1.5))
            
            return response
            
        except requests.exceptions.ProxyError as e:
            logger.error(f"代理请求失败 {url}: {e}，尝试直连...")
            # 代理失败时尝试直连
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
            except Exception as e2:
                logger.error(f"直连也失败 {url}: {e2}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def fetch_html(self, url: str, **kwargs) -> Optional[str]:
        """获取HTML内容"""
        response = self.fetch(url, **kwargs)
        if response:
            # 自动检测编码
            response.encoding = response.apparent_encoding
            return response.text
        return None
    
    def fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        """获取JSON数据"""
        response = self.fetch(url, **kwargs)
        if response:
            try:
                return response.json()
            except ValueError as e:
                logger.error(f"JSON parse error: {e}")
        return None
    
    def close(self):
        """关闭会话"""
        self.session.close()


class AsyncFetcher:
    """异步请求器（用于高并发场景）"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.ua = UserAgent()
    
    async def fetch(
        self, 
        session, 
        url: str, 
        referer: str = None,
        **kwargs
    ) -> Optional[str]:
        """异步获取内容"""
        import aiohttp
        
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        
        if referer:
            headers['Referer'] = referer
        
        try:
            async with session.get(
                url, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                **kwargs
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Async fetch error for {url}: {e}")
            return None
