"""
MCP协议服务端 - AI热点监控工具
使用官方mcp Python SDK实现
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        CallToolResult,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not available, MCP features disabled")


class MCPServer:
    """MCP协议服务端"""

    def __init__(self):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Run: pip install mcp")

        self.server = Server("ai-hot-monitor")
        self._setup_handlers()

    def _setup_handlers(self):
        """设置MCP协议处理器"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出所有可用的工具"""
            return [
                Tool(
                    name="get_hotspots",
                    description="获取AI热点列表，支持分页和筛选",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer", "description": "页码", "default": 1},
                            "page_size": {"type": "integer", "description": "每页数量", "default": 10},
                            "source": {"type": "string", "description": "数据来源筛选"},
                            "category": {"type": "string", "description": "分类筛选"},
                            "sentiment": {"type": "string", "description": "情感筛选(positive/negative/neutral)"},
                            "min_hot_score": {"type": "number", "description": "最低热度分数"},
                        }
                    }
                ),
                Tool(
                    name="get_hot_top",
                    description="获取热点TOP榜单",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "返回数量", "default": 10},
                            "hours": {"type": "integer", "description": "最近N小时"},
                        }
                    }
                ),
                Tool(
                    name="get_hot_trend",
                    description="获取热点趋势数据",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "天数", "default": 7},
                        }
                    }
                ),
                Tool(
                    name="get_dashboard",
                    description="获取仪表盘统计数据",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_hot_stats",
                    description="获取热点统计信息",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="predict_trend",
                    description="预测热点趋势，基于历史数据预测未来热度",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "指定分类进行预测"},
                            "hours_ahead": {"type": "integer", "description": "预测多少小时后的趋势", "default": 24},
                        }
                    }
                ),
                Tool(
                    name="trigger_crawl",
                    description="手动触发热点抓取任务",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "指定数据源(留空则抓取所有)"},
                        }
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> CallToolResult:
            """调用工具"""
            try:
                result = await self._handle_tool(name, arguments)
                return CallToolResult(
                    content=[TextContent(type="text", text=str(result))]
                )
            except Exception as e:
                logger.error(f"MCP tool error: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

    async def _handle_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        from core.models import get_db
        from sqlalchemy import desc, func
        from datetime import datetime, timedelta

        db = get_db()
        session = db.get_session()

        try:
            if name == "get_hotspots":
                query = session.query(HotspotORM).filter_by(is_deleted=False)

                if arguments.get("source"):
                    query = query.filter_by(source=arguments["source"])
                if arguments.get("category"):
                    query = query.filter_by(category=arguments["category"])
                if arguments.get("sentiment"):
                    query = query.filter_by(sentiment=arguments["sentiment"])
                if arguments.get("min_hot_score"):
                    query = query.filter(HotspotORM.hot_score >= arguments["min_hot_score"])

                query = query.order_by(desc(HotspotORM.hot_score))

                page = arguments.get("page", 1)
                page_size = arguments.get("page_size", 10)
                items = query.offset((page - 1) * page_size).limit(page_size).all()

                return {
                    "total": query.count(),
                    "page": page,
                    "items": [
                        {
                            "id": h.id,
                            "title": h.title,
                            "source": h.source,
                            "hot_score": h.hot_score,
                            "category": h.category,
                            "sentiment": h.sentiment,
                            "url": h.url,
                        }
                        for h in items
                    ]
                }

            elif name == "get_hot_top":
                query = session.query(HotspotORM).filter_by(is_deleted=False)

                if arguments.get("hours"):
                    since = datetime.utcnow() - timedelta(hours=arguments["hours"])
                    query = query.filter(HotspotORM.crawl_time >= since)

                limit = arguments.get("limit", 10)
                items = query.order_by(desc(HotspotORM.hot_score)).limit(limit).all()

                return {
                    "items": [
                        {"rank": i + 1, "title": h.title, "hot_score": h.hot_score, "source": h.source}
                        for i, h in enumerate(items)
                    ]
                }

            elif name == "get_hot_trend":
                days = arguments.get("days", 7)
                since = datetime.utcnow() - timedelta(days=days)

                results = session.query(
                    func.date(HotspotORM.crawl_time).label('date'),
                    func.count().label('count'),
                    func.avg(HotspotORM.hot_score).label('avg_score')
                ).filter(
                    HotspotORM.crawl_time >= since
                ).group_by(
                    func.date(HotspotORM.crawl_time)
                ).order_by('date').all()

                return {
                    "trend": [
                        {"date": str(r.date), "count": r.count, "avg_hot_score": float(r.avg_score or 0)}
                        for r in results
                    ]
                }

            elif name == "get_dashboard":
                total = session.query(HotspotORM).filter_by(is_deleted=False).count()
                today = datetime.utcnow().date()

                return {
                    "total_hotspots": total,
                    "today_hotspots": session.query(HotspotORM).filter(
                        func.date(HotspotORM.crawl_time) == today
                    ).count(),
                }

            elif name == "get_hot_stats":
                total = session.query(HotspotORM).filter_by(is_deleted=False).count()

                cat_results = session.query(
                    HotspotORM.category,
                    func.count().label('count')
                ).filter_by(is_deleted=False).group_by(HotspotORM.category).all()

                return {
                    "total": total,
                    "categories": [
                        {"category": r.category, "count": r.count}
                        for r in cat_results
                    ]
                }

            elif name == "predict_trend":
                category = arguments.get("category")
                hours_ahead = arguments.get("hours_ahead", 24)

                query = session.query(HotspotORM).filter_by(is_deleted=False)
                if category:
                    query = query.filter_by(category=category)

                items = query.order_by(desc(HotspotORM.crawl_time)).limit(100).all()

                if not items:
                    return {"prediction": [], "confidence": 0}

                avg_score = sum(h.hot_score for h in items) / len(items)
                score_trend = "stable"
                if len(items) >= 3:
                    recent_avg = sum(h.hot_score for h in items[:3]) / 3
                    older_avg = sum(h.hot_score for h in items[-3:]) / 3 if len(items) >= 3 else recent_avg
                    if recent_avg > older_avg * 1.2:
                        score_trend = "rising"
                    elif recent_avg < older_avg * 0.8:
                        score_trend = "falling"

                predicted_score = avg_score * (
                    1.1 if score_trend == "rising" else 0.9 if score_trend == "falling" else 1.0
                )

                return {
                    "prediction": {
                        "predicted_hot_score": round(predicted_score, 2),
                        "trend": score_trend,
                        "based_on_samples": len(items),
                        "hours_ahead": hours_ahead,
                    },
                    "confidence": min(0.8, 0.5 + len(items) * 0.01)
                }

            elif name == "trigger_crawl":
                source = arguments.get("source")
                return {"status": "triggered", "source": source or "all"}

            else:
                return {"error": f"Unknown tool: {name}"}

        finally:
            session.close()

    async def run(self):
        """运行MCP服务"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


_mcp_server = None

def get_mcp_server() -> Optional[MCPServer]:
    """获取MCP服务器实例"""
    global _mcp_server
    if MCP_AVAILABLE and _mcp_server is None:
        try:
            _mcp_server = MCPServer()
        except Exception as e:
            logger.error(f"Failed to create MCP server: {e}")
            return None
    return _mcp_server


async def run_mcp_server():
    """运行MCP服务器的便捷函数"""
    server = get_mcp_server()
    if server:
        await server.run()
    else:
        raise RuntimeError("MCP server not available")
