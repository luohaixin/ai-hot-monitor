"""
社交媒体和搜索引擎数据源
支持 Twitter、Bing、HackerNews、搜狗、B站、微博
"""

import json
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger

# 导入网络管理器
try:
    from ..network_manager import get_network_manager, get_proxy_for_httpx
    NETWORK_MANAGER_AVAILABLE = True
except ImportError:
    NETWORK_MANAGER_AVAILABLE = False
    logger.warning("网络管理器不可用，社交媒体数据源将不使用代理")


def get_httpx_client(timeout: float = 30.0, url: str = None, **kwargs) -> httpx.AsyncClient:
    """
    创建支持智能代理的 httpx 客户端
    
    Args:
        timeout: 超时时间
        url: 目标URL（用于判断是否需要代理）
        **kwargs: 其他参数
    
    Returns:
        httpx.AsyncClient 实例
    """
    proxy = None
    if NETWORK_MANAGER_AVAILABLE and url:
        proxy = get_proxy_for_httpx(url)
        if proxy:
            logger.debug(f"🌐 社交媒体使用代理: {proxy}")
    
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        proxy=proxy,
        **kwargs
    )


@dataclass
class SocialSearchResult:
    """社交媒体搜索结果"""
    title: str
    content: str
    url: str
    source: str
    author: Optional[str] = None
    author_avatar: Optional[str] = None
    published_at: Optional[datetime] = None
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0


class RateLimiter:
    """频率限制器"""
    
    def __init__(self, min_interval_ms: int = 5000):
        self.min_interval = min_interval_ms / 1000
        self.last_request_time = 0
    
    async def wait(self):
        """等待以确保请求间隔"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()


import asyncio

# 各数据源的频率限制器
twitter_limiter = RateLimiter(2000)    # 2秒
bing_limiter = RateLimiter(5000)       # 5秒
hackernews_limiter = RateLimiter(1000) # 1秒
sogou_limiter = RateLimiter(5000)      # 5秒
bilibili_limiter = RateLimiter(3000)   # 3秒
weibo_limiter = RateLimiter(3000)      # 3秒


class TwitterSource:
    """Twitter/X 数据源 - 使用 twitterapi.io"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.twitterapi.io"
        self.enabled = api_key is not None
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """搜索推文"""
        if not self.enabled:
            logger.warning("Twitter/X 搜索被禁用：未配置 TWITTER_API_KEY 环境变量")
            return []
        
        logger.info(f"开始 Twitter/X 搜索: '{query}'")
        
        await twitter_limiter.wait()
        
        headers = {"X-API-Key": self.api_key}
        
        try:
            async with get_httpx_client(timeout=30.0, url=self.base_url) as client:
                response = await client.get(
                    f"{self.base_url}/api/tweets/search",
                    headers=headers,
                    params={
                        "query": query,
                        "limit": max_results
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Twitter API错误: {response.status_code}")
                    return []
                
                data = response.json()
                tweets = data.get("tweets", [])
                
                results = []
                for tweet in tweets:
                    try:
                        published = None
                        if tweet.get("createdAt"):
                            published = datetime.strptime(
                                tweet["createdAt"],
                                "%a %b %d %H:%M:%S %z %Y"
                            )
                        
                        results.append(SocialSearchResult(
                            title=tweet.get("text", "")[:100],
                            content=tweet.get("text", ""),
                            url=f"https://twitter.com/i/web/status/{tweet.get('id')}",
                            source="Twitter",
                            author=tweet.get("author", {}).get("userName"),
                            author_avatar=tweet.get("author", {}).get("profilePicture"),
                            published_at=published,
                            views=tweet.get("viewCount", 0),
                            likes=tweet.get("likeCount", 0),
                            shares=tweet.get("retweetCount", 0),
                            comments=tweet.get("replyCount", 0)
                        ))
                    except Exception as e:
                        logger.debug(f"解析推文失败: {e}")
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Twitter搜索失败: {e}")
            return []


class BingSource:
    """Bing 搜索数据源 - 网页爬虫"""
    
    def __init__(self):
        self.ua = UserAgent()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头 - 模拟真实浏览器"""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.bing.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "max-age=0",
        }
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """Bing搜索"""
        await bing_limiter.wait()
        
        try:
            async with get_httpx_client(timeout=15.0, url="https://www.bing.com", follow_redirects=True) as client:
                # 先访问Bing主页获取cookie
                await client.get("https://www.bing.com", headers=self._get_headers())
                
                # 然后搜索
                response = await client.get(
                    "https://www.bing.com/search",
                    headers=self._get_headers(),
                    params={
                        "q": query,
                        "count": min(max_results * 2, 30),
                        "form": "QBLH",
                        "sp": "-1",
                        "lq": "0",
                        "pq": query,
                        "sc": "10-5",
                        "qs": "n",
                        "sk": "",
                        "cvid": ""
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Bing搜索失败: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # 尝试多个选择器
                selectors = ['li.b_algo', '.b_algo', '#b_results .b_algo', '#b_content .b_algo']
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        break
                
                logger.debug(f"Bing找到 {len(items)} 个结果项")
                
                for item in items[:max_results]:
                    try:
                        # 尝试多种标题选择器
                        title_elem = item.find('h2') or item.find('a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                        url = link_elem.get('href', '') if link_elem else ""
                        
                        # 跳过Bing自己的链接
                        if url and url.startswith('/'):
                            url = f"https://www.bing.com{url}"
                        
                        # 尝试多种摘要选择器
                        summary = ""
                        for caption_selector in ['.b_caption p', '.b_caption', '.b_snippet', 'p']:
                            caption = item.select_one(caption_selector)
                            if caption:
                                summary = caption.get_text(strip=True)
                                if summary and summary != title:
                                    break
                        
                        if title and url and url.startswith('http') and 'bing.com' not in url:
                            results.append(SocialSearchResult(
                                title=title,
                                content=summary[:200] if summary else "",
                                url=url,
                                source="Bing"
                            ))
                    except Exception as e:
                        logger.debug(f"解析Bing结果失败: {e}")
                        continue
                
                logger.info(f"Bing搜索 '{query}' 返回 {len(results)} 条结果")
                return results
                
        except Exception as e:
            logger.error(f"Bing搜索失败: {e}")
            return []


class HackerNewsSource:
    """HackerNews 数据源 - 使用 Algolia API"""
    
    def __init__(self):
        self.base_url = "https://hn.algolia.com/api/v1"
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """搜索 HackerNews"""
        await hackernews_limiter.wait()
        
        try:
            logger.info(f"开始 HackerNews 搜索: '{query}'")
            
            async with get_httpx_client(timeout=15.0, url=self.base_url) as client:
                search_url = f"{self.base_url}/search"
                params = {
                    "query": query,
                    "hitsPerPage": max_results,
                    "tags": "story"
                }
                
                logger.debug(f"HackerNews API请求: {search_url}, params={params}")
                
                response = await client.get(search_url, params=params)
                
                if response.status_code != 200:
                    logger.warning(f"HackerNews API错误: {response.status_code}, 响应: {response.text[:200]}")
                    return []
                
                data = response.json()
                hits = data.get("hits", [])
                logger.debug(f"HackerNews API返回 {len(hits)} 条原始结果")
                
                results = []
                for hit in hits:
                    try:
                        published = None
                        if hit.get("created_at"):
                            published = datetime.strptime(
                                hit["created_at"],
                                "%Y-%m-%dT%H:%M:%S.%fZ"
                            )
                        
                        results.append(SocialSearchResult(
                            title=hit.get("title", ""),
                            content=hit.get("story_text", "") or "",
                            url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            source="HackerNews",
                            author=hit.get("author"),
                            published_at=published,
                            likes=hit.get("points", 0),
                            comments=hit.get("num_comments", 0)
                        ))
                    except Exception as e:
                        logger.debug(f"解析HackerNews结果失败: {e}")
                        continue
                
                logger.info(f"HackerNews搜索 '{query}' 返回 {len(results)} 条结果")
                return results
                
        except Exception as e:
            logger.error(f"HackerNews搜索失败: {e}")
            return []
    
    async def get_trending(self, max_results: int = 10) -> List[SocialSearchResult]:
        """获取热门内容 - 使用有限并发请求，防止卡住"""
        await hackernews_limiter.wait()
        
        try:
            # 使用更短的整体超时
            async with get_httpx_client(timeout=10.0, url="https://hacker-news.firebaseio.com") as client:
                # 获取热门故事ID - 添加超时保护
                try:
                    response = await asyncio.wait_for(
                        client.get("https://hacker-news.firebaseio.com/v0/topstories.json"),
                        timeout=8.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("获取HackerNews故事ID列表超时")
                    return []
                
                if response.status_code != 200:
                    logger.warning(f"HackerNews API返回错误: {response.status_code}")
                    return []
                
                story_ids = response.json()[:max_results]
                logger.info(f"HackerNews 获取到 {len(story_ids)} 个故事ID")
                
                # 使用信号量限制并发数，防止同时发起过多请求
                semaphore = asyncio.Semaphore(5)  # 最多5个并发
                
                async def fetch_story(story_id: int) -> Optional[SocialSearchResult]:
                    async with semaphore:  # 限制并发
                        try:
                            # 使用 wait_for 包装请求，确保超时控制
                            story_resp = await asyncio.wait_for(
                                client.get(
                                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                                ),
                                timeout=3.0  # 单个故事3秒超时
                            )
                            if story_resp.status_code == 200:
                                story = story_resp.json()
                                if story and story.get("type") == "story":
                                    published = datetime.fromtimestamp(story.get("time", 0))
                                    return SocialSearchResult(
                                        title=story.get("title", ""),
                                        content="",
                                        url=story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                                        source="HackerNews",
                                        author=story.get("by"),
                                        published_at=published,
                                        likes=story.get("score", 0),
                                        comments=story.get("descendants", 0)
                                    )
                        except asyncio.TimeoutError:
                            logger.debug(f"获取HackerNews故事 {story_id} 超时")
                        except Exception as e:
                            logger.debug(f"获取HackerNews故事 {story_id} 失败: {e}")
                        return None
                
                # 使用 gather 并行获取，设置 return_exceptions=True 防止一个失败影响全部
                tasks = [fetch_story(sid) for sid in story_ids]
                
                # 添加整体超时保护，最多等待15秒
                try:
                    results_raw = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=15.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("HackerNews 批量获取超时，返回已获取的数据")
                    # 取消未完成的任务
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    results_raw = []
                
                # 过滤掉 None 和异常
                results = []
                for r in results_raw:
                    if isinstance(r, SocialSearchResult):
                        results.append(r)
                
                logger.info(f"HackerNews 成功获取 {len(results)}/{len(story_ids)} 条热门")
                return results
                
        except Exception as e:
            logger.error(f"获取HackerNews热门失败: {e}")
            return []


class SogouSource:
    """搜狗搜索数据源"""
    
    def __init__(self):
        self.ua = UserAgent()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头 - 模拟真实浏览器"""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.sogou.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """搜狗搜索"""
        await sogou_limiter.wait()
        
        try:
            async with get_httpx_client(timeout=15.0, url="https://www.sogou.com", follow_redirects=True) as client:
                # 先访问主页
                await client.get("https://www.sogou.com", headers=self._get_headers())
                
                response = await client.get(
                    "https://www.sogou.com/web",
                    headers=self._get_headers(),
                    params={
                        "query": query,
                        "page": 1,
                        "ie": "utf8"
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"搜狗搜索失败: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # 尝试多个选择器
                selectors = ['.vrwrap', '.result', '#main .result', '.rb']
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        logger.debug(f"搜狗使用选择器 '{selector}' 找到 {len(items)} 个结果")
                        break
                
                for item in items[:max_results]:
                    try:
                        # 尝试多种标题选择器
                        title_elem = item.select_one('h3 a') or item.select_one('a[href]')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        
                        # 处理相对URL和跳转链接
                        if url.startswith('/'):
                            url = f"https://www.sogou.com{url}"
                        elif url.startswith('http://') or url.startswith('https://'):
                            pass  # 保留完整URL
                        
                        # 尝试多种摘要选择器
                        summary = ""
                        for summary_selector in ['.str-text', '.str_info', '.abstract', 'p']:
                            summary_elem = item.select_one(summary_selector)
                            if summary_elem:
                                summary = summary_elem.get_text(strip=True)
                                if summary and summary != title:
                                    break
                        
                        if title and len(title) > 5:
                            results.append(SocialSearchResult(
                                title=title,
                                content=summary[:200] if summary else "",
                                url=url if url else f"https://www.sogou.com/web?query={quote(query)}",
                                source="搜狗"
                            ))
                    except Exception as e:
                        logger.debug(f"解析搜狗结果失败: {e}")
                        continue
                
                logger.info(f"搜狗搜索 '{query}' 返回 {len(results)} 条结果")
                return results
                
        except Exception as e:
            logger.error(f"搜狗搜索失败: {e}")
            return []


class BilibiliSource:
    """Bilibili 数据源"""
    
    def __init__(self):
        self.ua = UserAgent()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.ua.random,
            "Referer": "https://search.bilibili.com/",
        }
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """搜索B站视频"""
        await bilibili_limiter.wait()
        
        try:
            async with get_httpx_client(timeout=15.0, url="https://api.bilibili.com") as client:
                response = await client.get(
                    "https://api.bilibili.com/x/web-interface/search/type",
                    headers=self._get_headers(),
                    params={
                        "keyword": query,
                        "search_type": "video",
                        "page": 1,
                        "page_size": max_results
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"B站API错误: {response.status_code}")
                    return []
                
                data = response.json()
                if data.get("code") != 0:
                    logger.warning(f"B站API返回错误: {data.get('message')}")
                    return []
                
                videos = data.get("data", {}).get("result", [])
                results = []
                
                for video in videos:
                    try:
                        bvid = video.get("bvid")
                        title = video.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", "")
                        
                        results.append(SocialSearchResult(
                            title=title,
                            content=video.get("description", ""),
                            url=f"https://www.bilibili.com/video/{bvid}",
                            source="Bilibili",
                            author=video.get("author"),
                            published_at=datetime.fromtimestamp(video.get("pubdate", 0)),
                            views=video.get("play", 0),
                            likes=video.get("like", 0),
                            comments=video.get("review", 0)
                        ))
                    except Exception as e:
                        logger.debug(f"解析B站视频失败: {e}")
                        continue
                
                logger.info(f"Bilibili搜索 '{query}' 返回 {len(results)} 条结果")
                return results
                
        except Exception as e:
            logger.error(f"B站搜索失败: {e}")
            return []


class WeiboSource:
    """微博数据源"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.hot_topics_cache = []
        self.cache_time = None
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://s.weibo.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> List[SocialSearchResult]:
        """搜索微博 - 通过热搜匹配获取相关内容"""
        await weibo_limiter.wait()
        
        try:
            logger.info(f"开始微博搜索: '{query}'")
            
            # 获取热搜数据
            hot_topics = await self.get_hot_topics(50)  # 获取更多热搜以提高匹配率
            
            if not hot_topics:
                logger.warning("微博热搜获取失败，返回空结果")
                return []
            
            logger.debug(f"获取到 {len(hot_topics)} 条微博热搜")
            
            # 过滤匹配关键词的热搜
            query_lower = query.lower()
            results = []
            
            for topic in hot_topics:
                title_lower = topic.title.lower()
                # 简单匹配：关键词包含在标题中，或标题包含关键词
                if query_lower in title_lower or title_lower in query_lower:
                    results.append(topic)
                    if len(results) >= max_results:
                        break
            
            # 如果没有精确匹配，尝试相关匹配
            if not results:
                logger.debug(f"未找到精确匹配，尝试相关匹配")
                for topic in hot_topics:
                    title_lower = topic.title.lower()
                    if self._is_related(query_lower, title_lower):
                        results.append(topic)
                        if len(results) >= max_results // 2:  # 相关匹配返回更少结果
                            break
            
            # 如果仍然没有结果，返回前几个热门热搜作为参考
            if not results and hot_topics:
                logger.debug(f"未找到匹配内容，返回热门热搜作为参考")
                results = hot_topics[:min(5, max_results)]
                # 标记这些是热门推荐
                for r in results:
                    r.title = f"[热门] {r.title}"
            
            logger.info(f"微博搜索 '{query}' 返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"微博搜索失败: {e}")
            return []
    
    def _is_related(self, query: str, title: str) -> bool:
        """检查两个词是否相关（有共同字符）"""
        # 如果有一个以上相同字符，认为相关
        common_chars = set(query) & set(title)
        return len(common_chars) >= 2
    
    async def get_hot_topics(self, max_results: int = 15) -> List[SocialSearchResult]:
        """获取微博热搜 - 添加超时保护"""
        await weibo_limiter.wait()
        
        try:
            logger.info("开始获取微博热搜...")
            
            async with get_httpx_client(timeout=8.0, url="https://s.weibo.com") as client:
                # 添加整体超时保护
                try:
                    response = await asyncio.wait_for(
                        client.get(
                            "https://s.weibo.com/top/summary",
                            headers=self._get_headers()
                        ),
                        timeout=6.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("获取微博热搜超时")
                    return []
                
                if response.status_code != 200:
                    logger.warning(f"获取微博热搜失败，状态码: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # 尝试多种选择器来获取热搜
                selectors = [
                    '#pl_top_realtimehot tbody tr',
                    '.realtimehot tbody tr',
                    'table tbody tr',
                    '.ranklist tbody tr',
                ]
                
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        logger.debug(f"使用选择器 '{selector}' 找到 {len(items)} 个元素")
                        break
                
                if not items:
                    logger.warning("未找到微博热搜元素，尝试打印页面结构...")
                    # 记录页面结构用于调试
                    tables = soup.find_all('table')
                    logger.debug(f"页面中找到 {len(tables)} 个 table 元素")
                    return []
                
                logger.debug(f"找到 {len(items)} 个热搜项")
                
                # 热搜列表
                for i, item in enumerate(items[:max_results + 1]):
                    try:
                        if i == 0:  # 跳过表头
                            continue
                        
                        # 尝试多种方式获取标题
                        title_elem = item.select_one('td a') or item.select_one('a') or item.find('a')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '')
                            
                            if not title:
                                continue
                            
                            if link.startswith('/'):
                                link = f"https://s.weibo.com{link}"
                            elif not link.startswith('http'):
                                link = f"https://s.weibo.com/weibo?q={title}"
                            
                            results.append(SocialSearchResult(
                                title=title,
                                content="",
                                url=link,
                                source="微博热搜"
                            ))
                    except Exception as e:
                        logger.debug(f"解析微博热搜失败: {e}")
                        continue
                
                logger.info(f"成功获取微博热搜 {len(results)} 条")
                return results
                
        except Exception as e:
            logger.error(f"获取微博热搜失败: {e}")
            return []


class SocialSourceAggregator:
    """社交媒体数据源聚合器"""
    
    def __init__(
        self,
        twitter_api_key: Optional[str] = None,
        enable_twitter: bool = True,
        enable_bing: bool = True,
        enable_hackernews: bool = True,
        enable_sogou: bool = True,
        enable_bilibili: bool = True,
        enable_weibo: bool = True
    ):
        self.twitter = TwitterSource(twitter_api_key) if enable_twitter else None
        self.bing = BingSource() if enable_bing else None
        self.hackernews = HackerNewsSource() if enable_hackernews else None
        self.sogou = SogouSource() if enable_sogou else None
        self.bilibili = BilibiliSource() if enable_bilibili else None
        self.weibo = WeiboSource() if enable_weibo else None
    
    async def search_all(
        self,
        query: str,
        max_results_per_source: int = 10
    ) -> Dict[str, List[SocialSearchResult]]:
        """
        搜索所有启用的数据源
        
        Args:
            query: 搜索关键词
            max_results_per_source: 每个数据源的最大结果数
            
        Returns:
            按数据源分组的搜索结果
        """
        results = {}
        
        # 并行搜索所有数据源
        tasks = []
        sources = []
        
        if self.twitter and self.twitter.enabled:
            tasks.append(self.twitter.search(query, max_results_per_source))
            sources.append("twitter")
        
        if self.bing:
            tasks.append(self.bing.search(query, max_results_per_source))
            sources.append("bing")
        
        if self.hackernews:
            tasks.append(self.hackernews.search(query, max_results_per_source))
            sources.append("hackernews")
        
        if self.sogou:
            tasks.append(self.sogou.search(query, max_results_per_source))
            sources.append("sogou")
        
        if self.bilibili:
            tasks.append(self.bilibili.search(query, max_results_per_source))
            sources.append("bilibili")
        
        if self.weibo:
            tasks.append(self.weibo.search(query, max_results_per_source))
            sources.append("weibo")
        
        # 等待所有任务完成
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for source, result in zip(sources, search_results):
            if isinstance(result, Exception):
                logger.error(f"{source} 搜索失败: {result}")
                results[source] = []
            else:
                results[source] = result
        
        return results
    
    async def get_trending(self) -> Dict[str, List[SocialSearchResult]]:
        """获取各平台热门内容"""
        results = {}
        
        if self.hackernews:
            results["hackernews"] = await self.hackernews.get_trending(20)
        
        if self.weibo:
            results["weibo"] = await self.weibo.get_hot_topics(20)
        
        return results


# 便捷的搜索函数
async def search_social_sources(
    query: str,
    twitter_api_key: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, List[SocialSearchResult]]:
    """
    搜索社交媒体数据源
    
    Args:
        query: 搜索关键词
        twitter_api_key: Twitter API密钥
        max_results: 每个数据源的最大结果数
        
    Returns:
        搜索结果
    """
    aggregator = SocialSourceAggregator(
        twitter_api_key=twitter_api_key,
        enable_bing=True,
        enable_hackernews=True,
        enable_sogou=True,
        enable_bilibili=True,
        enable_weibo=True
    )
    
    return await aggregator.search_all(query, max_results)
