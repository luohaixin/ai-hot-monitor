"""
AI分析引擎 - 热度计算、关键词匹配、综合筛选
"""

import re
import math
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from loguru import logger

from ..models import HotspotCreate, SentimentType, AIAnalysisDetail
from ..config_loader import get_config
from ..ai_service import get_ai_service, AIServiceManager, AIAnalysisResult


@dataclass
class HotspotScore:
    """热点评分结果"""
    total_score: float
    views_score: float
    interaction_score: float
    time_decay_score: float
    keyword_match_score: float
    is_hot: bool


class AIFilterEngine:
    """AI筛选引擎"""
    
    def __init__(self):
        self.config = get_config()
        self.keywords_config = self.config.keywords
        self.hot_score_config = self.config.hot_score_config
        
        # 编译正则表达式
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译关键词匹配模式"""
        self.exact_patterns = [
            re.compile(re.escape(kw), re.IGNORECASE) 
            for kw in self.keywords_config.get('exact', [])
        ]
        self.fuzzy_patterns = [
            re.compile(re.escape(kw), re.IGNORECASE) 
            for kw in self.keywords_config.get('fuzzy', [])
        ]
        self.exclude_patterns = [
            re.compile(re.escape(kw), re.IGNORECASE) 
            for kw in self.keywords_config.get('exclude', [])
        ]
    
    def keyword_match(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        关键词匹配
        
        Returns:
            (是否匹配, 匹配得分, 匹配到的关键词列表)
        """
        if not text:
            return False, 0.0, []
        
        text_lower = text.lower()
        matched_keywords = []
        score = 0.0
        
        # 检查排除词
        for pattern in self.exclude_patterns:
            if pattern.search(text):
                logger.debug(f"内容包含排除词，跳过: {text[:50]}...")
                return False, 0.0, []
        
        # 精确匹配（权重高）
        for i, pattern in enumerate(self.exact_patterns):
            if pattern.search(text):
                keyword = self.keywords_config['exact'][i]
                matched_keywords.append(keyword)
                score += 2.0  # 精确匹配得2分
        
        # 模糊匹配（权重低）
        for i, pattern in enumerate(self.fuzzy_patterns):
            if pattern.search(text):
                keyword = self.keywords_config['fuzzy'][i]
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
                    score += 1.0  # 模糊匹配得1分
        
        is_match = len(matched_keywords) > 0
        return is_match, score, matched_keywords
    
    def calculate_hot_score(
        self, 
        views: int, 
        interactions: int, 
        publish_time: Optional[datetime],
        keyword_score: float,
        source: str = ""
    ) -> HotspotScore:
        """
        计算热点分数
        
        公式: (浏览量×0.4 + 互动量×0.4) × 时间衰减因子 + 关键词匹配得分×0.2 + 基础分
        
        对于没有浏览量数据的数据源（如机器之心、量子位等），给予基础热度分
        """
        weights = self.hot_score_config.get('weights', {})
        view_weight = weights.get('views', 0.4)
        interaction_weight = weights.get('interactions', 0.4)
        time_weight = weights.get('time_decay', 0.2)
        
        # 基础热度计算（对数平滑）
        views_score = math.log10(max(views, 1)) * 10 * view_weight
        interaction_score = math.log10(max(interactions, 1)) * 10 * interaction_weight
        
        # 时间衰减因子
        time_decay = self._calculate_time_decay(publish_time)
        time_score = 100 * time_decay * time_weight
        
        # 为不同数据源设置基础热度分（解决无浏览量数据的热度问题）
        base_hot_score = 0
        if views == 0 and interactions == 0:
            # 新闻类网站给予基础分 40-50
            news_sources = ['机器之心', '机器之心英文版', '量子位', '新智元', 'InfoQ AI', '36氪']
            if source in news_sources:
                base_hot_score = 45
            # 社交媒体给予基础分 35-45
            elif 'github' in source.lower() or 'hackernews' in source.lower():
                base_hot_score = 40
            else:
                base_hot_score = 35  # 其他数据源默认基础分
        
        # 综合得分
        base_score = (views_score + interaction_score) * time_decay
        keyword_bonus = keyword_score * 5  # 关键词匹配加成
        total_score = base_score + keyword_bonus + base_hot_score
        
        # 判断是否热点
        threshold = self.hot_score_config.get('threshold', 100)
        is_hot = total_score >= threshold
        
        return HotspotScore(
            total_score=round(total_score, 2),
            views_score=round(views_score, 2),
            interaction_score=round(interaction_score, 2),
            time_decay_score=round(time_score, 2),
            keyword_match_score=round(keyword_bonus, 2),
            is_hot=is_hot
        )
    
    def _calculate_time_decay(self, publish_time: Optional[datetime]) -> float:
        """计算时间衰减因子"""
        if publish_time is None:
            return 0.5  # 无时间信息，中等权重
        
        decay_factor = self.hot_score_config.get('decay_factor', 0.95)
        now = datetime.utcnow()
        hours_diff = max((now - publish_time).total_seconds() / 3600, 0)
        
        # 指数衰减
        decay = math.pow(decay_factor, hours_diff)
        return max(decay, 0.1)  # 最小保留10%
    
    def filter_hotspot(self, hotspot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        筛选热点
        
        Returns:
            筛选后的热点数据，如果不匹配则返回None
        """
        # 合并标题和摘要进行匹配
        title = hotspot_data.get('title', '')
        text = f"{title} {hotspot_data.get('summary', '')}"
        
        # 关键词匹配
        is_match, keyword_score, matched_keywords = self.keyword_match(text)
        
        if not is_match:
            logger.debug(f"[关键词过滤] 标题: {title[:50]}... - 未匹配任何关键词")
            return None
        
        # 计算热度分数
        views = hotspot_data.get('views', 0)
        interactions = hotspot_data.get('interactions', 0)
        publish_time = hotspot_data.get('publish_time')
        source = hotspot_data.get('source', '')
        
        score_result = self.calculate_hot_score(
            views, interactions, publish_time, keyword_score, source
        )
        
        # 组装结果
        result = hotspot_data.copy()
        result['hot_score'] = score_result.total_score
        result['keywords'] = ','.join(matched_keywords)
        result['is_hot'] = score_result.is_hot
        result['_score_detail'] = score_result
        result['_matched_keywords'] = matched_keywords
        
        logger.debug(f"[关键词匹配] 标题: {title[:50]}... - 匹配: {matched_keywords}, 热度: {score_result.total_score:.2f}")
        
        return result
    
    def batch_filter(self, hotspots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量筛选"""
        results = []
        for hotspot in hotspots:
            filtered = self.filter_hotspot(hotspot)
            if filtered:
                results.append(filtered)
        
        # 按热度排序
        results.sort(key=lambda x: x['hot_score'], reverse=True)
        return results


class HotspotAnalyzer:
    """热点综合分析器"""
    
    def __init__(self):
        self.filter_engine = AIFilterEngine()
        self.config = get_config()
        self._ai_service: Optional[AIServiceManager] = None
    
    def _get_ai_service(self) -> Optional[AIServiceManager]:
        """获取AI服务实例（延迟初始化）"""
        if self._ai_service is None:
            provider = self.config.get('ai_service.provider', 'openrouter')
            
            # 根据 provider 选择对应的环境变量，其次使用配置文件
            if provider in ['moonshot', 'kimi']:
                api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENROUTER_API_KEY") or self.config.get('ai_service.api_key')
            else:
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MOONSHOT_API_KEY") or self.config.get('ai_service.api_key')
            
            if api_key:
                self._ai_service = get_ai_service(api_key, provider)
                # 设置模型
                model = self.config.get('ai_service.model', 'moonshot-v1-8k' if provider in ['moonshot', 'kimi'] else 'deepseek/deepseek-chat')
                if model:
                    self._ai_service.openrouter.model = model
        return self._ai_service
    
    def _is_ai_enabled(self) -> bool:
        """检查AI功能是否启用"""
        return self.config.get('ai_service.enabled', True) and self._get_ai_service() is not None
    
    def analyze_sync(self, hotspot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        同步版本的综合分析热点（用于爬虫引擎）
        
        包括：
        1. 关键词匹配
        2. 热度计算
        3. 情感分析（简化版或AI分析）
        4. 自动分类
        5. AI分析（真实性、相关性、重要程度、摘要）
        """
        title = hotspot_data.get('title', '')[:50]
        
        # 先进行筛选
        filtered = self.filter_engine.filter_hotspot(hotspot_data)
        if not filtered:
            logger.debug(f"[分析过滤] 标题: {title}... - 关键词匹配失败")
            return None
        
        # 获取监控关键词
        keywords = self.config.keywords
        exact_keywords = keywords.get('exact', [])
        primary_keyword = exact_keywords[0] if exact_keywords else "AI"
        
        # 判断是否启用AI分析
        if self._is_ai_enabled():
            try:
                # 使用真实AI服务进行分析（同步调用）
                ai_result = self._analyze_with_ai_sync(filtered, primary_keyword)
                filtered['sentiment'] = self._map_importance_to_sentiment(ai_result.importance)
                filtered['category'] = self._determine_category(filtered)
                filtered['is_real'] = ai_result.is_real
                filtered['relevance'] = ai_result.relevance
                filtered['relevance_reason'] = ai_result.relevance_reason
                filtered['importance'] = ai_result.importance
                filtered['ai_summary'] = ai_result.summary
                filtered['keyword_mentioned'] = ai_result.keyword_mentioned
                filtered['matched_keywords'] = ai_result.matched_keywords
                
                # 生成AI分析详情
                ai_analysis = self._generate_ai_analysis_with_result(filtered, ai_result)
                filtered['ai_analysis'] = ai_analysis
                
                # 根据相关性过滤
                min_relevance = self.config.get('ai_service.min_relevance', 50)
                if ai_result.relevance < min_relevance:
                    logger.info(f"[AI过滤] 标题: {filtered.get('title', '')[:50]}... - 相关性{ai_result.relevance}低于阈值{min_relevance}")
                    return None
                    
            except Exception as e:
                logger.error(f"AI分析失败，回退到规则分析: {e}")
                # AI分析失败，回退到规则分析
                self._analyze_with_rules_sync(filtered)
        else:
            # 使用规则分析
            self._analyze_with_rules_sync(filtered)
        
        return filtered
    
    def analyze_batch_sync(self, hotspot_items: List[Dict[str, Any]], max_workers: int = 2) -> List[Dict[str, Any]]:
        """
        批量并发分析热点（同步版本）- 性能优化
        
        Args:
            hotspot_items: 热点数据列表
            max_workers: 最大并发数（默认5个并发）
            
        Returns:
            分析通过的热点列表
        """
        if not hotspot_items:
            return []
        
        results = []
        
        # 第一阶段：使用线程池并发进行关键词匹配和AI分析
        def analyze_single_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            try:
                return self.analyze_sync(item)
            except Exception as e:
                logger.error(f"分析单个项目失败: {e}")
                return None
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_item = {
                executor.submit(analyze_single_item, item): item 
                for item in hotspot_items
            }
            
            # 收集结果
            for future in as_completed(future_to_item):
                result = future.result()
                if result:
                    results.append(result)
        
        logger.info(f"批量分析完成: {len(hotspot_items)} 条输入, {len(results)} 条通过")
        return results
    
    async def analyze_batch(self, hotspot_items: List[Dict[str, Any]], max_concurrent: int = 2) -> List[Dict[str, Any]]:
        """
        批量并发分析热点（异步版本）- 性能优化
        
        Args:
            hotspot_items: 热点数据列表
            max_concurrent: 最大并发数（默认5个并发）
            
        Returns:
            分析通过的热点列表
        """
        if not hotspot_items:
            return []
        
        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    return await self.analyze(item)
                except Exception as e:
                    logger.error(f"分析单个项目失败: {e}")
                    return None
        
        # 并发执行所有分析任务
        tasks = [analyze_with_semaphore(item) for item in hotspot_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉None和异常
        valid_results = [
            r for r in results 
            if r is not None and not isinstance(r, Exception)
        ]
        
        logger.info(f"批量分析完成: {len(hotspot_items)} 条输入, {len(valid_results)} 条通过")
        return valid_results
    
    async def analyze(self, hotspot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        异步版本的综合分析热点（用于API端点）
        
        包括：
        1. 关键词匹配
        2. 热度计算
        3. 情感分析（简化版或AI分析）
        4. 自动分类
        5. AI分析（真实性、相关性、重要程度、摘要）
        """
        # 先进行筛选
        filtered = self.filter_engine.filter_hotspot(hotspot_data)
        if not filtered:
            return None
        
        # 获取监控关键词
        keywords = self.config.keywords
        exact_keywords = keywords.get('exact', [])
        primary_keyword = exact_keywords[0] if exact_keywords else "AI"
        
        # 判断是否启用AI分析
        if self._is_ai_enabled():
            try:
                # 使用真实AI服务进行分析
                ai_result = await self._analyze_with_ai(filtered, primary_keyword)
                filtered['sentiment'] = self._map_importance_to_sentiment(ai_result.importance)
                filtered['category'] = self._determine_category(filtered)
                filtered['is_real'] = ai_result.is_real
                filtered['relevance'] = ai_result.relevance
                filtered['relevance_reason'] = ai_result.relevance_reason
                filtered['importance'] = ai_result.importance
                filtered['ai_summary'] = ai_result.summary
                filtered['keyword_mentioned'] = ai_result.keyword_mentioned
                filtered['matched_keywords'] = ai_result.matched_keywords
                
                # 生成AI分析详情
                ai_analysis = self._generate_ai_analysis_with_result(filtered, ai_result)
                filtered['ai_analysis'] = ai_analysis
                
                # 根据相关性过滤
                min_relevance = self.config.get('ai_service.min_relevance', 50)
                if ai_result.relevance < min_relevance:
                    logger.debug(f"内容被AI过滤：相关性{ai_result.relevance}低于阈值{min_relevance}")
                    return None
                    
            except Exception as e:
                logger.error(f"AI分析失败，回退到规则分析: {e}")
                # AI分析失败，回退到规则分析
                await self._analyze_with_rules(filtered)
        else:
            # 使用规则分析
            await self._analyze_with_rules(filtered)
        
        return filtered
    
    async def _analyze_with_ai(self, filtered: Dict[str, Any], keyword: str) -> AIAnalysisResult:
        """使用AI服务分析内容（异步）"""
        ai_service = self._get_ai_service()
        title = filtered.get('title', '')
        content = filtered.get('content', '') or filtered.get('summary', '')
        
        result = await ai_service.analyze_hotspot(
            title=title,
            content=content,
            keyword=keyword
        )
        
        return result
    
    def _analyze_with_ai_sync(self, filtered: Dict[str, Any], keyword: str) -> AIAnalysisResult:
        """使用AI服务分析内容（同步版本）"""
        import asyncio
        ai_service = self._get_ai_service()
        title = filtered.get('title', '')
        content = filtered.get('content', '') or filtered.get('summary', '')
        
        # 尝试运行异步方法
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，直接提交协程到现有循环
                # 使用 asyncio.run_coroutine_threadsafe 而不是创建新线程
                future = asyncio.run_coroutine_threadsafe(
                    ai_service.analyze_hotspot(title=title, content=content, keyword=keyword),
                    loop
                )
                return future.result(timeout=60)  # 设置60秒超时
            else:
                return loop.run_until_complete(
                    ai_service.analyze_hotspot(title=title, content=content, keyword=keyword)
                )
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(ai_service.analyze_hotspot(title=title, content=content, keyword=keyword))
        except Exception as e:
            # AI调用失败，记录错误并返回默认结果
            logger.warning(f"AI分析调用失败: {e}，使用默认分析结果")
            return AIAnalysisResult(
                is_real=True,
                relevance=50,
                relevance_reason="AI分析服务暂时不可用，使用默认评分",
                keyword_mentioned=True,
                importance="medium",
                summary=content[:100] + "..." if len(content) > 100 else content
            )
    
    async def _analyze_with_rules(self, filtered: Dict[str, Any]) -> None:
        """使用规则进行分析（回退方案 - 异步）"""
        self._analyze_with_rules_sync(filtered)
    
    def _analyze_with_rules_sync(self, filtered: Dict[str, Any]) -> None:
        """使用规则进行分析（回退方案 - 同步）"""
        # 情感分析
        sentiment, sentiment_reason = self._analyze_sentiment(
            filtered.get('title', '') + ' ' + filtered.get('summary', '')
        )
        filtered['sentiment'] = sentiment
        
        # 自动分类
        category, category_reason = self._classify(
            filtered.get('title', '') + ' ' + filtered.get('summary', '')
        )
        filtered['category'] = category
        
        # 生成AI分析理由
        ai_analysis = self._generate_ai_analysis(filtered, sentiment_reason, category_reason)
        filtered['ai_analysis'] = ai_analysis
        
        # 设置默认值
        filtered['is_real'] = True
        filtered['relevance'] = 50
        filtered['relevance_reason'] = "基于关键词匹配的相关性评估"
        filtered['importance'] = "medium"
        filtered['ai_summary'] = filtered.get('summary', '')[:100]
        filtered['keyword_mentioned'] = len(filtered.get('_matched_keywords', [])) > 0
    
    def _map_importance_to_sentiment(self, importance: str) -> str:
        """将重要程度映射到情感"""
        mapping = {
            'urgent': 'positive',
            'high': 'positive',
            'medium': 'neutral',
            'low': 'neutral'
        }
        return mapping.get(importance, 'neutral')
    
    def _determine_category(self, filtered: Dict[str, Any]) -> str:
        """确定内容分类"""
        category, _ = self._classify(
            filtered.get('title', '') + ' ' + filtered.get('summary', '')
        )
        return category
    
    def _analyze_sentiment(self, text: str) -> Tuple[str, str]:
        """简化版情感分析，返回情感和理由"""
        sentiment_config = self.config.sentiment_config
        
        positive_words = sentiment_config.get('positive_words', [])
        negative_words = sentiment_config.get('negative_words', [])
        
        text = text.lower()
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            sentiment = SentimentType.POSITIVE.value
            reason = f"检测到 {pos_count} 个正面情感词，{neg_count} 个负面情感词，整体情感倾向积极"
        elif neg_count > pos_count:
            sentiment = SentimentType.NEGATIVE.value
            reason = f"检测到 {pos_count} 个正面情感词，{neg_count} 个负面情感词，整体情感倾向消极"
        else:
            sentiment = SentimentType.NEUTRAL.value
            reason = f"正面情感词({pos_count})与负面情感词({neg_count})数量平衡，情感倾向中性"
        
        return sentiment, reason
    
    def _classify(self, text: str) -> Tuple[str, str]:
        """自动分类，返回分类和理由"""
        categories = self.config.categories
        
        text = text.lower()
        category_scores = {}
        matched_keywords = {}
        
        for category in categories:
            name = category['name']
            keywords = category.get('keywords', [])
            score = 0
            matched = []
            for kw in keywords:
                if kw in text:
                    score += 1
                    matched.append(kw)
            if score > 0:
                category_scores[name] = score
                matched_keywords[name] = matched
        
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            matched = matched_keywords.get(best_category, [])
            reason = f"根据匹配到的关键词 [{', '.join(matched[:3])}]，判定为{best_category}类内容"
            return best_category, reason
        
        return "其他", "未匹配到明确分类关键词，归类为其他"
    
    def _generate_ai_analysis(
        self, 
        filtered: Dict[str, Any], 
        sentiment_reason: str, 
        category_reason: str
    ) -> AIAnalysisDetail:
        """生成AI分析理由（基于规则）"""
        score_detail = filtered.get('_score_detail')
        matched_keywords = filtered.get('_matched_keywords', [])
        
        # 关键词匹配理由
        if matched_keywords:
            exact_keywords = [kw for kw in matched_keywords if any(
                kw.lower() == e.lower() for e in self.config.keywords.get('exact', [])
            )]
            fuzzy_keywords = [kw for kw in matched_keywords if kw not in exact_keywords]
            
            keyword_parts = []
            if exact_keywords:
                keyword_parts.append(f"精确匹配: {', '.join(exact_keywords)}")
            if fuzzy_keywords:
                keyword_parts.append(f"模糊匹配: {', '.join(fuzzy_keywords)}")
            keyword_reason = f"命中 {len(matched_keywords)} 个监控词，{'；'.join(keyword_parts)}"
        else:
            keyword_reason = "未匹配到监控关键词"
        
        # 热度评分理由
        if score_detail:
            views = filtered.get('views', 0)
            interactions = filtered.get('interactions', 0)
            publish_time = filtered.get('publish_time')
            
            time_info = ""
            if publish_time:
                hours_ago = (datetime.utcnow() - publish_time).total_seconds() / 3600
                if hours_ago < 1:
                    time_info = "刚刚发布，时效性强"
                elif hours_ago < 24:
                    time_info = f"{int(hours_ago)}小时前发布"
                else:
                    time_info = f"{int(hours_ago/24)}天前发布"
            else:
                time_info = "发布时间未知"
            
            hot_score_reason = (
                f"热度得分 {filtered.get('hot_score', 0):.1f}，"
                f"浏览量({views})贡献 {score_detail.views_score:.1f}分，"
                f"互动量({interactions})贡献 {score_detail.interaction_score:.1f}分，"
                f"关键词匹配贡献 {score_detail.keyword_match_score:.1f}分。"
                f"{time_info}"
            )
            
            time_decay = score_detail.time_decay_score / 20  # 反推时间衰减因子
        else:
            hot_score_reason = "热度评分计算完成"
            time_decay = 1.0
        
        return AIAnalysisDetail(
            matched_keywords=matched_keywords,
            keyword_match_reason=keyword_reason,
            sentiment_reason=sentiment_reason,
            category_reason=category_reason,
            hot_score_reason=hot_score_reason,
            views_score=score_detail.views_score if score_detail else 0,
            interaction_score=score_detail.interaction_score if score_detail else 0,
            time_decay_factor=round(time_decay, 2),
            keyword_bonus=score_detail.keyword_match_score if score_detail else 0
        )
    
    def _generate_ai_analysis_with_result(
        self, 
        filtered: Dict[str, Any], 
        ai_result: AIAnalysisResult
    ) -> AIAnalysisDetail:
        """生成AI分析理由（基于AI分析结果）"""
        score_detail = filtered.get('_score_detail')
        matched_keywords = ai_result.matched_keywords or filtered.get('_matched_keywords', [])
        
        # 关键词匹配理由
        if matched_keywords:
            keyword_reason = f"AI识别到 {len(matched_keywords)} 个相关关键词: {', '.join(matched_keywords)}"
        else:
            keyword_reason = ai_result.relevance_reason or "未匹配到监控关键词"
        
        # 热度评分理由
        if score_detail:
            views = filtered.get('views', 0)
            interactions = filtered.get('interactions', 0)
            publish_time = filtered.get('publish_time')
            
            time_info = ""
            if publish_time:
                hours_ago = (datetime.utcnow() - publish_time).total_seconds() / 3600
                if hours_ago < 1:
                    time_info = "刚刚发布，时效性强"
                elif hours_ago < 24:
                    time_info = f"{int(hours_ago)}小时前发布"
                else:
                    time_info = f"{int(hours_ago/24)}天前发布"
            else:
                time_info = "发布时间未知"
            
            hot_score_reason = (
                f"热度得分 {filtered.get('hot_score', 0):.1f}，"
                f"浏览量({views})贡献 {score_detail.views_score:.1f}分，"
                f"互动量({interactions})贡献 {score_detail.interaction_score:.1f}分，"
                f"关键词匹配贡献 {score_detail.keyword_match_score:.1f}分。"
                f"{time_info}"
            )
            
            time_decay = score_detail.time_decay_score / 20
        else:
            hot_score_reason = "热度评分计算完成"
            time_decay = 1.0
        
        # 情感理由（基于AI重要性）
        sentiment_reason = f"AI评估重要程度为 {ai_result.importance}，相关性评分 {ai_result.relevance}/100"
        
        # 分类理由
        category = filtered.get('category', '其他')
        category_reason = f"基于内容主题自动分类为「{category}」"
        
        return AIAnalysisDetail(
            matched_keywords=matched_keywords,
            keyword_match_reason=keyword_reason,
            sentiment_reason=sentiment_reason,
            category_reason=category_reason,
            hot_score_reason=hot_score_reason,
            views_score=score_detail.views_score if score_detail else 0,
            interaction_score=score_detail.interaction_score if score_detail else 0,
            time_decay_factor=round(time_decay, 2),
            keyword_bonus=score_detail.keyword_match_score if score_detail else 0
        )
    
    def get_trend(self, hotspots: List[Dict], days: int = 7) -> List[Dict]:
        """计算趋势数据"""
        from collections import defaultdict
        
        trend_data = defaultdict(lambda: {'count': 0, 'total_score': 0})
        
        for hotspot in hotspots:
            crawl_time = hotspot.get('crawl_time')
            if crawl_time:
                date_key = crawl_time.strftime('%Y-%m-%d') if isinstance(crawl_time, datetime) else str(crawl_time)[:10]
                trend_data[date_key]['count'] += 1
                trend_data[date_key]['total_score'] += hotspot.get('hot_score', 0)
        
        # 转换为列表并排序
        result = []
        for date in sorted(trend_data.keys())[-days:]:
            data = trend_data[date]
            result.append({
                'date': date,
                'count': data['count'],
                'avg_hot_score': round(data['total_score'] / max(data['count'], 1), 2)
            })
        
        return result
