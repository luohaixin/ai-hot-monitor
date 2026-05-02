"""
网络管理模块 - 统一处理代理配置和网络适配
支持自动代理检测、智能路由选择、多网络环境兼容
"""

import os
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse
from loguru import logger


@dataclass
class ProxyConfig:
    """代理配置"""
    enabled: bool = False
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    socks_proxy: Optional[str] = None
    bypass_hosts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为请求库可用的代理字典"""
        proxies = {}
        if self.http_proxy:
            proxies['http://'] = self.http_proxy
        if self.https_proxy:
            proxies['https://'] = self.https_proxy
        return proxies
    
    def to_httpx_format(self) -> Optional[str]:
        """转换为 httpx 格式"""
        return self.https_proxy or self.http_proxy


class NetworkManager:
    """网络管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    # 国内网站域名列表 - 这些网站通常直连更快
    DOMESTIC_DOMAINS = [
        # 技术社区
        'zhihu.com', 'juejin.cn', 'csdn.net', 'oschina.net',
        'segmentfault.com', 'jiqizhixin.com', 'syncedreview.com',
        'qbitai.com', 'aiera.com.cn', 'infoq.cn', '36kr.com',
        
        # 搜索引擎/平台
        'baidu.com', 'sogou.com', 'so.com',
        'bilibili.com', 'weibo.com', 'sina.com.cn',
        
        # AI 服务
        'moonshot.cn', 'baichuan-ai.com', 'zhipuai.cn',
        
        # 代码托管
        'gitee.com', 'coding.net',
        
        # 邮箱
        'qq.com', '163.com', '126.com',
    ]
    
    # 国外网站列表 - 这些通常需要代理
    INTERNATIONAL_DOMAINS = [
        'openrouter.ai',
        'twitter.com', 'x.com',
        'github.com',
        'google.com', 'bing.com',
        'youtube.com',
        'algolia.com',
        'firebaseio.com',
    ]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._proxy_config: ProxyConfig = ProxyConfig()
        self._domestic_domains = set(self.DOMESTIC_DOMAINS)
        self._international_domains = set(self.INTERNATIONAL_DOMAINS)
        
        # 自动检测和配置代理
        self._auto_configure()
        
        logger.info(f"🌐 网络管理器初始化完成，代理状态: {'启用' if self._proxy_config.enabled else '禁用'}")
    
    def _auto_configure(self):
        """自动配置代理"""
        # 1. 首先检查配置文件
        config_proxy = self._get_config_from_file()
        if config_proxy and config_proxy.enabled:
            self._proxy_config = config_proxy
            logger.info("✅ 从配置文件加载代理设置")
            return
        
        # 2. 检查环境变量
        env_proxy = self._get_config_from_env()
        if env_proxy and env_proxy.enabled:
            self._proxy_config = env_proxy
            logger.info("✅ 从环境变量加载代理设置")
            return
        
        # 3. 检测系统代理
        system_proxy = self._detect_system_proxy()
        if system_proxy:
            self._proxy_config = system_proxy
            logger.info("✅ 自动检测到系统代理")
            return
        
        # 4. 无代理配置
        self._proxy_config = ProxyConfig(enabled=False)
        logger.info("ℹ️ 未检测到代理配置，使用直连模式")
    
    def _get_config_from_file(self) -> Optional[ProxyConfig]:
        """从配置文件读取代理设置"""
        try:
            from .config_loader import get_config
            config = get_config()
            proxy_config = config.get('network.proxy', {})
            
            if not proxy_config.get('enabled', False):
                return None
            
            return ProxyConfig(
                enabled=True,
                http_proxy=proxy_config.get('http'),
                https_proxy=proxy_config.get('https'),
                bypass_hosts=proxy_config.get('bypass', [])
            )
        except Exception as e:
            logger.debug(f"从配置文件读取代理设置失败: {e}")
            return None
    
    def _get_config_from_env(self) -> Optional[ProxyConfig]:
        """从环境变量读取代理设置"""
        # 优先使用项目特定的环境变量
        http_proxy = os.getenv('APP_HTTP_PROXY') or os.getenv('APP_PROXY')
        https_proxy = os.getenv('APP_HTTPS_PROXY') or os.getenv('APP_PROXY')
        
        if http_proxy or https_proxy:
            bypass = os.getenv('APP_PROXY_BYPASS', '')
            return ProxyConfig(
                enabled=True,
                http_proxy=http_proxy,
                https_proxy=https_proxy or http_proxy,
                bypass_hosts=[h.strip() for h in bypass.split(',') if h.strip()]
            )
        return None
    
    def _detect_system_proxy(self) -> Optional[ProxyConfig]:
        """检测系统代理设置"""
        # 检查常见的环境变量
        http_proxy = (
            os.getenv('HTTP_PROXY') or 
            os.getenv('http_proxy') or
            os.getenv('ALL_PROXY') or
            os.getenv('all_proxy')
        )
        https_proxy = (
            os.getenv('HTTPS_PROXY') or 
            os.getenv('https_proxy') or
            os.getenv('ALL_PROXY') or
            os.getenv('all_proxy') or
            http_proxy
        )
        
        # macOS 特有的检测
        if not http_proxy and os.name == 'posix':
            http_proxy = self._detect_macos_proxy()
        
        if http_proxy or https_proxy:
            # 获取绕过设置
            no_proxy = os.getenv('NO_PROXY') or os.getenv('no_proxy', '')
            bypass = [h.strip() for h in no_proxy.split(',') if h.strip()]
            
            return ProxyConfig(
                enabled=True,
                http_proxy=http_proxy,
                https_proxy=https_proxy or http_proxy,
                bypass_hosts=bypass
            )
        
        return None
    
    def _detect_macos_proxy(self) -> Optional[str]:
        """检测 macOS 系统代理（通过 scutil）"""
        try:
            import subprocess
            result = subprocess.run(
                ['scutil', '--proxy'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            
            # 解析 HTTP 代理设置
            if 'HTTPProxy' in output:
                proxy_match = re.search(r'HTTPProxy\s*:\s*(\S+)', output)
                port_match = re.search(r'HTTPPort\s*:\s*(\d+)', output)
                
                if proxy_match and port_match:
                    proxy = proxy_match.group(1)
                    port = port_match.group(1)
                    return f"http://{proxy}:{port}"
        except Exception:
            pass
        return None
    
    def is_domestic_domain(self, url: str) -> bool:
        """判断是否为国内域名"""
        try:
            hostname = urlparse(url).netloc.lower()
            # 移除端口号
            if ':' in hostname:
                hostname = hostname.split(':')[0]
            
            # 检查是否在白名单中
            for bypass in self._proxy_config.bypass_hosts:
                if bypass in hostname:
                    return True
            
            # 检查是否为国内域名
            for domain in self._domestic_domains:
                if domain in hostname or hostname.endswith('.' + domain):
                    return True
            
            # 检查是否为国外域名
            for domain in self._international_domains:
                if domain in hostname or hostname.endswith('.' + domain):
                    return False
            
            # 默认策略：.cn 域名和中文域名视为国内
            if hostname.endswith('.cn') or '.cn.' in hostname:
                return True
            
        except Exception:
            pass
        
        return False
    
    def should_use_proxy(self, url: str) -> bool:
        """判断是否应该对指定URL使用代理"""
        if not self._proxy_config.enabled:
            return False
        
        # 检查是否在绕过列表中
        try:
            hostname = urlparse(url).netloc.lower()
            for bypass in self._proxy_config.bypass_hosts:
                if bypass in hostname:
                    return False
        except Exception:
            pass
        
        # 国内域名通常不需要代理
        if self.is_domestic_domain(url):
            return False
        
        return True
    
    def get_proxy_for_url(self, url: str) -> Optional[str]:
        """获取指定URL应使用的代理"""
        if not self.should_use_proxy(url):
            return None
        
        parsed = urlparse(url)
        if parsed.scheme == 'https':
            return self._proxy_config.https_proxy or self._proxy_config.http_proxy
        return self._proxy_config.http_proxy
    
    def get_proxies_for_requests(self, url: str) -> Dict[str, str]:
        """获取 requests 库格式的代理配置"""
        proxy = self.get_proxy_for_url(url)
        if proxy:
            return {
                'http': proxy,
                'https': proxy
            }
        return {}
    
    def get_proxy_for_httpx(self, url: str) -> Optional[str]:
        """获取 httpx 格式的代理配置"""
        return self.get_proxy_for_url(url)
    
    def get_proxy_config(self) -> ProxyConfig:
        """获取当前代理配置"""
        return self._proxy_config
    
    def get_playwright_proxy_config(self) -> Optional[Dict[str, Any]]:
        """获取 Playwright 浏览器代理配置"""
        if not self._proxy_config.enabled:
            return None
        
        proxy_url = self._proxy_config.http_proxy or self._proxy_config.https_proxy
        if not proxy_url:
            return None
        
        # 解析代理URL
        parsed = urlparse(proxy_url)
        
        config = {
            'server': f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else f"{parsed.scheme}://{parsed.hostname}",
        }
        
        if parsed.username:
            config['username'] = parsed.username
        if parsed.password:
            config['password'] = parsed.password
        
        # 添加绕过列表（国内网站）
        bypass_list = list(self._domestic_domains)
        bypass_list.extend(self._proxy_config.bypass_hosts)
        if bypass_list:
            config['bypass'] = ','.join(bypass_list)
        
        return config
    
    def test_proxy_connection(self, url: str = "https://www.google.com") -> bool:
        """测试代理连接"""
        if not self._proxy_config.enabled:
            return True
        
        try:
            import httpx
            proxy = self.get_proxy_for_httpx(url)
            
            with httpx.Client(proxy=proxy, timeout=10) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"代理连接测试失败: {e}")
            return False
    
    def get_network_summary(self) -> Dict[str, Any]:
        """获取网络配置摘要"""
        return {
            'proxy_enabled': self._proxy_config.enabled,
            'http_proxy': self._proxy_config.http_proxy,
            'https_proxy': self._proxy_config.https_proxy,
            'bypass_count': len(self._proxy_config.bypass_hosts),
            'domestic_domains_count': len(self._domestic_domains),
            'international_domains_count': len(self._international_domains),
        }


# 全局网络管理器实例
_network_manager = None


def get_network_manager() -> NetworkManager:
    """获取网络管理器实例"""
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkManager()
    return _network_manager


def should_use_proxy(url: str) -> bool:
    """便捷函数：判断是否应该对URL使用代理"""
    return get_network_manager().should_use_proxy(url)


def get_proxy_for_url(url: str) -> Optional[str]:
    """便捷函数：获取URL应使用的代理"""
    return get_network_manager().get_proxy_for_url(url)


def get_proxies_for_requests(url: str) -> Dict[str, str]:
    """便捷函数：获取 requests 格式的代理配置"""
    return get_network_manager().get_proxies_for_requests(url)


def get_proxy_for_httpx(url: str) -> Optional[str]:
    """便捷函数：获取 httpx 格式的代理配置"""
    return get_network_manager().get_proxy_for_httpx(url)
