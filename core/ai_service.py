"""
OpenRouter AI 服务
提供 Query Expansion、内容分析、真假识别、相关性分析等功能
"""

import asyncio
import json
import random
import re
import threading
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import httpx
from loguru import logger

# 导入网络管理器
try:
    from .network_manager import get_proxy_for_httpx
    NETWORK_MANAGER_AVAILABLE = True
except ImportError:
    NETWORK_MANAGER_AVAILABLE = False
    logger.warning("网络管理器不可用，AI服务将不使用代理")


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    is_real: bool = True  # 是否真实
    relevance: int = 0  # 相关性 0-100
    relevance_reason: str = ""  # 相关性理由
    keyword_mentioned: bool = False  # 是否提及关键词
    importance: str = "low"  # 重要程度 low/medium/high/urgent
    summary: str = ""  # AI摘要
    matched_keywords: List[str] = None  # 匹配的关键词
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []


@dataclass
class QueryExpansionResult:
    """查询扩展结果"""
    original: str = ""
    expanded_terms: List[str] = None
    
    def __post_init__(self):
        if self.expanded_terms is None:
            self.expanded_terms = []


class OpenRouterService:
    """OpenRouter AI 服务（支持多模型提供商）"""
    
    # 可用模型列表（按优先级排序）
    # Kimi (Moonshot) 模型 - 在中国可用
    AVAILABLE_MODELS = [
        "moonshot-v1-8k",                   # Kimi 主要模型 (8k上下文) - 中国可用
        "moonshot-v1-32k",                  # Kimi 长文本模型 (32k上下文) - 中国可用
        "deepseek/deepseek-chat",           # DeepSeek - 中国可用
        "qwen/qwen-2.5-72b-instruct",       # 通义千问 - 中国可用
        "google/gemini-2.0-flash-exp:free", # Gemini - 免费版
    ]
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "openrouter"):
        """
        初始化 AI 服务
        
        Args:
            api_key: API Key
            provider: 模型提供商 ("openrouter", "moonshot"/"kimi")
        """
        import os
        
        # 存储两个提供商的 API key（无论当前provider是什么，都尝试读取两个key，以便切换时使用）
        self._moonshot_api_key = os.getenv("MOONSHOT_API_KEY") or (api_key if provider in ["moonshot", "kimi"] else None)
        self._openrouter_api_key = os.getenv("OPENROUTER_API_KEY") or (api_key if provider == "openrouter" else None)
        
        self.provider = provider.lower()
        self.api_key = api_key  # 当前使用的 API key
        
        # 根据提供商设置 base_url 和默认模型
        if self.provider in ["moonshot", "kimi"]:
            self.base_url = "https://api.moonshot.cn/v1"
            self.model = "moonshot-v1-8k"
            if not self.api_key:
                self.api_key = self._moonshot_api_key
        else:
            self.base_url = "https://openrouter.ai/api/v1"
            self.model = self.AVAILABLE_MODELS[0]
            if not self.api_key:
                self.api_key = self._openrouter_api_key
        
        self.timeout = 30.0
        
        # 速率限制处理配置
        self.max_retries = 3  # 最大重试次数
        self.base_delay = 1.0  # 基础延迟（秒）
        self.max_delay = 30.0  # 最大延迟（秒）
        
        # 模型切换状态
        self._current_model_index = 0
        self._rate_limited_models = set()  # 记录被限速的模型
        
        if not self.api_key:
            logger.warning("API Key 未设置，AI功能将不可用")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        
        # OpenRouter 需要额外的头
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://ai-hotspot-monitor.com"
            headers["X-Title"] = "AI-Hotspot-Monitor"
        
        return headers
    
    def _switch_to_next_model(self) -> bool:
        """
        切换到下一个可用模型
        
        Returns:
            是否成功切换
        """
        # 找到下一个未被限速的模型
        for i in range(self._current_model_index + 1, len(self.AVAILABLE_MODELS)):
            model = self.AVAILABLE_MODELS[i]
            if model not in self._rate_limited_models:
                old_model = self.model
                self._current_model_index = i
                self.model = model
                
                # 如果从 Moonshot 模型切换到 OpenRouter 模型，需要切换 base_url 和 API key
                if self.provider in ["moonshot", "kimi"] and not model.startswith("moonshot"):
                    old_provider = self.provider
                    self.provider = "openrouter"
                    self.base_url = "https://openrouter.ai/api/v1"
                    # 切换到 OpenRouter API key
                    if self._openrouter_api_key:
                        self.api_key = self._openrouter_api_key
                        logger.info(f"已切换到 OpenRouter API Key")
                    else:
                        logger.warning(f"OpenRouter API Key 未设置，可能导致认证失败")
                    logger.warning(
                        f"模型切换: {old_model} -> {model} "
                        f"(Kimi被限速，切换到OpenRouter备用模型，"
                        f"提供商: {old_provider} -> openrouter)"
                    )
                else:
                    logger.warning(
                        f"模型切换: {old_model} -> {model} "
                        f"(原模型被限速，切换到备用模型)"
                    )
                return True
        
        # 所有模型都尝试过了，重置并返回失败
        logger.error("所有模型都已被限速，无法切换")
        return False
    
    def reset_model(self):
        """重置为默认模型（在任务完成后调用）"""
        if self._current_model_index != 0:
            logger.info(f"重置模型: {self.model} -> {self.AVAILABLE_MODELS[0]}")
            self._current_model_index = 0
            self.model = self.AVAILABLE_MODELS[0]
            self._rate_limited_models.clear()
            
            # 如果从 OpenRouter 切换回 Moonshot，需要恢复 provider 和 API key
            first_model = self.AVAILABLE_MODELS[0]
            if first_model.startswith("moonshot"):
                if self.provider != "moonshot":
                    logger.info(f"重置提供商: {self.provider} -> moonshot")
                    self.provider = "moonshot"
                    self.base_url = "https://api.moonshot.cn/v1"
                    if self._moonshot_api_key:
                        self.api_key = self._moonshot_api_key
                        logger.info(f"已恢复 Moonshot API Key")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 500,
        response_format: Optional[Dict] = None
    ) -> Optional[str]:
        """
        调用 OpenRouter Chat API（带429错误重试机制）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式
            
        Returns:
            AI响应文本
        """
        if not self.api_key:
            logger.warning("OpenRouter API Key 未设置")
            return None
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        last_exception = None
        
        # 获取代理配置
        proxy = None
        if NETWORK_MANAGER_AVAILABLE:
            proxy = get_proxy_for_httpx(self.base_url)
            if proxy:
                logger.debug(f"🌐 AI服务使用代理: {proxy}")
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, proxy=proxy) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                        else:
                            logger.error(f"OpenRouter响应格式错误: {data}")
                            return None
                    elif response.status_code == 429:
                        # 速率限制错误，记录被限速的模型
                        self._rate_limited_models.add(self.model)
                        
                        # 先尝试切换模型
                        if self._switch_to_next_model():
                            logger.warning(
                                f"检测到 429 速率限制，已切换到备用模型: {self.model}"
                            )
                            # 切换模型后继续循环（不增加attempt计数）
                            continue
                        
                        # 没有可用模型了，进行指数退避重试
                        if attempt < self.max_retries:
                            # 计算退避时间：基础延迟 * 2^尝试次数 + 随机抖动
                            delay = min(
                                self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                                self.max_delay
                            )
                            logger.warning(
                                f"OpenRouter API 429 速率限制，"
                                f"第 {attempt + 1}/{self.max_retries} 次重试，"
                                f"等待 {delay:.1f} 秒..."
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"OpenRouter API 429 速率限制，"
                                f"已重试 {self.max_retries} 次，放弃请求"
                            )
                            return None
                    elif response.status_code == 404:
                        # 模型不存在，尝试切换到下一个模型
                        logger.warning(f"模型 {self.model} 不存在 (404)，尝试切换到备用模型")
                        if self._switch_to_next_model():
                            continue
                        else:
                            logger.error("所有模型都不可用 (404)")
                            return None
                    elif response.status_code == 403:
                        # 模型在当前地区不可用，尝试切换到下一个模型
                        logger.warning(f"模型 {self.model} 在当前地区不可用 (403)，尝试切换到备用模型")
                        self._rate_limited_models.add(self.model)  # 标记为不可用
                        if self._switch_to_next_model():
                            continue
                        else:
                            logger.error("所有模型在当前地区都不可用 (403)")
                            return None
                    else:
                        logger.error(f"OpenRouter API错误: {response.status_code} - {response.text}")
                        return None

            except httpx.TimeoutException:
                logger.error(f"OpenRouter API请求超时（尝试 {attempt + 1}/{self.max_retries + 1}）")
                last_exception = "timeout"
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                return None
            except UnicodeEncodeError as e:
                logger.error(f"OpenRouter API编码错误: {e}")
                return None
            except Exception as e:
                logger.error(f"OpenRouter API请求失败: {e}")
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                return None
        
        # 所有重试都失败了
        logger.error(f"OpenRouter API 请求失败，已耗尽所有重试次数")
        return None
    
    async def expand_keyword(self, keyword: str) -> QueryExpansionResult:
        """
        Query Expansion - 扩展关键词变体
        
        Args:
            keyword: 原始关键词
            
        Returns:
            扩展后的关键词列表
        """
        system_prompt = """你是一个关键词扩展助手。请为给定的关键词生成多个变体和相关检索词。

规则：
1. 包含原始关键词的各种写法（大小写、空格、连字符变体）
2. 包含关键词的核心组成词
3. 包含常见别称、缩写、中英文对照
4. 总数控制在 5-15 个

输出格式：JSON数组，只输出JSON，不要其他解释。

示例输入：Claude Sonnet 4.6
示例输出：["Claude Sonnet 4.6", "Claude Sonnet", "Sonnet 4.6", "Claude 4.6", "Anthropic Claude Sonnet", "Claude Sonnet 4.6版本"]"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": keyword}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=300
        )
        
        if not response:
            return QueryExpansionResult(original=keyword, expanded_terms=[keyword])
        
        try:
            # 提取JSON部分
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                expanded = json.loads(json_match.group())
                # 确保原始关键词在列表中
                if keyword not in expanded:
                    expanded.insert(0, keyword)
                return QueryExpansionResult(original=keyword, expanded_terms=expanded)
            else:
                # 尝试直接解析
                expanded = json.loads(response)
                if isinstance(expanded, list):
                    if keyword not in expanded:
                        expanded.insert(0, keyword)
                    return QueryExpansionResult(original=keyword, expanded_terms=expanded)
        except json.JSONDecodeError:
            logger.warning(f"Query Expansion JSON解析失败: {response}")
        
        # 回退：返回原始关键词
        return QueryExpansionResult(original=keyword, expanded_terms=[keyword])
    
    def _build_analysis_prompt(
        self,
        keyword: str,
        expanded_terms: List[str],
        pre_matched: bool,
        matched_terms: List[str]
    ) -> str:
        """构建内容分析提示词"""
        
        matched_str = f"匹配到的变体：{', '.join(matched_terms)}" if matched_terms else ""
        
        return f"""你是一个专业的AI内容分析助手。请分析以下内容与监控关键词的相关性。

监控关键词：{keyword}
关键词变体：{', '.join(expanded_terms)}
预匹配结果：{'已匹配' if pre_matched else '未匹配'}
{matched_str}

请分析以下维度并输出JSON格式结果：

1. is_real (boolean): 内容是否真实可信（不是谣言、虚假内容）
2. relevance (integer 0-100): 内容与监控关键词的相关性分数
3. relevance_reason (string): 相关性评分的理由，2-3句话说明为什么相关或不相关
4. keyword_mentioned (boolean): 内容是否明确提及了关键词或其变体
5. importance (string): 重要程度，可选值：low/medium/high/urgent
   - urgent: 重大突破、发布、行业颠覆性新闻
   - high: 重要产品发布、技术突破、重大合作
   - medium: 一般性技术文章、常规更新
   - low: 边缘内容、重复信息、弱相关
6. summary (string): 内容的AI摘要，100字以内，突出与关键词相关的要点

输出格式示例：
{{
    "is_real": true,
    "relevance": 85,
    "relevance_reason": "内容详细讨论了{keyword}的新功能，与关键词高度相关",
    "keyword_mentioned": true,
    "importance": "high",
    "summary": "本文介绍了{keyword}的最新进展..."
}}

重要：只输出JSON，不要其他解释。"""
    
    async def analyze_content(
        self,
        content: str,
        keyword: str,
        expanded_terms: Optional[List[str]] = None,
        pre_matched: bool = False,
        matched_terms: Optional[List[str]] = None
    ) -> AIAnalysisResult:
        """
        分析内容的真实性、相关性、重要程度
        
        Args:
            content: 内容文本
            keyword: 监控关键词
            expanded_terms: 扩展的关键词变体
            pre_matched: 是否预匹配
            matched_terms: 匹配到的变体
            
        Returns:
            AI分析结果
        """
        if not self.api_key:
            logger.warning("OpenRouter API Key 未设置，返回默认分析结果")
            return AIAnalysisResult(
                is_real=True,
                relevance=50 if pre_matched else 30,
                keyword_mentioned=pre_matched,
                importance="medium" if pre_matched else "low",
                summary=content[:100] + "..." if len(content) > 100 else content
            )
        
        if expanded_terms is None:
            expanded_terms = [keyword]
        if matched_terms is None:
            matched_terms = []
        
        # 截断内容以避免超出token限制
        truncated_content = content[:2000] if len(content) > 2000 else content
        
        system_prompt = self._build_analysis_prompt(
            keyword, expanded_terms, pre_matched, matched_terms
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": truncated_content}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=500
        )
        
        if not response:
            return AIAnalysisResult(
                is_real=True,
                relevance=50 if pre_matched else 30,
                keyword_mentioned=pre_matched,
                importance="medium" if pre_matched else "low",
                summary=truncated_content[:100] + "..."
            )
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                return AIAnalysisResult(
                    is_real=result.get("is_real", True),
                    relevance=result.get("relevance", 0),
                    relevance_reason=result.get("relevance_reason", ""),
                    keyword_mentioned=result.get("keyword_mentioned", pre_matched),
                    importance=result.get("importance", "low"),
                    summary=result.get("summary", ""),
                    matched_keywords=matched_terms
                )
        except json.JSONDecodeError as e:
            logger.warning(f"AI分析JSON解析失败: {e}, 响应: {response}")
        
        # 回退到默认结果
        return AIAnalysisResult(
            is_real=True,
            relevance=50 if pre_matched else 30,
            keyword_mentioned=pre_matched,
            importance="medium" if pre_matched else "low",
            summary=truncated_content[:100] + "..."
        )
    
    async def generate_summary(self, title: str, content: str, max_length: int = 100) -> str:
        """
        生成内容摘要
        
        Args:
            title: 标题
            content: 内容
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        if not self.api_key:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        truncated = content[:1500] if len(content) > 1500 else content
        
        system_prompt = f"""请为以下内容生成摘要，{max_length}字以内，突出核心要点："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"标题：{title}\n\n内容：{truncated}"}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )
        
        if response:
            return response.strip()[:max_length]
        
        return truncated[:max_length] + "..." if len(truncated) > max_length else truncated


class AIServiceManager:
    """AI服务管理器"""
    
    # 类级别变量，用于跨线程同步请求频率
    _global_last_request_time = 0
    _global_lock = threading.Lock()
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "openrouter"):
        """
        初始化 AI 服务管理器
        
        Args:
            api_key: API Key
            provider: 模型提供商 ("openrouter", "moonshot"/"kimi")
        """
        self.openrouter = OpenRouterService(api_key, provider)
        # 根据 provider 设置不同的请求间隔
        # Moonshot 免费用户限制较严，建议 2-3 秒间隔
        # OpenRouter 可以设置更短的间隔
        if provider in ["moonshot", "kimi"]:
            self._min_request_interval = 2.0  # Moonshot: 2秒间隔（每分钟约30个请求）
        else:
            self._min_request_interval = 0.5  # OpenRouter: 0.5秒间隔
    
    async def _rate_limit_delay(self):
        """请求频率控制，避免过快调用API（线程安全版本）"""
        delay = 0
        self._global_lock.acquire()
        try:
            current_time = time.time()
            elapsed = current_time - self._global_last_request_time
            if elapsed < self._min_request_interval:
                delay = self._min_request_interval - elapsed
        finally:
            self._global_lock.release()
        
        # 在锁外等待
        if delay > 0:
            await asyncio.sleep(delay)
        
        # 更新最后请求时间
        with self._global_lock:
            self._global_last_request_time = time.time()
    
    async def analyze_hotspot(
        self,
        title: str,
        content: str,
        keyword: str
    ) -> AIAnalysisResult:
        """
        分析热点内容
        
        Args:
            title: 标题
            content: 内容
            keyword: 监控关键词
            
        Returns:
            分析结果
        """
        # 请求频率控制
        await self._rate_limit_delay()
        
        # 1. Query Expansion
        expansion = await self.openrouter.expand_keyword(keyword)
        expanded_terms = expansion.expanded_terms
        
        # 2. 预匹配检查
        full_text = f"{title} {content}".lower()
        matched_terms = []
        pre_matched = False
        
        for term in expanded_terms:
            if term.lower() in full_text:
                matched_terms.append(term)
                pre_matched = True
        
        # 3. AI分析
        combined_content = f"标题：{title}\n\n内容：{content}"
        analysis = await self.openrouter.analyze_content(
            content=combined_content,
            keyword=keyword,
            expanded_terms=expanded_terms,
            pre_matched=pre_matched,
            matched_terms=matched_terms
        )
        
        return analysis
    
    def filter_by_relevance(
        self,
        analysis: AIAnalysisResult,
        min_relevance: int = 50,
        require_keyword_mention: bool = False
    ) -> bool:
        """
        根据相关性过滤
        
        Args:
            analysis: AI分析结果
            min_relevance: 最小相关性分数
            require_keyword_mention: 是否要求提及关键词
            
        Returns:
            是否通过过滤
        """
        # 不真实的内容丢弃
        if not analysis.is_real:
            logger.debug(f"内容被过滤：不真实")
            return False
        
        # 相关性低于阈值丢弃
        if analysis.relevance < min_relevance:
            logger.debug(f"内容被过滤：相关性{analysis.relevance}低于阈值{min_relevance}")
            return False
        
        # 未提及关键词且相关性低于65丢弃
        if require_keyword_mention and not analysis.keyword_mentioned:
            if analysis.relevance < 65:
                logger.debug(f"内容被过滤：未提及关键词且相关性低于65")
                return False
        
        return True


# 全局AI服务实例
_ai_service: Optional[AIServiceManager] = None


def get_ai_service(api_key: Optional[str] = None, provider: str = "openrouter") -> AIServiceManager:
    """
    获取AI服务实例
    
    Args:
        api_key: API Key
        provider: 模型提供商 ("openrouter", "moonshot"/"kimi")
        
    Returns:
        AI服务管理器实例
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIServiceManager(api_key, provider)
    return _ai_service
