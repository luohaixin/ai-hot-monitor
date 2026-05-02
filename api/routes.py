"""
API路由定义 - FastAPI接口
"""

import io
import time
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, desc
from loguru import logger

# HTTP Bearer安全方案 - 用于认证
security = HTTPBearer(auto_error=False)

from core.models import (
    get_db, HotspotORM, HotspotResponse, HotspotFilter,
    TrendData, CategoryStats, SourceStats, DashboardStats,
    AIAnalysisDetail
)
from core.config_loader import get_config
from core.crawler.engine import CrawlerEngine, ScheduledCrawler
from core.crawler.task_manager import task_manager
from core.filter.analyzer import HotspotAnalyzer
from core.filter.predictor import HotspotForecaster
from core.push.service import PushService
from core.urgent_detector import UrgentHotspotDetector, UrgentPushService

# V3.1 新增导入
from core.crawler.social_sources import SocialSourceAggregator
from core.ai_service import get_ai_service, AIServiceManager
from core.email_service import get_email_service, EmailConfig, HotspotEmailData


router = APIRouter(prefix="/api/v1")


# ========== 响应模型 ==========

class ApiResponse(BaseModel):
    """统一API响应"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class CrawlRequest(BaseModel):
    """抓取请求"""
    source: Optional[str] = None  # None表示抓取所有
    fast_mode: Optional[bool] = False  # 快速模式：跳过AI分析和详情页抓取


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    keywords: Optional[dict] = None
    hot_score: Optional[dict] = None
    push: Optional[dict] = None


class PushTestRequest(BaseModel):
    """推送测试请求"""
    channel: Optional[str] = None  # None表示测试所有渠道


# V3.1 新增请求模型
class SocialSearchRequest(BaseModel):
    """社交媒体搜索请求"""
    query: str
    max_results: int = Field(20, ge=1, le=50)
    sources: Optional[List[str]] = None  # 指定数据源，None表示搜索所有


class AIAnalyzeRequest(BaseModel):
    """AI分析请求"""
    title: str
    content: str
    keyword: str


class AIConfigRequest(BaseModel):
    """AI配置请求"""
    enabled: Optional[bool] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    min_relevance: Optional[int] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=50, le=2000)
    require_keyword_mention: Optional[bool] = None


class GeneralConfigRequest(BaseModel):
    """通用配置请求"""
    monitor_interval: Optional[int] = Field(None, ge=5, le=1440)
    hot_score_threshold: Optional[int] = Field(None, ge=0, le=1000)


class NotificationConfigRequest(BaseModel):
    """通知配置请求"""
    websocket_enabled: Optional[bool] = None
    new_hotspot_push: Optional[bool] = None
    urgent_reminder: Optional[bool] = None
    daily_digest: Optional[bool] = None


class EmailConfigRequest(BaseModel):
    """邮件配置请求"""
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    use_tls: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_name: Optional[str] = None


class SecurityConfigRequest(BaseModel):
    """安全配置请求"""
    current_password: str
    new_password: str
    confirm_password: str


class EmailTestRequest(BaseModel):
    """邮件测试请求"""
    to_email: str


class EmailNotificationConfigRequest(BaseModel):
    """邮件通知配置请求"""
    enabled: Optional[bool] = None
    min_hotspots_to_notify: Optional[int] = Field(None, ge=1, le=100)
    notify_on_urgent_only: Optional[bool] = None
    send_batch: Optional[bool] = None
    recipients: Optional[List[str]] = None


class KeywordAddRequest(BaseModel):
    """添加关键词请求"""
    type: str  # exact, fuzzy, exclude
    keyword: str


class KeywordRemoveRequest(BaseModel):
    """移除关键词请求"""
    type: str  # exact, fuzzy, exclude
    keyword: str


class KeywordsUpdateRequest(BaseModel):
    """关键词更新请求"""
    exact: List[str] = []
    fuzzy: List[str] = []
    exclude: List[str] = []


# ========== 工具函数 ==========

def get_db_session():
    """获取数据库会话"""
    db = get_db()
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()


def success_response(data=None, message="success"):
    """成功响应"""
    return ApiResponse(code=200, message=message, data=data)


def error_response(code=500, message="error"):
    """错误响应"""
    return ApiResponse(code=code, message=message, data=None)


def _serialize_hotspot(item: HotspotORM, include_analysis: bool = False, include_content: bool = False) -> dict:
    """序列化热点数据（V3.1 AI集成：包含完整的AI分析字段）"""
    result = {
        "id": item.id,
        "title": item.title,
        "source": item.source,
        "url": item.url,
        "summary": item.summary,
        "hot_score": item.hot_score,
        "views": item.views,
        "interactions": item.interactions,
        "sentiment": item.sentiment,
        "category": item.category,
        "keywords": item.keywords,
        "publish_time": item.publish_time.isoformat() if item.publish_time else None,
        "crawl_time": item.crawl_time.isoformat() if item.crawl_time else None,
        "is_urgent": item.is_urgent,
        "urgent_acknowledged": item.urgent_acknowledged
    }
    
    if include_analysis:
        # V3.1 AI集成：返回完整的AI分析字段
        result["ai_analysis"] = {
            "is_real": item.is_real,
            "relevance": item.relevance,
            "relevance_reason": item.relevance_reason,
            "importance": item.importance,
            "keyword_mentioned": item.keyword_mentioned,
            "matched_keywords": item.matched_keywords.split(',') if item.matched_keywords else []
        }
        # 同时添加顶层字段方便访问
        result["is_real"] = item.is_real
        result["relevance"] = item.relevance
        result["relevance_reason"] = item.relevance_reason
        result["importance"] = item.importance
        result["ai_summary"] = item.ai_summary
        result["keyword_mentioned"] = item.keyword_mentioned
        result["matched_keywords"] = item.matched_keywords.split(',') if item.matched_keywords else []
    
    if include_content and item.content:
        result["content"] = item.content
    
    return result


# ========== 热点相关接口 ==========

@router.get("/dashboard", response_model=ApiResponse)
async def get_dashboard():
    """获取仪表盘数据"""
    session = get_db().get_session()
    try:
        # 总数量
        total = session.query(HotspotORM).filter_by(is_deleted=False).count()
        
        # 今日数量
        today = datetime.utcnow().date()
        today_count = session.query(HotspotORM).filter(
            func.date(HotspotORM.crawl_time) == today
        ).count()
        
        # 分类统计
        cat_results = session.query(
            HotspotORM.category,
            func.count().label('count')
        ).filter_by(is_deleted=False).group_by(HotspotORM.category).all()
        
        total_cats = sum(r.count for r in cat_results)
        categories = sorted([
            {
                "category": r.category,
                "count": r.count,
                "percentage": round(r.count / total_cats * 100, 1) if total_cats > 0 else 0
            }
            for r in cat_results
        ], key=lambda x: x['count'], reverse=True)[:5]
        
        # 7天趋势
        since = datetime.utcnow() - timedelta(days=7)
        trend_results = session.query(
            func.date(HotspotORM.crawl_time).label('date'),
            func.count().label('count'),
            func.avg(HotspotORM.hot_score).label('avg_score')
        ).filter(
            HotspotORM.crawl_time >= since
        ).group_by(
            func.date(HotspotORM.crawl_time)
        ).order_by('date').all()
        
        trend = [
            {
                "date": str(r.date),
                "count": r.count,
                "avg_hot_score": round(float(r.avg_score or 0), 2)
            }
            for r in trend_results
        ]
        
        # 热门来源
        source_results = session.query(
            HotspotORM.source,
            func.count().label('count'),
            func.max(HotspotORM.crawl_time).label('last_update')
        ).filter_by(is_deleted=False).group_by(HotspotORM.source).all()
        
        sources = sorted([
            {
                "source": r.source,
                "count": r.count,
                "last_update": r.last_update.isoformat() if r.last_update else None
            }
            for r in source_results
        ], key=lambda x: x['count'], reverse=True)[:5]
        
        # 最新热点
        latest = session.query(HotspotORM).filter_by(is_deleted=False).order_by(
            desc(HotspotORM.crawl_time)
        ).limit(5).all()
        
        return success_response({
            "total_hotspots": total,
            "today_hotspots": today_count,
            "top_categories": categories,
            "trend_7d": trend,
            "hot_sources": sources,
            "latest_hotspots": [
                {
                    "id": h.id,
                    "title": h.title,
                    "source": h.source,
                    "hot_score": h.hot_score,
                    "category": h.category,
                    "crawl_time": h.crawl_time.isoformat() if h.crawl_time else None
                }
                for h in latest
            ]
        })
    finally:
        session.close()


@router.get("/hot/list", response_model=ApiResponse)
async def get_hot_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    category: Optional[str] = None,
    sentiment: Optional[str] = None,
    min_hot_score: Optional[float] = None,
    keyword: Optional[str] = None,
    today_only: bool = Query(False, description="仅返回今日新增的热点")
):
    """获取热点列表"""
    session = get_db().get_session()
    try:
        query = session.query(HotspotORM).filter_by(is_deleted=False)
        
        # 应用筛选条件
        if source:
            query = query.filter_by(source=source)
        if category:
            query = query.filter_by(category=category)
        if sentiment:
            query = query.filter_by(sentiment=sentiment)
        if min_hot_score is not None:
            query = query.filter(HotspotORM.hot_score >= min_hot_score)
        if keyword:
            query = query.filter(
                (HotspotORM.title.contains(keyword)) | 
                (HotspotORM.summary.contains(keyword)) |
                (HotspotORM.keywords.contains(keyword))
            )
        if today_only:
            today = datetime.utcnow().date()
            query = query.filter(func.date(HotspotORM.crawl_time) == today)
        
        # 总数
        total = query.count()
        
        # 分页 - 今日新增按热度排序，其他按时间排序
        if today_only:
            items = query.order_by(desc(HotspotORM.hot_score)).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
        else:
            items = query.order_by(desc(HotspotORM.crawl_time)).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
        
        return success_response({
            "items": [_serialize_hotspot(item) for item in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        })
    finally:
        session.close()


@router.get("/hot/top", response_model=ApiResponse)
async def get_hot_top(
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None
):
    """获取热门榜单"""
    session = get_db().get_session()
    try:
        query = session.query(HotspotORM).filter_by(is_deleted=False)
        
        if category:
            query = query.filter_by(category=category)
        
        items = query.order_by(desc(HotspotORM.hot_score)).limit(limit).all()
        
        return success_response({
            "items": [_serialize_hotspot(item, include_analysis=True) for item in items]
        })
    finally:
        session.close()


@router.get("/hot/detail/{hotspot_id}", response_model=ApiResponse)
async def get_hot_detail(hotspot_id: int):
    """获取热点详情"""
    session = get_db().get_session()
    try:
        item = session.query(HotspotORM).filter_by(
            id=hotspot_id, 
            is_deleted=False
        ).first()
        
        if not item:
            return error_response(code=404, message="热点不存在")
        
        # 获取热点内容
        content = None
        if item.content:
            content = item.content
        
        return success_response({
            "detail": _serialize_hotspot(item, include_analysis=True, include_content=True)
        })
    finally:
        session.close()


@router.get("/hot/trend", response_model=ApiResponse)
async def get_hot_trend(
    days: int = Query(7, ge=1, le=90)
):
    """获取热点趋势数据"""
    session = get_db().get_session()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        
        # 按日期统计
        results = session.query(
            func.date(HotspotORM.crawl_time).label('date'),
            func.count().label('count'),
            func.avg(HotspotORM.hot_score).label('avg_score')
        ).filter(
            HotspotORM.crawl_time >= since
        ).group_by(
            func.date(HotspotORM.crawl_time)
        ).order_by('date').all()
        
        return success_response({
            "trend": [
                {
                    "date": str(r.date),
                    "count": r.count,
                    "avg_hot_score": round(float(r.avg_score or 0), 2)
                }
                for r in results
            ]
        })
    finally:
        session.close()


@router.get("/hot/stats", response_model=ApiResponse)
async def get_hot_stats():
    """获取热点统计信息"""
    session = get_db().get_session()
    try:
        # 总数量
        total = session.query(HotspotORM).filter_by(is_deleted=False).count()
        
        # 今日数量
        today = datetime.utcnow().date()
        today_count = session.query(HotspotORM).filter(
            func.date(HotspotORM.crawl_time) == today
        ).count()
        
        # 分类统计
        cat_results = session.query(
            HotspotORM.category,
            func.count().label('count')
        ).filter_by(is_deleted=False).group_by(HotspotORM.category).all()
        
        categories = [
            {
                "category": r.category,
                "count": r.count,
                "percentage": round(r.count / total * 100, 1) if total > 0 else 0
            }
            for r in cat_results
        ]
        
        # 来源统计
        source_results = session.query(
            HotspotORM.source,
            func.count().label('count'),
            func.max(HotspotORM.crawl_time).label('last_update')
        ).filter_by(is_deleted=False).group_by(HotspotORM.source).all()
        
        sources = [
            {
                "source": r.source,
                "count": r.count,
                "last_update": r.last_update.isoformat() if r.last_update else None
            }
            for r in source_results
        ]
        
        return success_response({
            "total_hotspots": total,
            "today_hotspots": today_count,
            "top_categories": sorted(categories, key=lambda x: x['count'], reverse=True)[:5],
            "hot_sources": sorted(sources, key=lambda x: x['count'], reverse=True)[:5]
        })
    finally:
        session.close()


# ========== V3.1 社交媒体搜索接口 ==========

@router.post("/hotspots/search", response_model=ApiResponse)
async def search_social_hotspots(request: SocialSearchRequest):
    """全网搜索 - 搜索多个社交媒体数据源"""
    try:
        # 根据请求中的 sources 参数决定是否启用对应数据源
        requested_sources = request.sources or []
        # 如果没有指定数据源，则搜索全部
        enable_all = len(requested_sources) == 0

        aggregator = SocialSourceAggregator(
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            enable_twitter=enable_all or "twitter" in requested_sources,
            enable_bing=enable_all or "bing" in requested_sources,
            enable_hackernews=enable_all or "hackernews" in requested_sources,
            enable_sogou=enable_all or "sogou" in requested_sources,
            enable_bilibili=enable_all or "bilibili" in requested_sources,
            enable_weibo=enable_all or "weibo" in requested_sources
        )

        results = await aggregator.search_all(
            query=request.query,
            max_results_per_source=request.max_results
        )
        
        # 合并所有结果
        all_results = []
        for source, items in results.items():
            for item in items:
                all_results.append({
                    "title": item.title,
                    "content": item.content,
                    "url": item.url,
                    "source": item.source,
                    "author": item.author,
                    "author_avatar": item.author_avatar,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "views": item.views,
                    "likes": item.likes,
                    "shares": item.shares,
                    "comments": item.comments
                })
        
        # 按时间排序
        all_results.sort(key=lambda x: x.get("published_at") or "", reverse=True)
        
        return success_response({
            "query": request.query,
            "results": all_results,
            "total": len(all_results),
            "sources": list(results.keys())
        })
    except Exception as e:
        logger.error(f"社交媒体搜索失败: {e}")
        return error_response(code=500, message=f"搜索失败: {str(e)}")


@router.get("/hotspots/trending", response_model=ApiResponse)
async def get_trending_hotspots():
    """获取各平台热门内容"""
    try:
        aggregator = SocialSourceAggregator(
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            enable_bing=False,
            enable_hackernews=True,
            enable_sogou=False,
            enable_bilibili=False,
            enable_weibo=True
        )
        
        results = await aggregator.get_trending()
        
        trending_data = {}
        for source, items in results.items():
            trending_data[source] = [
                {
                    "title": item.title,
                    "content": item.content,
                    "url": item.url,
                    "source": item.source,
                    "author": item.author,
                    "views": item.views,
                    "likes": item.likes,
                    "comments": item.comments
                }
                for item in items[:20]
            ]
        
        return success_response({
            "trending": trending_data
        })
    except Exception as e:
        logger.error(f"获取热门内容失败: {e}")
        return error_response(code=500, message=f"获取热门内容失败: {str(e)}")


# ========== V3.1 AI分析接口 ==========

@router.post("/ai/analyze", response_model=ApiResponse)
async def analyze_content(request: AIAnalyzeRequest):
    """AI分析内容 - 分析内容的真实性、相关性、重要程度"""
    try:
        config = get_config()
        ai_config = config.ai_service_config
        
        # 优先使用环境变量，其次使用配置文件
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
        provider = ai_config.get('provider', 'openrouter')
        
        if not ai_api_key:
            return error_response(code=503, message="AI服务未配置，请在设置页面配置API Key")
        
        ai_service = get_ai_service(ai_api_key, provider)
        
        result = await ai_service.analyze_hotspot(
            title=request.title,
            content=request.content,
            keyword=request.keyword
        )
        
        return success_response({
            "is_real": result.is_real,
            "relevance": result.relevance,
            "relevance_reason": result.relevance_reason,
            "keyword_mentioned": result.keyword_mentioned,
            "importance": result.importance,
            "summary": result.summary,
            "matched_keywords": result.matched_keywords
        })
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        return error_response(code=500, message=f"AI分析失败: {str(e)}")


@router.get("/ai/expand-keyword", response_model=ApiResponse)
async def expand_keyword(keyword: str = Query(..., description="要扩展的关键词")):
    """Query Expansion - 扩展关键词变体"""
    try:
        config = get_config()
        ai_config = config.ai_service_config
        
        # 优先使用环境变量，其次使用配置文件
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
        provider = ai_config.get('provider', 'openrouter')
        
        if not ai_api_key:
            return error_response(code=503, message="AI服务未配置，请在设置页面配置API Key")
        
        ai_service = get_ai_service(ai_api_key, provider)
        expansion = await ai_service.openrouter.expand_keyword(keyword)
        
        return success_response({
            "original": expansion.original,
            "expanded_terms": expansion.expanded_terms
        })
    except Exception as e:
        logger.error(f"关键词扩展失败: {e}")
        return error_response(code=500, message=f"关键词扩展失败: {str(e)}")


@router.post("/ai/summary", response_model=ApiResponse)
async def generate_summary(
    title: str = Query(..., description="标题"),
    content: str = Query(..., description="内容"),
    max_length: int = Query(100, ge=50, le=500, description="最大长度")
):
    """AI生成摘要"""
    try:
        config = get_config()
        ai_config = config.ai_service_config
        
        # 优先使用环境变量，其次使用配置文件
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
        provider = ai_config.get('provider', 'openrouter')
        
        if not ai_api_key:
            return error_response(code=503, message="AI服务未配置，请在设置页面配置API Key")
        
        ai_service = get_ai_service(ai_api_key, provider)
        summary = await ai_service.openrouter.generate_summary(title, content, max_length)
        
        return success_response({
            "title": title,
            "summary": summary,
            "max_length": max_length
        })
    except Exception as e:
        logger.error(f"生成摘要失败: {e}")
        return error_response(code=500, message=f"生成摘要失败: {str(e)}")


@router.get("/ai/config", response_model=ApiResponse)
async def get_ai_config():
    """获取AI服务配置"""
    try:
        config = get_config()
        ai_config = config.ai_service_config
        
        # 隐藏敏感信息（API Key）
        safe_config = ai_config.copy()
        if safe_config.get('api_key'):
            safe_config['api_key'] = '********' + safe_config['api_key'][-4:]
        
        # 检查环境变量中的API Key
        env_api_key = os.getenv("OPENROUTER_API_KEY")
        
        return success_response({
            "config": safe_config,
            "env_api_key_configured": env_api_key is not None and len(env_api_key) > 0,
            "source": "env" if env_api_key else "config_file"
        })
    except Exception as e:
        logger.error(f"获取AI配置失败: {e}")
        return error_response(code=500, message=f"获取AI配置失败: {str(e)}")


@router.post("/ai/config", response_model=ApiResponse)
async def update_ai_config(request: AIConfigRequest):
    """更新AI服务配置"""
    try:
        config = get_config()
        
        # 构建更新数据
        update_data = {}
        if request.enabled is not None:
            update_data['enabled'] = request.enabled
        if request.model is not None:
            update_data['model'] = request.model
        if request.provider is not None:
            update_data['provider'] = request.provider
        if request.api_key is not None:
            # 如果API Key不是掩码，则更新
            if not request.api_key.startswith('********'):
                update_data['api_key'] = request.api_key
        if request.min_relevance is not None:
            update_data['min_relevance'] = request.min_relevance
        if request.temperature is not None:
            update_data['temperature'] = request.temperature
        if request.max_tokens is not None:
            update_data['max_tokens'] = request.max_tokens
        if request.require_keyword_mention is not None:
            update_data['require_keyword_mention'] = request.require_keyword_mention
        
        success = config.update_ai_config(update_data)
        
        if success:
            return success_response(message="AI配置更新成功")
        else:
            return error_response(code=500, message="AI配置更新失败")
    except Exception as e:
        logger.error(f"更新AI配置失败: {e}")
        return error_response(code=500, message=f"更新AI配置失败: {str(e)}")


@router.get("/ai/models", response_model=ApiResponse)
async def get_ai_models():
    """获取可用的AI模型列表"""
    models = [
        # Moonshot (Kimi) 模型
        {"id": "moonshot-v1-8k", "name": "Kimi v1 (8K)", "provider": "moonshot", "description": "Moonshot Kimi模型，8K上下文，长文本理解优秀"},
        {"id": "moonshot-v1-32k", "name": "Kimi v1 (32K)", "provider": "moonshot", "description": "Moonshot Kimi长文本模型，32K上下文，适合长文档分析"},
        # OpenRouter 模型
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "provider": "openrouter", "description": "DeepSeek官方模型，性价比高"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "openrouter", "description": "Anthropic Claude模型，理解能力强"},
        {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openrouter", "description": "OpenAI GPT-4o模型，综合能力优秀"},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openrouter", "description": "OpenAI轻量级模型，速度快"},
        {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "openrouter", "description": "Anthropic轻量级模型，响应快速"},
    ]
    
    return success_response({"models": models})


# ========== V3.1 邮件服务接口 ==========

@router.post("/email/test", response_model=ApiResponse)
async def test_email_connection(request: EmailTestRequest):
    """测试邮件连接"""
    try:
        email_service = get_email_service()
        
        if not email_service.is_configured():
            return error_response(code=503, message="邮件服务未配置")
        
        # 发送测试邮件
        test_data = HotspotEmailData(
            title="邮件服务测试",
            summary="这是一封测试邮件，用于验证邮件服务配置是否正确。",
            url="https://example.com",
            source="AI热点监控",
            importance="low",
            relevance=100,
            hot_score=100.0
        )
        
        results = email_service.send_hotspot_notification(
            to_emails=[request.to_email],
            hotspot=test_data
        )
        
        if results.get(request.to_email):
            return success_response(message="测试邮件发送成功")
        else:
            return error_response(code=500, message="测试邮件发送失败")
    except Exception as e:
        logger.error(f"邮件测试失败: {e}")
        return error_response(code=500, message=f"邮件测试失败: {str(e)}")


@router.get("/email/status", response_model=ApiResponse)
async def get_email_status():
    """获取邮件服务状态"""
    try:
        email_service = get_email_service()

        return success_response({
            "configured": email_service.is_configured(),
            "smtp_server": email_service.config.smtp_server if email_service.config else None,
            "username": email_service.config.username if email_service.config else None,
            "from_name": email_service.config.from_name if email_service.config else None
        })
    except Exception as e:
        logger.error(f"获取邮件状态失败: {e}")
        return error_response(code=500, message=f"获取邮件状态失败: {str(e)}")


# ========== 邮件通知自动化绑定接口 ==========

@router.get("/email/notification/status", response_model=ApiResponse)
async def get_email_notification_status():
    """获取邮件通知服务状态（爬取自动化绑定）"""
    try:
        from core.email_notification_service import get_email_notification_service

        email_notify_service = get_email_notification_service()
        status = email_notify_service.get_status()

        return success_response(status)
    except Exception as e:
        logger.error(f"获取邮件通知状态失败: {e}")
        return error_response(code=500, message=f"获取邮件通知状态失败: {str(e)}")


@router.get("/email/notification/logs", response_model=ApiResponse)
async def get_email_notification_logs(limit: int = Query(50, ge=1, le=100)):
    """获取邮件发送日志"""
    try:
        from core.email_notification_service import get_email_notification_service

        email_notify_service = get_email_notification_service()
        logs = email_notify_service.get_send_logs(limit=limit)

        return success_response({
            "logs": logs,
            "total": len(logs)
        })
    except Exception as e:
        logger.error(f"获取邮件发送日志失败: {e}")
        return error_response(code=500, message=f"获取邮件发送日志失败: {str(e)}")


@router.post("/email/notification/config", response_model=ApiResponse)
async def update_email_notification_config(request: EmailNotificationConfigRequest):
    """更新邮件通知配置（运行时）"""
    try:
        from core.email_notification_service import get_email_notification_service

        email_notify_service = get_email_notification_service()

        # 构建更新参数
        update_kwargs = {}
        if request.enabled is not None:
            update_kwargs['enabled'] = request.enabled
        if request.min_hotspots_to_notify is not None:
            update_kwargs['min_hotspots_to_notify'] = request.min_hotspots_to_notify
        if request.notify_on_urgent_only is not None:
            update_kwargs['notify_on_urgent_only'] = request.notify_on_urgent_only
        if request.send_batch is not None:
            update_kwargs['send_batch'] = request.send_batch
        if request.recipients is not None:
            update_kwargs['recipients'] = request.recipients

        success = email_notify_service.update_config(**update_kwargs)

        if success:
            return success_response(message="邮件通知配置已更新")
        else:
            return error_response(code=500, message="配置更新失败")
    except Exception as e:
        logger.error(f"更新邮件通知配置失败: {e}")
        return error_response(code=500, message=f"更新邮件通知配置失败: {str(e)}")


@router.post("/email/notification/test", response_model=ApiResponse)
async def test_email_notification():
    """手动触发邮件通知测试（模拟爬取完成后的通知）"""
    try:
        from core.email_notification_service import get_email_notification_service

        email_notify_service = get_email_notification_service()

        # 模拟爬取统计和新热点数据
        mock_crawl_stats = {
            'total_crawled': 10,
            'total_filtered': 5,
            'total_saved': 3,
            'total_new': 2,
            'crawl_time': datetime.now()
        }

        mock_new_hotspots = [
            {
                'id': 1,
                'title': '测试热点1：OpenAI发布新模型',
                'summary': '这是一个测试热点的摘要信息...',
                'url': 'https://example.com/news/1',
                'source': '测试来源',
                'importance': 'high',
                'relevance': 85,
                'hot_score': 88.5,
                'publish_time': datetime.now()
            },
            {
                'id': 2,
                'title': '测试热点2：AI技术突破',
                'summary': '另一个测试热点的摘要信息...',
                'url': 'https://example.com/news/2',
                'source': '测试来源2',
                'importance': 'medium',
                'relevance': 75,
                'hot_score': 72.0,
                'publish_time': datetime.now()
            }
        ]

        result = email_notify_service.on_crawl_completed(mock_crawl_stats, mock_new_hotspots)

        return success_response({
            "should_send": result.get('should_send'),
            "sent": result.get('sent'),
            "message": result.get('message')
        })
    except Exception as e:
        logger.error(f"邮件通知测试失败: {e}")
        return error_response(code=500, message=f"邮件通知测试失败: {str(e)}")


# ========== V3.1 WebSocket状态接口 ==========

@router.get("/websocket/status", response_model=ApiResponse)
async def get_websocket_status():
    """获取WebSocket连接状态"""
    try:
        from core.websocket import websocket_manager
        
        stats = websocket_manager.get_connection_stats()
        
        return success_response({
            "enabled": websocket_manager.get_socket_io() is not None,
            "connected_clients": stats["connected_clients"],
            "subscribed_keywords": stats["subscribed_keywords"],
            "total_subscriptions": stats["total_subscriptions"],
            "message_history": stats["message_history"]
        })
    except Exception as e:
        logger.error(f"获取WebSocket状态失败: {e}")
        return error_response(code=500, message=f"获取WebSocket状态失败: {str(e)}")


# ========== V3.1 系统状态接口 ==========

@router.get("/system/status", response_model=ApiResponse)
async def get_system_status():
    """获取系统整体状态"""
    try:
        # 检查各项服务状态
        email_service = get_email_service()
        config = get_config()
        ai_config = config.ai_service_config
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
        ai_provider = ai_config.get('provider', 'openrouter')
        twitter_api_key = os.getenv("TWITTER_API_KEY")
        
        from core.websocket import websocket_manager
        
        return success_response({
            "version": "3.1.0",
            "services": {
                "email": {
                    "configured": email_service.is_configured(),
                    "status": "ok" if email_service.is_configured() else "not_configured"
                },
                "ai": {
                    "configured": ai_api_key is not None,
                    "status": "ok" if ai_api_key else "not_configured",
                    "provider": ai_provider
                },
                "websocket": {
                    "enabled": websocket_manager.get_socket_io() is not None,
                    "status": "ok" if websocket_manager.get_socket_io() else "disabled"
                },
                "twitter": {
                    "configured": twitter_api_key is not None,
                    "status": "ok" if twitter_api_key else "not_configured"
                }
            },
            "features": {
                "social_search": True,
                "ai_analysis": ai_api_key is not None,
                "email_notification": email_service.is_configured(),
                "realtime_websocket": websocket_manager.get_socket_io() is not None
            }
        })
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return error_response(code=500, message=f"获取系统状态失败: {str(e)}")


# ========== 监控词管理接口 ==========

@router.get("/keywords", response_model=ApiResponse)
async def get_keywords():
    """获取监控词配置"""
    config = get_config()
    return success_response({
        "keywords": config.keywords
    })


@router.post("/keywords", response_model=ApiResponse)
async def update_keywords(request: KeywordsUpdateRequest):
    """批量更新监控词"""
    config = get_config()
    success = config.update_keywords({
        "exact": request.exact,
        "fuzzy": request.fuzzy,
        "exclude": request.exclude
    })
    if success:
        return success_response(message="监控词更新成功")
    else:
        return error_response(message="监控词更新失败")


@router.post("/keywords/add", response_model=ApiResponse)
async def add_keyword(request: KeywordAddRequest):
    """添加单个监控词"""
    config = get_config()
    success = config.add_keyword(request.type, request.keyword)
    if success:
        return success_response(message="监控词添加成功")
    else:
        return error_response(message="监控词添加失败")


@router.post("/keywords/remove", response_model=ApiResponse)
async def remove_keyword(request: KeywordRemoveRequest):
    """移除单个监控词"""
    config = get_config()
    success = config.remove_keyword(request.type, request.keyword)
    if success:
        return success_response(message="监控词移除成功")
    else:
        return error_response(message="监控词移除失败")


# ========== 爬虫相关接口 ==========

crawler_engine = None
scheduled_crawler = None

@router.post("/crawler/run", response_model=ApiResponse)
async def run_crawler(
    background_tasks: BackgroundTasks,
    request: Optional[CrawlRequest] = None
):
    """手动触发抓取 - 带进度跟踪（V3.1 AI分析集成）"""
    global crawler_engine
    
    if crawler_engine is None:
        crawler_engine = CrawlerEngine()
    
    source = request.source if request else None
    
    # 创建任务
    task_id = task_manager.create_task(source_filter=source)
    
    def do_crawl():
        try:
            # 获取启用的数据源
            config = get_config()
            data_sources = config.data_sources
            enabled_sources = {
                k: v for k, v in data_sources.items() 
                if v.get('enabled', True) and (not source or k == source)
            }
            
            # 计算总数据源数量（包括社交媒体源）
            total_sources = len(enabled_sources)
            social_config = config.get('social_sources', {})
            # 检查启用的社交媒体源
            if social_config.get('hackernews', {}).get('enabled', True):
                total_sources += 1  # HackerNews 热门
            if social_config.get('weibo', {}).get('enabled', True):
                total_sources += 1  # 微博热搜
            
            # 开始任务
            task_manager.start_task(task_id, total_sources)
            
            # V3.1 AI分析集成：创建分析器实例并传入
            analyzer = HotspotAnalyzer()
            
            # 检查是否启用快速模式
            is_fast_mode = request.fast_mode if request else False
            if is_fast_mode:
                logger.info(f"⚡ 任务 {task_id} 启用快速模式")
            
            stats = crawler_engine.crawl_and_save(
                analyzer=analyzer,      # 传入分析器进行AI深度分析
                task_id=task_id,        # 传递任务ID用于进度更新
                fast_mode=is_fast_mode  # 传递快速模式参数
            )
            
            # 完成任务
            task_manager.complete_task(task_id, stats)
            logger.info(f"手动抓取完成: {task_id}, 统计: {stats}")
            
        except Exception as e:
            logger.error(f"手动抓取失败: {e}")
            task_manager.fail_task(task_id, str(e))
    
    # 后台执行
    background_tasks.add_task(do_crawl)
    
    return success_response({
        "task_id": task_id,
        "message": "抓取任务已启动"
    })


@router.get("/crawler/status", response_model=ApiResponse)
async def get_crawler_status():
    """获取爬虫状态"""
    config = get_config()
    data_sources = config.data_sources
    
    return success_response({
        "sources": [
            {
                "id": k,
                "name": v.get('name', k),
                "enabled": v.get('enabled', True),
                "interval": v.get('interval', 30),
                "url": v.get('url', '')
            }
            for k, v in data_sources.items()
        ]
    })


@router.get("/crawler/task/{task_id}", response_model=ApiResponse)
async def get_crawler_task(task_id: str):
    """获取抓取任务状态和进度"""
    task = task_manager.get_task(task_id)
    if not task:
        return error_response(code=404, message="任务不存在")
    
    return success_response({"task": task})


@router.get("/crawler/tasks", response_model=ApiResponse)
async def list_crawler_tasks(limit: int = Query(10, ge=1, le=20)):
    """获取抓取任务历史列表"""
    tasks = task_manager.list_tasks(limit=limit)
    return success_response({"tasks": tasks})


# ========== 推送相关接口 ==========

push_service = None

@router.post("/push/test", response_model=ApiResponse)
async def test_push(request: Optional[PushTestRequest] = None):
    """测试推送"""
    global push_service
    
    if push_service is None:
        push_service = PushService()
    
    channel = request.channel if request else None
    results = push_service.test(channel)
    
    return success_response({
        "results": results
    })


@router.post("/push/now", response_model=ApiResponse)
async def push_now(
    background_tasks: BackgroundTasks,
    threshold: Optional[float] = None
):
    """立即执行推送"""
    global push_service
    
    if push_service is None:
        push_service = PushService()
    
    def do_push():
        try:
            count = push_service.check_and_push(threshold)
            logger.info(f"手动推送完成: {count} 条")
        except Exception as e:
            logger.error(f"手动推送失败: {e}")
    
    background_tasks.add_task(do_push)
    
    return success_response(message="推送任务已启动")


# ========== 配置相关接口 ==========

@router.get("/config", response_model=ApiResponse)
async def get_config_api():
    """获取当前配置（隐藏敏感信息）"""
    config = get_config()
    
    return success_response({
        "app": config.get('app'),
        "keywords": config.keywords,
        "hot_score": config.hot_score_config,
        "categories": config.categories,
        "data_sources_count": len(config.data_sources),
        "push_enabled": config.push_config.get('enabled', False),
        "push_mode": config.push_config.get('mode', 'threshold')
    })


@router.post("/config/reload", response_model=ApiResponse)
async def reload_config():
    """重新加载配置"""
    config = get_config()
    config.reload()
    return success_response(message="配置已重新加载")


# ========== 健康检查 ==========

@router.get("/health", response_model=ApiResponse)
async def health_check():
    """健康检查"""
    return success_response({
        "status": "healthy",
        "version": "3.1.0",
        "timestamp": int(time.time())
    })


# ========== V3.1 设置管理接口 ==========

@router.get("/settings/general", response_model=ApiResponse)
async def get_general_settings():
    """获取通用设置"""
    try:
        config = get_config()
        general_config = config.general_config
        
        return success_response({
            "monitor_interval": general_config.get('monitor_interval', 30),
            "hot_score_threshold": general_config.get('hot_score_threshold', 100)
        })
    except Exception as e:
        logger.error(f"获取通用设置失败: {e}")
        return error_response(code=500, message=f"获取通用设置失败: {str(e)}")


@router.post("/settings/general", response_model=ApiResponse)
async def update_general_settings(request: GeneralConfigRequest):
    """更新通用设置"""
    try:
        config = get_config()
        
        update_data = {}
        if request.monitor_interval is not None:
            update_data['monitor_interval'] = request.monitor_interval
        if request.hot_score_threshold is not None:
            update_data['hot_score_threshold'] = request.hot_score_threshold
        
        success = config.update_general_config(update_data)
        
        if success:
            return success_response(message="通用设置更新成功")
        else:
            return error_response(code=500, message="通用设置更新失败")
    except Exception as e:
        logger.error(f"更新通用设置失败: {e}")
        return error_response(code=500, message=f"更新通用设置失败: {str(e)}")


@router.get("/settings/notifications", response_model=ApiResponse)
async def get_notification_settings():
    """获取通知设置"""
    try:
        config = get_config()
        notification_config = config.notification_config
        
        return success_response({
            "websocket_enabled": notification_config.get('websocket_enabled', True),
            "new_hotspot_push": notification_config.get('new_hotspot_push', True),
            "urgent_reminder": notification_config.get('urgent_reminder', True),
            "daily_digest": notification_config.get('daily_digest', False)
        })
    except Exception as e:
        logger.error(f"获取通知设置失败: {e}")
        return error_response(code=500, message=f"获取通知设置失败: {str(e)}")


@router.post("/settings/notifications", response_model=ApiResponse)
async def update_notification_settings(request: NotificationConfigRequest):
    """更新通知设置"""
    try:
        config = get_config()
        
        update_data = {}
        if request.websocket_enabled is not None:
            update_data['websocket_enabled'] = request.websocket_enabled
        if request.new_hotspot_push is not None:
            update_data['new_hotspot_push'] = request.new_hotspot_push
        if request.urgent_reminder is not None:
            update_data['urgent_reminder'] = request.urgent_reminder
        if request.daily_digest is not None:
            update_data['daily_digest'] = request.daily_digest
        
        success = config.update_notification_config(update_data)
        
        if success:
            return success_response(message="通知设置更新成功")
        else:
            return error_response(code=500, message="通知设置更新失败")
    except Exception as e:
        logger.error(f"更新通知设置失败: {e}")
        return error_response(code=500, message=f"更新通知设置失败: {str(e)}")


@router.get("/settings/email", response_model=ApiResponse)
async def get_email_settings():
    """获取邮件设置"""
    try:
        config = get_config()
        email_config = config.email_config
        
        # 隐藏密码
        safe_config = email_config.copy()
        if safe_config.get('password'):
            safe_config['password'] = '********' + safe_config['password'][-4:]
        
        return success_response({
            "config": safe_config,
            "env_configured": os.getenv("EMAIL_SMTP_SERVER") is not None
        })
    except Exception as e:
        logger.error(f"获取邮件设置失败: {e}")
        return error_response(code=500, message=f"获取邮件设置失败: {str(e)}")


@router.post("/settings/email", response_model=ApiResponse)
async def update_email_settings(request: EmailConfigRequest):
    """更新邮件设置"""
    try:
        config = get_config()
        
        update_data = {}
        if request.smtp_server is not None:
            update_data['smtp_server'] = request.smtp_server
        if request.smtp_port is not None:
            update_data['smtp_port'] = request.smtp_port
        if request.use_tls is not None:
            update_data['use_tls'] = request.use_tls
        if request.username is not None:
            update_data['username'] = request.username
        if request.password is not None:
            update_data['password'] = request.password
        if request.from_name is not None:
            update_data['from_name'] = request.from_name
        
        success = config.update_email_config(update_data)
        
        if success:
            return success_response(message="邮件设置更新成功")
        else:
            return error_response(code=500, message="邮件设置更新失败")
    except Exception as e:
        logger.error(f"更新邮件设置失败: {e}")
        return error_response(code=500, message=f"更新邮件设置失败: {str(e)}")


@router.get("/settings/export", response_model=ApiResponse)
async def export_data(format: str = "json"):
    """导出数据"""
    try:
        session = get_db().get_session()
        try:
            # 获取所有热点数据
            items = session.query(HotspotORM).filter_by(is_deleted=False).all()
            
            data = []
            for item in items:
                data.append({
                    "id": item.id,
                    "title": item.title,
                    "source": item.source,
                    "url": item.url,
                    "summary": item.summary,
                    "content": item.content,
                    "hot_score": item.hot_score,
                    "views": item.views,
                    "interactions": item.interactions,
                    "sentiment": item.sentiment,
                    "category": item.category,
                    "keywords": item.keywords,
                    "publish_time": item.publish_time.isoformat() if item.publish_time else None,
                    "crawl_time": item.crawl_time.isoformat() if item.crawl_time else None,
                    "is_urgent": item.is_urgent,
                    "is_real": item.is_real,
                    "relevance": item.relevance,
                    "importance": item.importance,
                    "ai_summary": item.ai_summary
                })
            
            if format == "json":
                content = json.dumps(data, ensure_ascii=False, indent=2)
                media_type = "application/json"
                filename = f"hotspots_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            elif format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                content = output.getvalue()
                media_type = "text/csv"
                filename = f"hotspots_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                return error_response(code=400, message="不支持的导出格式")
            
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"导出数据失败: {e}")
        return error_response(code=500, message=f"导出数据失败: {str(e)}")


@router.post("/settings/clear-data", response_model=ApiResponse)
async def clear_all_data():
    """清空所有数据"""
    try:
        session = get_db().get_session()
        try:
            # 软删除所有数据
            count = session.query(HotspotORM).filter_by(is_deleted=False).update({"is_deleted": True})
            session.commit()
            
            logger.info(f"已清空 {count} 条数据")
            return success_response(message=f"已清空 {count} 条数据")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"清空数据失败: {e}")
        return error_response(code=500, message=f"清空数据失败: {str(e)}")


@router.get("/settings/security", response_model=ApiResponse)
async def get_security_settings():
    """获取安全设置状态"""
    try:
        # 检查是否设置了管理员密码
        admin_password = os.getenv("ADMIN_PASSWORD")
        return success_response({
            "password_configured": admin_password is not None and len(admin_password) > 0
        })
    except Exception as e:
        logger.error(f"获取安全设置失败: {e}")
        return error_response(code=500, message=f"获取安全设置失败: {str(e)}")


@router.post("/settings/security/password", response_model=ApiResponse)
async def change_password(request: SecurityConfigRequest):
    """修改密码（当前仅做验证，不实际修改环境变量）"""
    try:
        # 验证新密码和确认密码是否匹配
        if request.new_password != request.confirm_password:
            return error_response(code=400, message="新密码和确认密码不匹配")
        
        # 验证新密码长度
        if len(request.new_password) < 6:
            return error_response(code=400, message="新密码长度至少6位")
        
        # 注意：实际修改密码需要写入环境变量或配置文件
        # 这里仅做前端演示，实际生产环境需要更安全的处理
        logger.info("密码修改请求已接收")
        return success_response(message="密码修改成功（演示模式）")
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return error_response(code=500, message=f"修改密码失败: {str(e)}")


# ========== 监控服务管理接口 ==========

@router.get("/monitor/status", response_model=ApiResponse)
async def get_monitor_status():
    """获取监控服务状态"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        status = monitor.get_status()
        return success_response(status)
    except Exception as e:
        logger.error(f"获取监控状态失败: {e}")
        return error_response(code=500, message=f"获取监控状态失败: {str(e)}")


@router.post("/monitor/start", response_model=ApiResponse)
async def start_monitor():
    """启动监控服务"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        
        # 获取配置中的间隔
        config = get_config()
        interval = config.general_config.get('monitor_interval', 30)
        
        success = monitor.start(interval_minutes=interval)
        
        if success:
            return success_response(message=f"监控服务已启动，间隔: {interval}分钟")
        else:
            return error_response(code=500, message="监控服务启动失败")
    except Exception as e:
        logger.error(f"启动监控服务失败: {e}")
        return error_response(code=500, message=f"启动监控服务失败: {str(e)}")


@router.post("/monitor/stop", response_model=ApiResponse)
async def stop_monitor():
    """停止监控服务"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        
        success = monitor.stop()
        
        if success:
            return success_response(message="监控服务已停止")
        else:
            return error_response(code=400, message="监控服务未在运行")
    except Exception as e:
        logger.error(f"停止监控服务失败: {e}")
        return error_response(code=500, message=f"停止监控服务失败: {str(e)}")


@router.post("/monitor/restart", response_model=ApiResponse)
async def restart_monitor():
    """重启监控服务"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        
        # 获取配置中的间隔
        config = get_config()
        interval = config.general_config.get('monitor_interval', 30)
        
        success = monitor.restart(interval_minutes=interval)
        
        if success:
            return success_response(message=f"监控服务已重启，间隔: {interval}分钟")
        else:
            return error_response(code=500, message="监控服务重启失败")
    except Exception as e:
        logger.error(f"重启监控服务失败: {e}")
        return error_response(code=500, message=f"重启监控服务失败: {str(e)}")


@router.post("/monitor/update-interval", response_model=ApiResponse)
async def update_monitor_interval(interval: int):
    """更新监控间隔（实时生效）"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        
        if interval < 5 or interval > 1440:
            return error_response(code=400, message="监控间隔必须在5-1440分钟之间")
        
        # 更新配置
        config = get_config()
        config.update_general_config({'monitor_interval': interval})
        
        # 更新运行中的服务
        success = monitor.update_interval(interval_minutes=interval)
        
        if success:
            return success_response(message=f"监控间隔已更新为: {interval}分钟")
        else:
            return error_response(code=500, message="监控间隔更新失败")
    except Exception as e:
        logger.error(f"更新监控间隔失败: {e}")
        return error_response(code=500, message=f"更新监控间隔失败: {str(e)}")


@router.post("/monitor/run-once", response_model=ApiResponse)
async def monitor_run_once():
    """立即执行一次抓取"""
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        
        # 在后台执行，不阻塞请求
        def do_crawl():
            try:
                monitor.run_once()
                logger.info("手动抓取完成")
            except Exception as e:
                logger.error(f"手动抓取失败: {e}")
        
        import threading
        thread = threading.Thread(target=do_crawl)
        thread.start()
        
        return success_response(message="抓取任务已启动")
    except Exception as e:
        logger.error(f"立即抓取失败: {e}")
        return error_response(code=500, message=f"立即抓取失败: {str(e)}")
